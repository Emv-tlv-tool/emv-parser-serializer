import customtkinter as ctk
from tkinter import ttk
import re

MOCK_TAGS_DICT = {
    "E0":   {"name": "Terminal Config",       "value_format": "constructed"},
    "E1":   {"name": "RID Config",            "value_format": "constructed"},
    "9F1A": {"name": "Country Code",          "value_format": "numeric"},
    "DF1B": {"name": "Terminal Currency",     "value_format": "numeric"},
    "9F33": {"name": "Terminal Capabilities", "value_format": "bitmask"},
    "9A":   {"name": "Transaction Date",      "value_format": "date"},
    "9C":   {"name": "Transaction Type",      "value_format": "enum"},
    "5A":   {"name": "PAN",                   "value_format": "string"},
    "9F02": {"name": "Amount",                "value_format": "numeric"},
    "F1":   {"name": "Mag Stripe Config",     "value_format": "constructed"},
    "DF01": {"name": "ZKA Mag Config",        "value_format": "constructed"},
    "DF04": {"name": "ZKA Mag Rule",          "value_format": "constructed"},
    "9F4E": {"name": "Merchant Name",         "value_format": "string"},
    "DF1C": {"name": "Currency Exponent",     "value_format": "numeric"},
    "9F35": {"name": "Terminal Type",         "value_format": "numeric"},
}

COLORS = {
    "bg":       "#F5F5F5",
    "surface":  "#FFFFFF",
    "border":   "#CCCCCC",
    "accent":   "#1E88E5",
    "text":     "#000000",
}

def tag_color(tag: str) -> str:
    return "#000000"

class MockNode:
    def __init__(self, tag, value_hex, is_constructed):
        self.tag            = tag
        self.value_hex      = value_hex
        self.is_constructed = is_constructed
        self.children       = []
        self.length         = len(value_hex) // 2 if not is_constructed else 0
    def to_bytes(self) -> bytes:
        if self.is_constructed:
            value = b''.join(child.to_bytes() for child in self.children)
        else:

                value = bytes.fromhex(self.value_hex)

        tag_bytes = bytes.fromhex(self.tag)
        length = len(value)
        if length < 128:
            len_bytes = bytes([length])
        elif length < 256:
            len_bytes = bytes([0x81, length])
        else:
            len_bytes = bytes([0x82,
                               (length >> 8) & 0xFF,
                               length & 0xFF])

        return tag_bytes + len_bytes + value


