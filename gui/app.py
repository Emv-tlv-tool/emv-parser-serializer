import os
import threading
import queue
import sys
import re
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from emv_tlv import parse, serialize, validate_hex, Dictionary, TLVNode


def hex_bytes_to_decimals(value_hex: str) -> str:
    if not value_hex or len(value_hex) % 2 != 0:
        return ""
    bytes_list = [str(int(value_hex[i:i+2], 16)) for i in range(0, len(value_hex), 2)]
    return " ".join(bytes_list)

UI_FONT   = "helvetica"
MONO_FONT = "courier"

COLORS = {
    "bg":         "#F8F9FA",
    "surface":    "#FFFFFF",
    "border":     "#E5E7EB",
    "accent":     "#2563EB",
    "text":       "#1F2937",
    "text_muted": "#6B7280",
    "danger":     "#DC2626",
    "success":    "#059669",
    "hover":      "#F3F4F6",
    "select":     "#DBEAFE",
}


def get_node_display_length(node: TLVNode) -> int:
    if not node.is_constructed:
        return node.length
    try:
        return len(serialize(node.children)) // 2
    except Exception:
        return node.length


class BitmaskPseudoNode:
    def __init__(self, text, is_constructed=False):
        self.tag = ""
        self.name = ""
        self.length = 0
        self.is_constructed = is_constructed
        self.is_valid_parent = True
        self.parent_validation_error = None
        self.text = text
        self.value = b""
        self.children = []


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("EMV TLV Parser")
        self.geometry("1200x800")
        self.configure(fg_color=COLORS["bg"])

        self._root_nodes = []
        self._node_map   = {}
        self._edit_entry = None
        self._edit_frame = None

        self._build_header()
        self._build_input_area()
        self._build_buttons()
        self._build_tree_zone()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self._immediate_close)

    def _immediate_close(self):
        self.withdraw()
        self.quit()
        self.destroy()

    def _build_header(self):
        h = ctk.CTkFrame(self, height=50, fg_color=COLORS["surface"], corner_radius=0)
        h.pack(fill="x")
        h.pack_propagate(False)
        ctk.CTkFrame(h, height=1, fg_color=COLORS["border"]).pack(fill="x", side="bottom")
        ctk.CTkLabel(
            h, text="  EMV TLV Parser",
            font=ctk.CTkFont(UI_FONT, 15, "bold"),
            text_color=COLORS["accent"],
        ).pack(side="left", padx=20)

    def _build_input_area(self):
        card = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=8, border_color=COLORS["border"], border_width=1,
        )
        card.pack(fill="x", padx=15, pady=(14, 5))

        ctk.CTkLabel(
            card, text="TLV Hex Payload:", anchor="w",
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            text_color=COLORS["text_muted"],
        ).pack(fill="x", padx=14, pady=(10, 2))

        self.entry_tlv = ctk.CTkEntry(
            card,
            placeholder_text="Paste raw TLV hex here (spaces allowed)...",
            font=ctk.CTkFont(MONO_FONT, 12),
            fg_color=COLORS["surface"],
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            height=34, corner_radius=6,
        )
        self.entry_tlv.pack(fill="x", padx=14, pady=(0, 12))
        self.entry_tlv.bind("<Return>", lambda _e: self._do_parse())

    def _build_buttons(self):
        bar = ctk.CTkFrame(self, height=42, fg_color="transparent")
        bar.pack(fill="x", padx=15, pady=(0, 5))
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar, text="Parse", command=self._do_parse,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color=COLORS["accent"], hover_color="#1D4ED8",
            text_color="#fff", width=110, height=32, corner_radius=6,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            bar, text="Clear", command=self._do_clear,
            font=ctk.CTkFont(UI_FONT, 12),
            fg_color=COLORS["surface"], border_color=COLORS["border"],
            border_width=1, hover_color=COLORS["hover"],
            text_color=COLORS["text_muted"],
            width=100, height=32, corner_radius=6,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bar, text="Generate", command=self._do_generate,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color=COLORS["success"], hover_color="#047857",
            text_color="#fff", width=130, height=32, corner_radius=6,
        ).pack(side="left", padx=6)

    def _build_tree_zone(self):
        outer = tk.Frame(self, bg=COLORS["border"], bd=1, relief="flat")
        outer.pack(fill="both", expand=True, padx=15, pady=(0, 5))

        container = tk.Frame(outer, bg=COLORS["surface"])
        container.pack(fill="both", expand=True, padx=1, pady=1)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")

        # --- Augmentation de rowheight pour plus d'espace ---
        style.configure("EMV.Treeview",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            rowheight=40,               # ← ESPACEMENT AUGMENTÉ (26 → 40)
            font=(MONO_FONT, 11),
            fieldbackground=COLORS["surface"],
            borderwidth=0,
            relief="flat",
            indent=28,
        )
        style.map("EMV.Treeview",
            background=[("selected", COLORS["select"])],
            foreground=[("selected", COLORS["text"])],
        )

        style.configure("EMV.Treeview", arrowsize=13)

        self._tree = ttk.Treeview(
            container,
            style="EMV.Treeview",
            show="tree",
            selectmode="browse",
        )
        self._tree.column("#0", width=2000, minwidth=800, stretch=False)

        vsb = ttk.Scrollbar(container, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._tree.tag_configure("warn",   foreground=COLORS["danger"])
        self._tree.tag_configure("pseudo", foreground=COLORS["text_muted"],
                                 font=(MONO_FONT, 10))

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Double-1>",         self._on_double_click)

    # ------------------------------------------------------------------ #
    #  Events
    # ------------------------------------------------------------------ #
    def _on_tree_select(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        item = sel[0]
        node = self._node_map.get(item)
        if node is None:
            return
        if isinstance(node, BitmaskPseudoNode):
            self._set_status(node.text, "ready")
            return
        tag_name = node.name or "Unknown Tag"
        length = get_node_display_length(node)
        msg = f"[{node.tag}]  {tag_name}  |  {length} bytes"
        if not node.is_valid_parent:
            msg += f"  [!] {node.parent_validation_error}"
            self._set_status(msg, "warn")
        else:
            self._set_status(msg, "ready")

    def _on_double_click(self, event=None):
        region = self._tree.identify_region(event.x, event.y)
        if region not in ("tree", "cell"):
            return
        item = self._tree.identify_row(event.y)
        if not item:
            return
        node = self._node_map.get(item)
        if node is None or isinstance(node, BitmaskPseudoNode):
            return
        if node.is_constructed:
            return
        self._start_inline_edit(item, node)

    def _start_inline_edit(self, item, node):
        self._cancel_edit()
        bbox = self._tree.bbox(item, column="#0")
        if not bbox:
            return
        x, y, w, h = bbox

        self._edit_frame = tk.Frame(self._tree, bg=COLORS["accent"], bd=1)
        self._edit_frame.place(x=x + 2, y=y + 1, width=max(w - 4, 520), height=h - 2)

        self._edit_entry = tk.Entry(
            self._edit_frame,
            font=(MONO_FONT, 11),
            fg=COLORS["text"],
            bg=COLORS["surface"],
            bd=0,
            relief="flat",
            insertbackground=COLORS["text"],
            selectbackground=COLORS["accent"],
            selectforeground="#FFFFFF",
        )
        self._edit_entry.pack(fill="both", expand=True, padx=3, pady=2)
        self._edit_entry.insert(0, node.value.hex().upper())
        self._edit_entry.select_range(0, "end")
        self._edit_entry.focus_set()

        self._edit_entry.bind("<Return>",   lambda e: self._commit_edit(item, node))
        self._edit_entry.bind("<Escape>",   lambda e: self._cancel_edit())
        self._edit_entry.bind("<FocusOut>", lambda e: self._commit_edit(item, node))

    def _commit_edit(self, item, node):
        if not self._edit_entry:
            return
        new_val = self._edit_entry.get().strip().upper()
        self._cancel_edit()
        if not re.fullmatch(r"[0-9A-F]*", new_val) or len(new_val) % 2 != 0:
            self._set_status("Hex invalide — longueur paire, chiffres 0-9 A-F uniquement", "error")
            return
        try:
            node.value = bytes.fromhex(new_val)
            if hasattr(node, "_enhance"):
                node._enhance()
            self._tree.item(item, text=self._format_node_text(node))
            new_hex = serialize(self._root_nodes)
            self.entry_tlv.delete(0, "end")
            self.entry_tlv.insert(0, new_hex)
            self._set_status(f"Updated [{node.tag}] → {new_val}", "ok")
        except Exception as e:
            self._set_status(f"Erreur : {e}", "error")

    def _cancel_edit(self):
        if self._edit_frame:
            self._edit_frame.destroy()
            self._edit_frame = None
        self._edit_entry = None

    # ------------------------------------------------------------------ #
    #  Formatting — Ajout de "Name: " et réduction des espaces entre champs
    # ------------------------------------------------------------------ #
    def _format_node_text(self, node) -> str:
        if isinstance(node, BitmaskPseudoNode):
            # Pour les pseudo-nœuds, on affiche juste le texte (pas de "Name:")
            return f"  {node.text}"
        tag    = node.tag
        name   = node.description or node.name or "Tag inconnu"
        length = node.length
        if node.is_constructed:
            # Ajout de "Name: " avant le nom
            return f"[{tag}]  Name: {name}  —  taille: {length}"
        else:
            value_hex = node.value.hex().upper() if node.value else ""
            return f"[{tag}]  Name: {name}  —  taille: {length}  —  value: {value_hex}"

    # ------------------------------------------------------------------ #
    #  Tree population
    # ------------------------------------------------------------------ #
    def _populate_tree(self, nodes, parent=""):
        for node in nodes:
            text = self._format_node_text(node)

            if isinstance(node, BitmaskPseudoNode):
                tags = ("pseudo",)
            elif not getattr(node, "is_valid_parent", True):
                tags = ("warn",)
            else:
                tags = ()

            item = self._tree.insert(
                parent, "end",
                text=text,
                tags=tags,
                open=False,
            )
            self._node_map[item] = node

            children = list(getattr(node, "children", []) or [])
            bitmask_ch = list(getattr(node, "_bitmask_children", []) or [])
            all_children = children + bitmask_ch
            if all_children:
                self._populate_tree(all_children, item)

    def _attach_bitmask_nodes(self, nodes):
        for node in nodes:
            bitmask = getattr(node, "_cached_bitmask", None) or getattr(node, "bitmask", None)
            if bitmask:
                value_bytes = node.value
                bytes_map = {}
                for bit in bitmask:
                    byte_idx = bit.get("byte", 0)
                    if byte_idx not in bytes_map:
                        byte_val = value_bytes[byte_idx] if byte_idx < len(value_bytes) else 0
                        bytes_map[byte_idx] = {"value": byte_val, "bits": []}
                    if bit.get("set", False):
                        bytes_map[byte_idx]["bits"].append(bit)

                bitmask_children = []
                for byte_idx in sorted(bytes_map):
                    byte_data = bytes_map[byte_idx]
                    byte_text = f"Byte {byte_idx + 1} ({byte_data['value']:02X})"
                    byte_node = BitmaskPseudoNode(byte_text, is_constructed=True)
                    for bit in byte_data["bits"]:
                        mask = bit.get("mask", 0)
                        label = bit.get("name", "")
                        if mask:
                            bit_val = byte_data["value"] & mask
                            bit_text = f"Bit {bit.get('bit', 0)} (Mask 0x{mask:02X}, value 0x{bit_val:02X}) → {label}"
                        else:
                            bit_text = label
                        byte_node.children.append(BitmaskPseudoNode(bit_text))
                    bitmask_children.append(byte_node)
                node._bitmask_children = bitmask_children
            if node.children:
                self._attach_bitmask_nodes(node.children)

    # ------------------------------------------------------------------ #
    #  Parse pipeline
    # ------------------------------------------------------------------ #
    def _do_parse(self):
        raw = self.entry_tlv.get().strip()
        if not raw:
            self._set_status("Please enter a TLV hex payload", "error")
            return

        self._do_clear()
        raw_hex = "".join(raw.split()).upper()

        fmt = validate_hex(raw_hex, level="format")
        if not fmt.valid:
            self._set_status(f"[FORMAT ERROR] {fmt.errors[0].message}", "error")
            return

        struct = validate_hex(fmt.cleaned_hex, level="structure")
        if not struct.valid:
            self._set_status(f"[STRUCTURE ERROR] {struct.errors[0].message}", "error")
            return

        self._set_status("Parsing... (please wait)", "ready")

        cleaned = fmt.cleaned_hex
        FAST_THRESHOLD = 4096

        if len(cleaned) < FAST_THRESHOLD:
            try:
                tree = parse(cleaned, "raw")
            except Exception:
                try:
                    tree = parse(cleaned, "config")
                except Exception as e2:
                    self._set_status(f"Parse error: {e2}", "error")
                    return
            self._on_parse_complete(tree)
        else:
            self._parse_result_queue = queue.Queue()

            def _bg_parse():
                try:
                    tree = parse(cleaned, "raw")
                except Exception:
                    try:
                        tree = parse(cleaned, "config")
                    except Exception as e2:
                        self._parse_result_queue.put(("error", str(e2)))
                        return
                self._parse_result_queue.put(("ok", tree))

            threading.Thread(target=_bg_parse, daemon=True).start()
            self.after(50, self._poll_parse_result)

    def _poll_parse_result(self):
        try:
            status, payload = self._parse_result_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_parse_result)
            return
        if status == "error":
            self._set_status(f"Parse error: {payload}", "error")
            return
        self._on_parse_complete(payload)

    def _on_parse_complete(self, tree):
        self._root_nodes = tree

        def count(nodes):
            n = len(nodes)
            for node in nodes:
                n += count(node.children)
            return n
        total = count(self._root_nodes)

        self._cache_bitmasks(self._root_nodes)
        self._attach_bitmask_nodes(self._root_nodes)
        self._populate_tree(self._root_nodes)
        self._set_status(f"Parsed {total} tag(s) successfully", "ok")

    def _cache_bitmasks(self, nodes):
        for node in nodes:
            node._cached_bitmask = getattr(node, "bitmask", None)
            if node.children:
                self._cache_bitmasks(node.children)

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=28, fg_color=COLORS["surface"], corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        ctk.CTkFrame(bar, height=1, fg_color=COLORS["border"]).pack(fill="x", side="top")
        self._lbl_status = ctk.CTkLabel(
            bar, text="Ready",
            font=ctk.CTkFont(UI_FONT, 11),
            text_color=COLORS["text_muted"], anchor="w",
        )
        self._lbl_status.pack(side="left", padx=16, pady=4)

    def _set_status(self, msg: str, level: str = "ready"):
        palette = {
            "ready": COLORS["text_muted"],
            "ok":    COLORS["success"],
            "error": COLORS["danger"],
            "warn":  "#D97706",
        }
        self._lbl_status.configure(text=msg, text_color=palette.get(level, COLORS["text_muted"]))

    def _do_clear(self):
        self._cancel_edit()
        self._tree.delete(*self._tree.get_children())
        self._node_map.clear()
        self._root_nodes = []
        self._set_status("Ready", "ready")

    def _do_generate(self):
        if not self._root_nodes:
            self._set_status("Nothing to generate -- parse a payload first", "error")
            return
        try:
            new_hex = serialize(self._root_nodes)
            self.entry_tlv.delete(0, "end")
            self.entry_tlv.insert(0, new_hex)
            self._set_status(f"Generated {len(new_hex) // 2} bytes -- input field updated", "ok")
        except Exception as e:
            self._set_status(f"Serialization error: {e}", "error")


if __name__ == "__main__":
    app = App()
    app.mainloop()