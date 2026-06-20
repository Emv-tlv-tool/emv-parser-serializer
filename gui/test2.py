import customtkinter as ctk
from tkinter import ttk
import re, json, os

_JSON_PATH = os.path.join(os.path.dirname(__file__), "tags (4).json")

with open(_JSON_PATH, "r", encoding="utf-8") as _f:
    _RAW = json.load(_f)
TAGS_DB = {t["poseidon_tag"]: t for t in _RAW if t.get("poseidon_tag")}

def get_tag_info(tag: str) -> dict:
    return TAGS_DB.get(tag.upper(), {
        "name": "Tag inconnu",
        "value_format": "binary",
        "child_tags": [],
        "parent_tags": []
    })

def is_constructed_from_json(tag: str) -> bool:
    """Vérifie si un tag est construit via child_tags dans tags.json."""
    info = TAGS_DB.get(tag.upper(), {})
    return len(info.get("child_tags", [])) > 0

COLORS = {
    "bg":       "#F5F5F5",
    "surface":  "#FFFFFF",
    "border":   "#CCCCCC",
    "accent":   "#1E88E5",
    "text":     "#000000",
    "hover":    "#E0E0E0",
    "selected": "#BBDEFB",
    "ok":       "#43A047",
    "error":    "#E53935",
    "muted":    "#666666",
}

class MockNode:
    def __init__(self, tag, value_hex, is_constructed):
        self.tag            = tag
        self.value_hex      = value_hex
        self.is_constructed = is_constructed
        self.children       = []
        self.length         = len(value_hex) // 2 if not is_constructed else 0

    def update_length(self):
        if self.is_constructed:
            total = 0
            for child in self.children:
                child.update_length()
                total += child.length
            self.length = total

    def to_bytes(self) -> bytes:
        if self.is_constructed:
            value = b''.join(c.to_bytes() for c in self.children)
        else:
            value = bytes.fromhex(self.value_hex)
        tag_b  = bytes.fromhex(self.tag)
        length = len(value)
        if length < 128:
            len_b = bytes([length])
        elif length < 256:
            len_b = bytes([0x81, length])
        else:
            len_b = bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
        return tag_b + len_b + value


def parse_tlv(hex_str: str):
 
    clean = hex_str.replace(" ", "").replace("\n", "").upper()
    if not clean:
        return [], "Champ vide"
    if len(clean) % 2 != 0:
        clean = clean[:-1]
    try:
        data = bytes.fromhex(clean)
    except ValueError as e:
        return [], f"Hex invalide : {e}"
    return _parse_bytes(data), None


def _parse_bytes(data: bytes) -> list:
    nodes = []
    i = 0
    while i < len(data):
        if i >= len(data): break

        first = data[i]; i += 1
        tag_bytes = [first]
        if (first & 0x1F) == 0x1F:
            while i < len(data) and (data[i] & 0x80):
                tag_bytes.append(data[i]); i += 1
            if i < len(data):
                tag_bytes.append(data[i]); i += 1
        tag = ''.join(f'{b:02X}' for b in tag_bytes)

        # ── Lire LONGUEUR
        if i >= len(data): break
        b = data[i]; i += 1
        if b < 0x80:
            length = b
        elif b == 0x81:
            if i >= len(data): break
            length = data[i]; i += 1
        elif b == 0x82:
            if i + 1 >= len(data): break
            length = (data[i] << 8) | data[i + 1]; i += 2
        else:
            break

        # ── Lire VALEUR
        if i + length > len(data):
            length = len(data) - i
        val_bytes = data[i:i + length]; i += length

        
        # Priorité 1 : bit 6 du premier octet (standard EMV)
        is_constr_bit = bool(first & 0x20)
        # Priorité 2 : child_tags dans tags.json
        is_constr_json = is_constructed_from_json(tag)
        is_constructed = is_constr_bit or is_constr_json

        node = MockNode(tag, val_bytes.hex().upper(), is_constructed)
        node.length = length

        # ── Récursion si construit ───────────────────────────
        if is_constructed:
            node.children = _parse_bytes(val_bytes)

        nodes.append(node)
    return nodes