class TreeRow(ctk.CTkFrame):
    def __init__(self, master, node: MockNode, depth: int,
                 on_toggle, on_edit_done, on_select, **kwargs):
        super().__init__(master,
                         fg_color="transparent",
                         corner_radius=0,
                         **kwargs)

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
        info     = MOCK_TAGS_DICT.get(self.node.tag, {"name": "Tag inconnu"})
        tag_name = info.get("name", "Tag inconnu")
        indent   = self.depth * 24

        inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        inner.pack(fill="x", padx=(indent, 0), pady=1)
        inner.bind("<Button-1>", self._on_click)

        if self.node.is_constructed:
            self.btn_triangle = ctk.CTkButton(
                inner,
                text="▶",
                width=24, height=24,
                font=ctk.CTkFont("Helvetica", 11),
                fg_color="transparent",
                hover_color="#E0E0E0",
                text_color="#666666",
                corner_radius=4,
                command=self._do_toggle
            )
            self.btn_triangle.pack(side="left", padx=(0, 4))
        else:
            ctk.CTkLabel(inner, text="  ", width=24).pack(side="left", padx=(0, 4))

        self.lbl_tag = ctk.CTkLabel(
            inner,
            text=f"[{self.node.tag}]",
            font=ctk.CTkFont("Courier", 15, "bold"),
            text_color=tag_color(self.node.tag),
            width=70,
            anchor="w"
        )
        self.lbl_tag.pack(side="left", padx=(0, 6))
        self.lbl_tag.bind("<Button-1>", self._on_click)

        if self.node.is_constructed:
            txt   = f"name: {tag_name}   —   taille: {self.node.length} octets"
            color = COLORS["text"]
        else:
            txt   = (f"name: {tag_name}   —   "
                     f"taille: {self.node.length} octets   —   "
                     f"value: {self.node.value_hex}")
            color = COLORS["text"]

        self.lbl_text = ctk.CTkLabel(
            inner,
            text=txt,
            font=ctk.CTkFont("Courier", 13, "bold"),
            text_color=color,
            anchor="w"
        )
        self.lbl_text.pack(side="left", fill="x", expand=True)
        self.lbl_text.bind("<Button-1>", self._on_click)
        self.lbl_text.bind("<Double-1>", self._on_double_click)

        self._inner = inner
        inner.bind("<Enter>", self._on_hover_in)
        inner.bind("<Leave>", self._on_hover_out)

    def _do_toggle(self):
        self.is_open = not self.is_open
        self.btn_triangle.configure(text="▼" if self.is_open else "▶")
        self.on_toggle(self, self.is_open)

    def _on_click(self, event=None):
        self.on_select(self)

    def _on_double_click(self, event=None):
        if self.node.is_constructed:
            return
        self._start_edit()

    def _on_hover_in(self, event=None):
        if not self.selected:
            self._inner.configure(fg_color="#E0E0E0")

    def _on_hover_out(self, event=None):
        if not self.selected:
            self._inner.configure(fg_color="transparent")

    def set_selected(self, sel: bool):
        self.selected = sel
        self._inner.configure(fg_color="#BBDEFB" if sel else "transparent")

    def _start_edit(self):
        if self._entry:
            return
        self.lbl_text.pack_forget()
        info     = MOCK_TAGS_DICT.get(self.node.tag, {"name": "Tag inconnu"})
        tag_name = info.get("name", "Tag inconnu")
        prefix   = f"name: {tag_name}   —   taille: {self.node.length} octets   —   value: "

        self.lbl_prefix = ctk.CTkLabel(
            self._inner, text=prefix,
            font=ctk.CTkFont("Courier", 11, "bold"),
            text_color=COLORS["text"], anchor="w"
        )
        self.lbl_prefix.pack(side="left")

        self._entry = ctk.CTkEntry(
            self._inner,
            font=ctk.CTkFont("Courier", 11),
            fg_color=COLORS["bg"],
            border_color=COLORS["accent"],
            text_color=COLORS["accent"],
            width=180, height=24
        )
        self._entry.insert(0, self.node.value_hex)
        self._entry.select_range(0, "end")
        self._entry.pack(side="left", padx=(0, 8))
        self._entry.focus_set()

        self._entry.bind("<Return>",   lambda e: self._commit_edit())
        self._entry.bind("<FocusOut>", lambda e: self._commit_edit())
        self._entry.bind("<Escape>",   lambda e: self._cancel_edit())

    def _commit_edit(self):
        if not self._entry:
            return
        new_val = self._entry.get().strip().upper()
        self._cleanup_entry()

        if not re.fullmatch(r'[0-9A-F]+', new_val) or len(new_val) % 2 != 0:
            self.on_edit_done(self.node, None, "error")
            return

        self.node.value_hex = new_val
        self.node.length    = len(new_val) // 2

        info     = MOCK_TAGS_DICT.get(self.node.tag, {"name": "Tag inconnu"})
        tag_name = info.get("name", "Tag inconnu")
        self.lbl_text.configure(
            text=f"name: {tag_name}   —   "
                 f"taille: {self.node.length} octets   —   "
                 f"value: {new_val}"
        )
        self.lbl_text.pack(side="left", fill="x", expand=True)
        self.on_edit_done(self.node, new_val, "ok")

    def _cancel_edit(self):
        if not self._entry:
            return
        self._cleanup_entry()
        self.lbl_text.pack(side="left", fill="x", expand=True)

    def _cleanup_entry(self):
        if self._entry:
            self._entry.destroy()
            self._entry = None
        if hasattr(self, "lbl_prefix"):
            self.lbl_prefix.destroy()
            del self.lbl_prefix

    def refresh_text(self):
        info     = MOCK_TAGS_DICT.get(self.node.tag, {"name": "Tag inconnu"})
        tag_name = info.get("name", "Tag inconnu")
        if self.node.is_constructed:
            self.lbl_text.configure(
                text=f"name: {tag_name}   —   taille: {self.node.length} octets"
            )
        else:
            self.lbl_text.configure(
                text=f"name: {tag_name}   —   "
                     f"taille: {self.node.length} octets   —   "
                     f"value: {self.node.value_hex}"
            )


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
        ctk.CTkLabel(h, text=" EMV TLV Parser",
                     font=ctk.CTkFont("Helvetica", 15, "bold"),
                     text_color=COLORS["accent"]).pack(side="left", padx=20)

    def _build_input_area(self):
        frame = ctk.CTkFrame(self, fg_color=COLORS["surface"], corner_radius=0)
        frame.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(frame, text="Message TLV (hex) :", anchor="w",
                     font=ctk.CTkFont("Helvetica", 12)).pack(fill="x", padx=5, pady=(5, 0))

        self.entry_tlv = ctk.CTkEntry(
            frame,
            placeholder_text="Collez votre TLV hex ici...",
            font=("Courier", 12)
        )
        self.entry_tlv.pack(fill="x", padx=5, pady=(0, 5))

    def _build_buttons(self):
        bar = ctk.CTkFrame(self, height=50, fg_color=COLORS["surface"], corner_radius=0)
        bar.pack(fill="x", pady=(1, 0))
        bar.pack_propagate(False)

        ctk.CTkButton(bar, text="  Parser",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      fg_color="#0077B6", hover_color="#005F8E",
                      width=130, height=34,
                      command=self._do_parse).pack(side="left", padx=(14, 6), pady=8)

        ctk.CTkButton(bar, text="  Effacer",
                      font=ctk.CTkFont("Helvetica", 12),
                      fg_color=COLORS["surface"],
                      border_color=COLORS["border"], border_width=1,
                      hover_color=COLORS["border"],
                      text_color="#666666",
                      width=120, height=34,
                      command=self._do_clear).pack(side="left", padx=6, pady=8)

        ctk.CTkButton(bar, text="  Générer",
                      font=ctk.CTkFont("Helvetica", 12, "bold"),
                      fg_color="#238636", hover_color="#2EA043",
                      width=150, height=34,
                      command=self._do_generate).pack(side="left", padx=6, pady=8)

    def _build_tree_zone(self):
        outer = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        outer.pack(fill="both", expand=True, pady=(1, 0))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        self._canvas = ctk.CTkCanvas(outer, bg=COLORS["bg"], highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._sv = ttk.Scrollbar(outer, orient="vertical",   command=self._canvas.yview)
        self._sv.grid(row=0, column=1, sticky="ns")
        self._sh = ttk.Scrollbar(outer, orient="horizontal", command=self._canvas.xview)
        self._sh.grid(row=1, column=0, sticky="ew")

        self._canvas.configure(yscrollcommand=self._sv.set, xscrollcommand=self._sh.set)

        self._tree_frame = ctk.CTkFrame(self._canvas, fg_color=COLORS["bg"], corner_radius=0)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._tree_frame, anchor="nw"
        )

        self._tree_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",     self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"))

    def _on_frame_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=28, fg_color=COLORS["surface"], corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._lbl_status = ctk.CTkLabel(
            bar, text="Prêt",
            font=ctk.CTkFont("Helvetica", 10),
            text_color="#666666", anchor="w"
        )
        self._lbl_status.pack(side="left", padx=14, pady=4)

    def _set_status(self, msg, level="ready"):
        colors = {
            "ready": "#666666",
            "ok":    "#43A047",
            "error": "#E53935",
            "warn":  "#FDD835"
        }
        self._lbl_status.configure(text=msg, text_color=colors.get(level, "#666666"))

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
                child_rows = self._build_tree_rows_list(node.children, row, depth + 1)
                row._child_rows = child_rows
            result.append(row)
        return result

    def _on_toggle(self, row, is_open):
        if is_open:
            self._show_children(row)
        else:
            self._hide_children(row)

    def _show_children(self, row):
        for i, child_row in enumerate(row._child_rows):
            child_row.pack(fill="x", pady=0,
                           after=row if i == 0 else row._child_rows[i - 1])
            if child_row.is_open:
                self._show_children(child_row)

    def _hide_children(self, row):
        for child_row in row._child_rows:
            self._hide_children(child_row)
            child_row.pack_forget()

    def _on_select_row(self, row):
        if self._selected_row and self._selected_row != row:
            self._selected_row.set_selected(False)
        row.set_selected(True)
        self._selected_row = row
        info = MOCK_TAGS_DICT.get(row.node.tag, {"name": "Tag inconnu"})
        self._set_status(
            f"Sélectionné : [{row.node.tag}]  {info['name']}  —  taille: {row.node.length} octets",
            "ready"
        )

    def _on_edit_done(self, node, new_val, level):
        if level == "ok":
            self._set_status(
                f" Valeur modifiée [{node.tag}] → {new_val}  |  cliquez sur Générer",
                "ok"
            )
        else:
            self._set_status(
                "  Hex invalide — utiliser 0-9 A-F, nombre pair de chiffres",
                "error"
            )

    def _do_parse(self):
        tlv_hex = self.entry_tlv.get().strip().replace(" ", "").upper()
        if not tlv_hex:
            self._set_status("⚠  Veuillez entrer un TLV hexadécimal", "error")
            return

        self._do_clear()


        e0 = MockNode("E0", "", True)
        e0.children = [
            MockNode("9F1A", "0280",                 False),
            MockNode("DF1B", "0978",                 False),
            MockNode("9F33", "60F8C8",               False),
            MockNode("9A",   "210315",               False),
            MockNode("9C",   "00",                   False),
            MockNode("5A",   "4276123456789012FFFF", False),
            MockNode("9F02", "000000010000",         False),
        ]
        f1   = MockNode("F1",   "", True)
        df01 = MockNode("DF01", "", True)
        df04 = MockNode("DF04", "00",False)
        df01.children = [MockNode("9F4E", "42535061796F6E65", False)]
        f1.children   = [df01, df04]

        e1 = MockNode("E1", "", True)
        e1.children   = [
            MockNode("DF1B", "0978", False),
            MockNode("DF1C", "02",   False),
        ]

        self._root_nodes = [e0, f1, e1]
        self._build_tree_rows(self._root_nodes)

        total = sum(1 for n in self._flatten(self._root_nodes))
        self._set_status(f"  Parsing réussi — {total} tags", "ok")

    def _do_clear(self):
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._selected_row = None
        self._root_nodes   = []
        self._set_status("Prêt", "ready")


    def _do_generate(self):
        if not self._root_nodes:
            self._set_status(" Aucun arbre — parser d'abord", "error")
            return
        try:

            new_bytes = b''.join(node.to_bytes() for node in self._root_nodes)
            new_hex   = new_bytes.hex().upper()


            self.entry_tlv.delete(0, "end")
            self.entry_tlv.insert(0, new_hex)

            self._set_status(
                f" TLV généré — {len(new_bytes)} bytes — message mis à jour",
                "ok"
            )
        except Exception as e:
            self._set_status(f"  Erreur génération : {e}", "error")

    def _flatten(self, nodes):
        for n in nodes:
            yield n
            yield from self._flatten(n.children)


if __name__ == "__main__":
    app = App()
    app.mainloop()