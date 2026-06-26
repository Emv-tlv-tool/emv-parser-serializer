import customtkinter as ctk
from tkinter import messagebox

class ButtonsPanel(ctk.CTkFrame):
    def __init__(self, master, input_panel_reference=None, on_parse_callback=None,
                 on_search_callback=None, **kwargs):
        super().__init__(master, **kwargs)

        self.input_panel = input_panel_reference
        self.on_parse_callback = on_parse_callback
        # Callback appelé quand l'utilisateur valide une recherche.
        # app.py se chargera de colorer la ligne correspondante dans l'arbre.
        self.on_search_callback = on_search_callback

        # On garde en mémoire le dernier résultat du parsing,
        # pour pouvoir rechercher dedans sans re-parser.
        self._dernier_arbre_resultats = []

        # État d'affichage de la zone de recherche : cachée au démarrage
        self._search_visible = False

        self.grid_columnconfigure(0, weight=1)  # bouton Parser
        self.grid_columnconfigure(1, weight=0)  # bouton Rechercher (toggle)

        # --- Bouton Parser ---
        self.parse_button = ctk.CTkButton(
            self,
            text="Parser",
            font=("Consolas", 13, "bold"),
            command=self._handle_click
        )
        self.parse_button.grid(row=0, column=0, padx=(14, 6), pady=10, sticky="ew")

        # --- Bouton Rechercher : ouvre/ferme la zone de saisie ---
        self.search_toggle_button = ctk.CTkButton(
            self,
            text="🔍 Rechercher",
            font=("Consolas", 13, "bold"),
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            command=self._toggle_search_zone,
        )
        self.search_toggle_button.grid(row=0, column=1, padx=(6, 14), pady=10)

        # --- Zone de recherche (cachée par défaut) ---
        # On la met dans son propre frame pour pouvoir l'afficher/cacher
        # d'un seul coup avec grid()/grid_remove(), sans toucher au reste.
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.grid_columnconfigure(0, weight=1)
        self.search_frame.grid_columnconfigure(1, weight=0)
        # Pas de .grid() ici : elle reste invisible tant qu'on n'appelle pas _toggle

        self.entry_search = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Tag à rechercher (ex: DF22)",
            font=("Consolas", 12),
        )
        self.entry_search.grid(row=0, column=0, padx=(14, 6), pady=(0, 10), sticky="ew")
        # Appuyer sur Entrée dans le champ lance la recherche
        self.entry_search.bind("<Return>", lambda e: self._handle_search())
        # Échap referme la zone de recherche
        self.entry_search.bind("<Escape>", lambda e: self._toggle_search_zone())

        self.search_confirm_button = ctk.CTkButton(
            self.search_frame,
            text="Valider",
            font=("Consolas", 12, "bold"),
            width=90,
            command=self._handle_search,
        )
        self.search_confirm_button.grid(row=0, column=1, padx=(0, 14), pady=(0, 10))

    # ------------------------------------------------------------------
    # AFFICHAGE / MASQUAGE DE LA ZONE DE RECHERCHE
    # ------------------------------------------------------------------
    def _toggle_search_zone(self):
        """
        Affiche la zone de recherche si elle est cachée, la cache si elle
        est visible. Place le curseur dans le champ quand elle s'ouvre.
        """
        if self._search_visible:
            # On la cache
            self.search_frame.grid_remove()
            self._search_visible = False
        else:
            # On l'affiche sous la ligne des boutons
            self.search_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
            self._search_visible = True
            # Place le focus directement dans le champ pour taper tout de suite
            self.entry_search.focus_set()

    # ------------------------------------------------------------------
    # PARSER (votre logique d'origine, inchangée)
    # ------------------------------------------------------------------
    def _handle_click(self):
        if self.input_panel is None:
            messagebox.showerror("Erreur", "Référence de l'InputPanel manquante.")
            return

        hex_data = self.input_panel.get_hex()
        if not hex_data:
            messagebox.showerror("Erreur", "Le champ de saisie est vide !")
            return

        # --- FONCTION DE DECOUPAGE INTERNE RECURSIVE ---
        def decoder_tlv_bloc(flux_hex, niveau_parent=""):
            elements = []
            idx = 0
            while idx < len(flux_hex):
                try:
                    # 1. Extraction du TAG
                    premier_octet = flux_hex[idx:idx+2]
                    if (int(premier_octet, 16) & 0x1F) == 0x1F:
                        tag = flux_hex[idx:idx+4]
                        idx += 4
                    else:
                        tag = premier_octet
                        idx += 2

                    # 2. Extraction de la LONGUEUR
                    premier_octet_longueur = flux_hex[idx:idx+2]
                    valeur_octet_longueur = int(premier_octet_longueur, 16)
                    idx += 2

                    if valeur_octet_longueur & 0x80:
                        nombre_octets_suivants = valeur_octet_longueur & 0x7F
                        octets_suivants = flux_hex[idx:idx+(nombre_octets_suivants*2)]
                        longueur_valeur = int(octets_suivants, 16)
                        idx += nombre_octets_suivants * 2
                    else:
                        longueur_valeur = valeur_octet_longueur

                    # 3. Extraction de la VALEUR
                    fin_valeur = idx + (longueur_valeur * 2)
                    valeur = flux_hex[idx:fin_valeur]
                    idx = fin_valeur

                    # Règle EMV : Vérifier si c'est un Tag Construit/Parent (Bit 6 à 1)
                    est_parent = bool(int(tag[:2], 16) & 0x20)
                    type_element = "Parent" if est_parent else "Enfant"

                    # On enregistre l'élément courant
                    elements.append({
                        "tag": tag,
                        "length": longueur_valeur,
                        "value": valeur if not est_parent else "", # Optionnel pour le parent
                        "type": type_element,
                        "parent_id": niveau_parent
                    })

                    # SI C'EST UN PARENT : On force l'algorithme à parser l'intérieur de sa valeur !
                    if est_parent and valeur:
                        sous_elements = decoder_tlv_bloc(valeur, niveau_parent=tag)
                        elements.extend(sous_elements)

                except Exception:
                    # Si un sous-bloc est mal formé, on passe à la suite pour ne pas bloquer l'application
                    break
            return elements

        # --- EXECUTION DU PARSER ---
        try:
            arbre_resultats = decoder_tlv_bloc(hex_data)

            # On garde le résultat en mémoire pour permettre la recherche ensuite
            self._dernier_arbre_resultats = arbre_resultats

            # --- COMPTER LES PARENTS ET ENFANTS SÉPARÉMENT ---
            nb_parents = sum(1 for el in arbre_resultats if el["type"] == "Parent")
            nb_enfants = sum(1 for el in arbre_resultats if el["type"] == "Enfant")

            texte_popup = (
                f"Parsing réussi !\n\n"
                f"🔹 Nombre de structures (Parents) : {nb_parents}\n"
                f"🔸 Nombre de données (Enfants) : {nb_enfants}\n\n"
                f"Total : {len(arbre_resultats)} éléments identifiés."
            )

            messagebox.showinfo("Résultat du Parser", texte_popup)

            # Envoi de la structure complète à votre binôme
            if self.on_parse_callback is not None:
                self.on_parse_callback(arbre_resultats)

        except Exception as e:
            messagebox.showerror("Erreur de format", f"Le flux hexadécimal est mal formé : {e}")

    # ------------------------------------------------------------------
    # RECHERCHE
    # ------------------------------------------------------------------
    def _handle_search(self):
        """
        Lit le tag saisi dans entry_search, vérifie qu'un parsing
        a déjà été fait, puis délègue la coloration à app.py
        via on_search_callback (ce fichier ne touche pas à l'affichage).
        """
        tag_recherche = self.entry_search.get().strip().upper()

        if not tag_recherche:
            messagebox.showwarning("Recherche", "Entrez un tag à rechercher (ex: DF22).")
            return

        if not self._dernier_arbre_resultats:
            messagebox.showwarning("Recherche", "Parsez d'abord un message TLV.")
            return

        # Compte combien de fois ce tag existe dans le dernier résultat
        occurrences = [el for el in self._dernier_arbre_resultats if el["tag"] == tag_recherche]

        if not occurrences:
            messagebox.showinfo("Recherche", f"Le tag '{tag_recherche}' est introuvable.")
            return

        # Délègue la coloration réelle dans l'arbre à app.py,
        # qui a accès aux vraies lignes TreeRow à colorer.
        if self.on_search_callback is not None:
            self.on_search_callback(tag_recherche)

# =====================================================================
# BLOC DE TEST AUTONOME
# =====================================================================
if __name__ == "__main__":
    # L'importation fonctionne directement car les fichiers sont côte à côte
    from input_panel import InputPanel

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    root_test = ctk.CTk()
    root_test.title("Sandbox de Test - Projet TLV")
    root_test.geometry("500x350")

    mon_input = InputPanel(root_test)
    mon_input.pack(fill="x", padx=15, pady=(15, 5))

    def test_search(tag):
        print(f"Recherche demandée pour le tag : {tag}")

    mes_boutons = ButtonsPanel(
        root_test,
        input_panel_reference=mon_input,
        on_search_callback=test_search,
    )
    mes_boutons.pack(fill="x", padx=15, pady=5)

    root_test.mainloop()