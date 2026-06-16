import customtkinter as ctk
from tkinter import messagebox

class ButtonsPanel(ctk.CTkFrame):
    def __init__(self, master, input_panel_reference=None, on_parse_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.input_panel = input_panel_reference
        self.on_parse_callback = on_parse_callback
        
        self.grid_columnconfigure(0, weight=1)

        self.parse_button = ctk.CTkButton(
            self, 
            text="Parser", 
            font=("Consolas", 13, "bold"),
            command=self._handle_click
        )
        self.parse_button.grid(row=0, column=0, padx=14, pady=10, sticky="ew")

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
            
            # --- ÉTAPE SUIVANTE : COMPTER LES PARENTS ET ENFANTS SÉPARÉMENT ---
            # On filtre la liste en comptant selon le type de chaque élément
            nb_parents = sum(1 for el in arbre_resultats if el["type"] == "Parent")
            nb_enfants = sum(1 for el in arbre_resultats if el["type"] == "Enfant")
            
            # Construction d'un message clair et pro pour la démo Teams
            texte_popup = (
                f"Parsing réussi !\n\n"
                f"🔹 Nombre de structures (Parents) : {nb_parents}\n"
                f"🔸 Nombre de données (Enfants) : {nb_enfants}\n\n"
                f"Total : {len(arbre_resultats)} éléments identifiés."
            )
            
            # Affichage de la pop-up avec les deux compteurs séparés
            messagebox.showinfo("Résultat du Parser", texte_popup)

            # Envoi de la structure complète à votre binôme
            if self.on_parse_callback is not None:
                self.on_parse_callback(arbre_resultats)

        except Exception as e:
            messagebox.showerror("Erreur de format", f"Le flux hexadécimal est mal formé : {e}")

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
    
    mes_boutons = ButtonsPanel(root_test, input_panel_reference=mon_input)
    mes_boutons.pack(fill="x", padx=15, pady=5)
    
    root_test.mainloop()