class TreeRow(ctk.CTkFrame):
    def __init__(self, master, node: MockNode, depth: int,
                 on_toggle, on_edit_done, on_select, **kwargs):
        super().__init__(master, fg_color="transparent",
                         corner_radius=0, **kwargs)
        self.node         = node
        self.depth        = depth
        self.on_toggle    = on_toggle
        self.on_edit_done = on_edit_done
        self.on_select    = on_select
        self.is_open      = False
        self._entry       = None
        self.selected     = False
        self._build()
        self.bind("<Button-1>", self._on_click)

    def _build(self):
        info     = get_tag_info(self.node.tag)
        tag_name = info.get("name", "Tag inconnu")
        indent   = self.depth * 24

        self._inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._inner.pack(fill="x", padx=(indent, 0), pady=1)
        self._inner.bind("<Button-1>", self._on_click)

        # Triangle
        if self.node.is_constructed:
            self.btn_triangle = ctk.CTkButton(
                self._inner, text="▶",
                width=24, height=24,
                font=ctk.CTkFont("Helvetica", 11),
                fg_color="transparent",
                hover_color=COLORS["hover"],
                text_color=COLORS["muted"],
                corner_radius=4,
                command=self._do_toggle
            )
            self.btn_triangle.pack(side="left", padx=(0, 4))
        else:
            ctk.CTkLabel(self._inner, text="  ", width=24).pack(side="left", padx=(0, 4))

        # Badge tag
        self.lbl_tag = ctk.CTkLabel(
            self._inner,
            text=f"[{self.node.tag}]",
            font=ctk.CTkFont("Courier", 13, "bold"),
            text_color=COLORS["accent"],
            width=80, anchor="w"
        )
        self.lbl_tag.pack(side="left", padx=(0, 6))
        self.lbl_tag.bind("<Button-1>", self._on_click)

        self.text_frame = ctk.CTkFrame(self._inner, fg_color="transparent")
        self.text_frame.pack(side="left", fill="x", expand=True)

        # Libellé "Name:" (gras)
        self.lbl_name_label = ctk.CTkLabel(
            self.text_frame,
            text="Name: ",
            font=ctk.CTkFont("Courier", 14, "bold"),
            text_color=COLORS["text"],
            anchor="w"
        )
        self.lbl_name_label.pack(side="left")

        # Valeur du nom (normal)
        self.lbl_name_value = ctk.CTkLabel(
            self.text_frame,
            text=tag_name,
            font=ctk.CTkFont("Courier", 14),
            text_color=COLORS["text"],
            anchor="w"
        )
        self.lbl_name_value.pack(side="left")

        self.lbl_taille_label = ctk.CTkLabel(
            self.text_frame,
            text=" — Taille: ",
            font=ctk.CTkFont("Courier", 14, "bold"),
            text_color=COLORS["text"],
            anchor="w"
        )
        self.lbl_taille_label.pack(side="left")

        # Valeur de la taille (normal)
        self.lbl_taille_value = ctk.CTkLabel(
            self.text_frame,
            text=f"{self.node.length} octets",
            font=ctk.CTkFont("Courier", 13),
            text_color=COLORS["text"],
            anchor="w"
        )
        self.lbl_taille_value.pack(side="left")

        # Si primitif → ajouter " — Value:" + valeur hex
        if not self.node.is_constructed:
            self.lbl_value_label = ctk.CTkLabel(
                self.text_frame,
                text=" — Value: ",
                font=ctk.CTkFont("Courier", 14, "bold"),
                text_color=COLORS["text"],
                anchor="w"
            )
            self.lbl_value_label.pack(side="left")

            self.lbl_value_value = ctk.CTkLabel(
                self.text_frame,
                text=self.node.value_hex,
                font=ctk.CTkFont("Courier", 12),
                text_color=COLORS["text"],
                anchor="w"
            )
            self.lbl_value_value.pack(side="left")
            self.lbl_value_value.bind("<Double-1>", self._on_double_click)
        else:
            self.lbl_value_label = None
            self.lbl_value_value = None

        self._inner.bind("<Enter>", lambda e: self._on_hover_in())
        self._inner.bind("<Leave>", lambda e: self._on_hover_out())

    def _do_toggle(self):
        self.is_open = not self.is_open
        self.btn_triangle.configure(text="▼" if self.is_open else "▶")
        self.on_toggle(self, self.is_open)


    def _on_click(self, event=None):
        self.on_select(self)

    def _on_hover_in(self):
        if not self.selected:
            self._inner.configure(fg_color=COLORS["hover"])

    def _on_hover_out(self):
        if not self.selected:
            self._inner.configure(fg_color="transparent")

    def set_selected(self, sel):
        self.selected = sel
        self._inner.configure(fg_color=COLORS["selected"] if sel else "transparent")

    def _on_double_click(self, event=None):
        if self.node.is_constructed:
            self.on_edit_done(self.node, None, "constructed")
            return
        self._start_edit()

    def _start_edit(self):
        if self._entry:
            return

        if self.lbl_value_label:
            self.lbl_value_label.pack_forget()
        if self.lbl_value_value:
            self.lbl_value_value.pack_forget()

        info = get_tag_info(self.node.tag)
        tag_name = info.get("name", "Tag inconnu")

        prefix = f"Name: {tag_name} — Taille: {self.node.length} octets — Value: "
        self.lbl_prefix = ctk.CTkLabel(
            self.text_frame,
            text=prefix,
            font=ctk.CTkFont("Courier", 12, "bold"),
            text_color=COLORS["text"],
            anchor="w"
        )
        self.lbl_prefix.pack(side="left")

        self._entry = ctk.CTkEntry(
            self.text_frame,
            font=ctk.CTkFont("Courier", 12),
            fg_color=COLORS["bg"],
            border_color=COLORS["accent"],
            text_color=COLORS["accent"],
            width=200, height=24
        )
        self._entry.insert(0, self.node.value_hex)
        self._entry.select_range(0, "end")
        self._entry.pack(side="left", padx=(0, 8))
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._commit_edit())
        self._entry.bind("<FocusOut>", lambda e: self._commit_edit())
        self._entry.bind("<Escape>", lambda e: self._cancel_edit())

    def _commit_edit(self):
        if not self._entry:
            return
        new_val = self._entry.get().strip().upper()
        self._cleanup_entry()
        if not re.fullmatch(r'[0-9A-F]+', new_val) or len(new_val) % 2 != 0:
            self.on_edit_done(self.node, None, "error")
            return
        self.node.value_hex = new_val
        self.node.length = len(new_val) // 2
        if self.lbl_value_label:
            self.lbl_value_label.pack(side="left")
        if self.lbl_value_value:
            self.lbl_value_value.configure(text=new_val)
            self.lbl_value_value.pack(side="left")
        self.on_edit_done(self.node, new_val, "ok")

    def _cancel_edit(self):
        if not self._entry:
            return
        self._cleanup_entry()
        if self.lbl_value_label:
            self.lbl_value_label.pack(side="left")
        if self.lbl_value_value:
            self.lbl_value_value.pack(side="left")

    def _cleanup_entry(self):
        if self._entry:
            self._entry.destroy()
            self._entry = None
        if hasattr(self, "lbl_prefix"):
            self.lbl_prefix.destroy()
            del self.lbl_prefix


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("EMV TLV Parser")
        self.geometry("1200x800")
        self.configure(fg_color=COLORS["bg"])

        self._rows         = []
        self._selected_row = None
        self._root_nodes   = []

        self._build_header()
        self._build_input_area()
        self._build_buttons()
        self._build_tree_zone()
        self._build_statusbar()

    def _build_header(self):
        h = ctk.CTkFrame(self, height=46, fg_color=COLORS["surface"], corner_radius=0)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkLabel(h, text="💳  EMV TLV Parser",
                     font=ctk.CTkFont("Helvetica", 15, "bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=20)
        ctk.CTkLabel(h, text=f"— {len(TAGS_DB)} tags chargés depuis tags.json",
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color=COLORS["muted"]).pack(side="left")


    def _build_input_area(self):
        frame = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(top, text="Message TLV (hex) :",
                     font=ctk.CTkFont("Helvetica", 12)).pack(side="left")
        self.lbl_bytes = ctk.CTkLabel(top, text="0 bytes",
                                       font=ctk.CTkFont("Helvetica", 10),
                                       text_color=COLORS["muted"])
        self.lbl_bytes.pack(side="right")

        self.entry_tlv = ctk.CTkEntry(
            frame,
            placeholder_text="Collez votre TLV hex ici...",
            font=("Courier", 12)
        )
        self.entry_tlv.pack(fill="x", padx=5, pady=(0, 5))
        self.entry_tlv.bind("<KeyRelease>", self._on_input_key)

    def _on_input_key(self, event=None):
        raw = self.entry_tlv.get().replace(" ", "")
        self.lbl_bytes.configure(text=f"{len(raw)//2} bytes")

    def _build_buttons(self):
        bar = ctk.CTkFrame(self, height=50, fg_color=COLORS["surface"], corner_radius=0)
        bar.pack(fill="x", pady=(1, 0))
        bar.pack_propagate(False)

        ctk.CTkButton(bar, text=" Parser",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      fg_color="#0077B6", hover_color="#005F8E",
                      width=130, height=34,
                      command=self._do_parse
                      ).pack(side="left", padx=(14, 6), pady=8)

        ctk.CTkButton(bar, text="  Effacer",
                      font=ctk.CTkFont("Helvetica", 12),
                      fg_color=COLORS["surface"],
                      border_color=COLORS["border"], border_width=1,
                      hover_color=COLORS["hover"],
                      text_color=COLORS["muted"],
                      width=120, height=34,
                      command=self._do_clear
                      ).pack(side="left", padx=6, pady=8)

        ctk.CTkButton(bar, text=" Générer",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      fg_color="#238636", hover_color="#2EA043",
                      width=150, height=34,
                      command=self._do_generate
                      ).pack(side="left", padx=6, pady=8)

    def _build_tree_zone(self):
        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        outer.pack(fill="both", expand=True, pady=(1, 0))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        self._canvas = ctk.CTkCanvas(outer, bg=COLORS["bg"], highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        sv = ttk.Scrollbar(outer, orient="vertical",   command=self._canvas.yview)
        sh = ttk.Scrollbar(outer, orient="horizontal", command=self._canvas.xview)
        sv.grid(row=0, column=1, sticky="ns")
        sh.grid(row=1, column=0, sticky="ew")
        self._canvas.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)

        self._tree_frame = ctk.CTkFrame(self._canvas, fg_color=COLORS["bg"], corner_radius=0)
        self._cw = self._canvas.create_window((0, 0), window=self._tree_frame, anchor="nw")

        self._tree_frame.bind("<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        # ⚠️ Correction : on ne force plus la largeur du frame à celle du Canvas
        # self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfig(self._cw, width=e.width))
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=28, fg_color=COLORS["surface"], corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._lbl_status = ctk.CTkLabel(
            bar, text="Prêt",
            font=ctk.CTkFont("Helvetica", 10),
            text_color=COLORS["muted"], anchor="w"
        )
        self._lbl_status.pack(side="left", padx=14, pady=4)

    def _set_status(self, msg, level="ready"):
        c = {"ready": COLORS["muted"], "ok": COLORS["ok"],
             "error": COLORS["error"], "warn": "#FDD835"}
        self._lbl_status.configure(text=msg, text_color=c.get(level, COLORS["muted"]))

    def _build_tree_rows(self, nodes, parent_row=None, depth=0):
        for node in nodes:
            row = TreeRow(self._tree_frame, node, depth,
                          on_toggle=self._on_toggle,
                          on_edit_done=self._on_edit_done,
                          on_select=self._on_select_row)
            row.pack(fill="x", pady=0)
            row._child_rows = []
            row._parent_row = parent_row
            self._rows.append(row)
            if node.children:
                child_rows = self._build_tree_rows_list(node.children, row, depth + 1)
                row._child_rows = child_rows
                for cr in child_rows:
                    cr.pack_forget()

    def _build_tree_rows_list(self, nodes, parent_row, depth):
        result = []
        for node in nodes:
            row = TreeRow(self._tree_frame, node, depth,
                          on_toggle=self._on_toggle,
                          on_edit_done=self._on_edit_done,
                          on_select=self._on_select_row)
            row._child_rows = []
            row._parent_row = parent_row
            self._rows.append(row)
            if node.children:
                row._child_rows = self._build_tree_rows_list(node.children, row, depth + 1)
            result.append(row)
        return result


    def _on_toggle(self, row, is_open):
        if is_open: self._show_children(row)
        else:       self._hide_children(row)

    def _show_children(self, row):
        for i, cr in enumerate(row._child_rows):
            cr.pack(fill="x", pady=0,
                    after=row if i == 0 else row._child_rows[i - 1])
            if cr.is_open:
                self._show_children(cr)

    def _hide_children(self, row):
        for cr in row._child_rows:
            self._hide_children(cr)
            cr.pack_forget()

    def _on_select_row(self, row):
        if self._selected_row and self._selected_row != row:
            self._selected_row.set_selected(False)
        row.set_selected(True)
        self._selected_row = row
        info = get_tag_info(row.node.tag)
        self._set_status(
            f"Sélectionné : [{row.node.tag}]  {info['name']}  —  "
            f"format: {info.get('value_format','?')}  —  "
            f"taille: {row.node.length} octets",
            "ready"
        )

    def _on_edit_done(self, node, new_val, level):
        if level == "ok":
            self._set_status(
                f"  Valeur modifiée [{node.tag}] → {new_val}  |  cliquez sur Générer", "ok")
        elif level == "constructed":
            self._set_status(
                f"  Modification non autorisée pour tag construit [{node.tag}]", "warn")
        else:
            self._set_status(
                " Hex invalide — utiliser 0-9 A-F, nombre pair de chiffres", "error")

    def _do_parse(self):
        tlv_hex = self.entry_tlv.get().strip()
        if not tlv_hex:
            self._set_status("⚠  Veuillez entrer un TLV hexadécimal", "error")
            return

        nodes, err = parse_tlv(tlv_hex)
        if err:
            self._set_status(f"  {err}", "error")
            return
        if not nodes:
            self._set_status(" Aucun tag trouvé dans ce message", "error")
            return

        self._do_clear_tree()
        self._root_nodes = nodes
        self._build_tree_rows(nodes)

        total = sum(1 for _ in self._flatten(nodes))
        nb    = len(tlv_hex.replace(" ", "")) // 2
        self._set_status(
            f"  Parsing réussi — {total} tags trouvés, {nb} bytes", "ok")
        self.lbl_bytes.configure(text=f"{nb} bytes")


    def _do_clear(self):
        self.entry_tlv.delete(0, "end")
        self.lbl_bytes.configure(text="0 bytes")
        self._do_clear_tree()
        self._set_status("Prêt", "ready")

    def _do_clear_tree(self):
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._selected_row = None
        self._root_nodes   = []

    def _do_generate(self):
        if not self._root_nodes:
            self._set_status("  Aucun arbre — parser d'abord", "error")
            return
        try:
            new_bytes = b''.join(n.to_bytes() for n in self._root_nodes)
            new_hex   = new_bytes.hex().upper()
            self.entry_tlv.delete(0, "end")
            self.entry_tlv.insert(0, new_hex)
            self.lbl_bytes.configure(text=f"{len(new_bytes)} bytes")
            self._set_status(
                f"  TLV généré — {len(new_bytes)} bytes — zone de saisie mise à jour", "ok")
        except Exception as e:
            self._set_status(f"  Erreur génération : {e}", "error")


    def _flatten(self, nodes):
        for n in nodes:
            yield n
            yield from self._flatten(n.children)


if __name__ == "__main__":
    app = App()
    app.mainloop()