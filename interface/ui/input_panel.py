import customtkinter as ctk
from tkinter import messagebox

class InputPanel(ctk.CTkFrame):
    """
    Panneau de saisie unique optimisé pour le copier-coller de logs monétiques.
    Prend en charge les chaînes de toutes tailles (de 5 à plus de 1000 octets).
    """
    def __init__(self, parent):
        super().__init__(parent, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)

        # 1. En-tête (Titre du panneau)
        ctk.CTkLabel(
            self,
            text="Saisie du message TLV brut",
            font=("Consolas", 15, "bold"),
            anchor="w"
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        # 2. Zone de texte principale pour le copier-coller
        self.text_input = ctk.CTkTextbox(
            self,
            height=180,
            font=("Consolas", 13),
            wrap="char",
            border_width=1
        )
        self.text_input.grid(row=1, column=0, padx=14, pady=4, sticky="ew")

        self.text_input.focus_set()

 

    # --- API PUBLIQUE POUR L'ORCHESTRATEUR (app.py) ---
    def get_hex(self):
        """Retourne le flux hexadécimal propre nettoyé pour le backend."""
        raw_text = self.text_input.get("1.0", "end-1c")
        return raw_text.replace(" ", "").replace("\n", "").replace("\r", "").replace("\t", "").upper()

    def set_hex(self, new_hex):
        """Permet d'injecter une nouvelle chaîne suite au bouton Generate."""
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", new_hex.upper())
   

    def clear(self):
        """Vide la zone de saisie."""
        self.text_input.delete("1.0", "end")
