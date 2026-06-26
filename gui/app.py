import os
import threading
import queue
import sys
import re
import traceback
import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
import tkinter.font as tkfont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from emv_tlv import parse, serialize, validate_hex, Dictionary, TLVNode


def hex_bytes_to_decimals(value_hex: str) -> str:
    if not value_hex or len(value_hex) % 2 != 0:
        return ""
    bytes_list = [str(int(value_hex[i:i+2], 16)) for i in range(0, len(value_hex), 2)]
    return " ".join(bytes_list)

UI_FONT   = "helvetica"
MONO_FONT = "courier"
FONT_SIZE_TREE = 13

COLORS = {
    "bg":           "#0047AB",
    "surface":      "#FFFFFF",
    "border":       "#D6D8E0",
    "accent":       "#0047AB",
    "accent_hover": "#003A8C",
    "text":         "#1A1F2E",
    "text_muted":   "#5B6278",
    "danger":       "#C0392B",
    "success":      "#1A7A4A",
    "hover":        "#EDF0F7",
    "select":       "#D0DCF5",
    "header_bg":    "#0047AB",
    "header_sub":   "#93C5FD",
    "input_bg":     "#003A8C",
    "warn":         "#D97706",
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

        self._root_nodes         = []
        self._node_map           = {}
        self._edit_entry         = None
        self._edit_frame         = None
        self._search_results     = []
        self._search_idx         = 0
        self._highlight_overlays = []
        self._tree_indent        = 28

        self._build_header()
        self._build_input_area()
        self._build_buttons()
        self._build_tree_zone()
        self._build_statusbar()
        self.bind("<Control-p>",       lambda e: self._do_parse())
        self.bind("<Control-e>", lambda e: self._do_clear())
        self.bind("<Control-g>",       lambda e: self._do_generate())

        self.protocol("WM_DELETE_WINDOW", self._immediate_close)

    def _immediate_close(self):
        self.withdraw()
        self.quit()
        self.destroy()

    def _build_header(self):
        h = ctk.CTkFrame(self, height=60, fg_color=COLORS["header_bg"], corner_radius=0)
        h.pack(fill="x")
        h.pack_propagate(False)

        left = ctk.CTkFrame(h, fg_color="transparent")
        left.pack(side="left", padx=24, pady=10)

        ctk.CTkLabel(
            left, text="EMV TLV Parser",
            font=ctk.CTkFont(UI_FONT, 22, "bold"),
            text_color="#FFFFFF",
        ).pack(anchor="w")

    def _build_input_area(self):
        card = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=8, border_color="#1A56DB", border_width=1,
        )
        card.pack(fill="x", padx=15, pady=(16, 8))

        ctk.CTkLabel(
            card, text="Message TLV (hex) :", anchor="w",
            font=ctk.CTkFont(UI_FONT, 17, "bold"),
            text_color=COLORS["bg"],
        ).pack(fill="x", padx=20, pady=(14, 6))

        input_container = tk.Frame(card, bg=COLORS["input_bg"])
        input_container.pack(fill="x", padx=20, pady=(0, 16))
        input_container.rowconfigure(0, weight=1)
        input_container.columnconfigure(0, weight=1)

        v_scroll = ttk.Scrollbar(input_container, orient="vertical")
        v_scroll.grid(row=0, column=1, sticky="ns")

        self.entry_tlv = tk.Text(
            input_container,
            height=4,
            wrap="word",
            font=(MONO_FONT, 13),
            fg=COLORS["text_muted"],
            bg="#F5F5F0",
            bd=0, relief="flat",
            highlightthickness=2,
            highlightbackground="#1A56DB",
            highlightcolor="#93C5FD",
            insertbackground=COLORS["text"],
            yscrollcommand=v_scroll.set,
            padx=10, pady=10,
        )
        self.entry_tlv.grid(row=0, column=0, sticky="nsew")
        v_scroll.config(command=self.entry_tlv.yview)

        self._placeholder = "Enter your TLV message here..."
        self.entry_tlv.insert("1.0", self._placeholder)
        self.entry_tlv.bind("<FocusIn>",  self._on_entry_focus_in)
        self.entry_tlv.bind("<FocusOut>", self._on_entry_focus_out)
        self.entry_tlv.bind("<Key>",      self._on_entry_key)
        self.entry_tlv.bind("<Return>",   lambda e: (self._do_parse(), "break"))

    def _on_entry_focus_in(self, event):
        if self.entry_tlv.get("1.0", "end-1c") == self._placeholder:
            self.entry_tlv.delete("1.0", "end")
            self.entry_tlv.configure(fg=COLORS["text"])

    def _on_entry_focus_out(self, event):
        if not self.entry_tlv.get("1.0", "end-1c").strip():
            self.entry_tlv.delete("1.0", "end")
            self.entry_tlv.insert("1.0", self._placeholder)
            self.entry_tlv.configure(fg=COLORS["text_muted"])

    def _on_entry_key(self, event):
        if self.entry_tlv.get("1.0", "end-1c") == self._placeholder:
            self.entry_tlv.delete("1.0", "end")
            self.entry_tlv.configure(fg=COLORS["text"])

    def _build_buttons(self):
        bar = ctk.CTkFrame(self, height=44, fg_color="transparent")
        bar.pack(fill="x", padx=15, pady=(0, 6))
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar, text="Parse", command=self._do_parse,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color="#800020", hover_color="#5C0015",
            text_color="#fff", width=110, height=34, corner_radius=7,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            bar, text="Clear", command=self._do_clear,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color=COLORS["surface"], border_color=COLORS["border"],
            border_width=1, hover_color=COLORS["hover"],
            text_color=COLORS["text_muted"],
            width=100, height=34, corner_radius=7,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            bar, text="Generate", command=self._do_generate,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color=COLORS["success"], hover_color="#145C38",
            text_color="#fff", width=130, height=34, corner_radius=7,
        ).pack(side="left", padx=6)

        search_card = ctk.CTkFrame(
            bar, fg_color=COLORS["surface"],
            corner_radius=7, border_color=COLORS["border"], border_width=1,
            height=34, width=340,
        )
        search_card.pack(side="right", padx=(0, 15))
        search_card.pack_propagate(False)

        inner = ctk.CTkFrame(search_card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=8)

        ctk.CTkLabel(
            inner, text="🔍",
            font=ctk.CTkFont(UI_FONT, 12),
            text_color=COLORS["text_muted"],
            width=18,
        ).pack(side="left", padx=(0, 4))

        self.entry_search = ctk.CTkEntry(
            inner,
            placeholder_text="Search tag...",
            font=ctk.CTkFont(MONO_FONT, 14),
            fg_color="transparent",
            border_width=0,
            text_color=COLORS["text"],
            height=30,
        )
        self.entry_search.pack(side="left", fill="both", expand=True)
        self.entry_search.bind("<Return>", self._on_search_return)
        self.entry_search.bind("<KeyRelease>", self._on_search_key)

        self._nav_frame = ctk.CTkFrame(inner, fg_color="transparent")
        self._nav_frame.pack(side="left", padx=(2, 0))
        self._nav_frame.pack_forget()

        self._lbl_search_count = ctk.CTkLabel(
            self._nav_frame, text="",
            font=ctk.CTkFont(UI_FONT, 11, "bold"),
            text_color=COLORS["accent"],
            width=36,
        )
        self._lbl_search_count.pack(side="left", padx=(2, 2))

        ctk.CTkFrame(self._nav_frame, width=1, height=18, fg_color=COLORS["border"]).pack(side="left", padx=4)

        ctk.CTkButton(
            self._nav_frame, text="▲", width=22, height=22,
            font=ctk.CTkFont(UI_FONT, 10),
            fg_color="transparent", hover_color=COLORS["hover"],
            text_color=COLORS["text_muted"], corner_radius=4,
            command=self._prev_result,
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            self._nav_frame, text="▼", width=22, height=22,
            font=ctk.CTkFont(UI_FONT, 10),
            fg_color="transparent", hover_color=COLORS["hover"],
            text_color=COLORS["text_muted"], corner_radius=4,
            command=self._next_result,
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            self._nav_frame, text="✕", width=22, height=22,
            font=ctk.CTkFont(UI_FONT, 11),
            fg_color="transparent", hover_color=COLORS["hover"],
            text_color=COLORS["text_muted"], corner_radius=4,
            command=self._clear_search_field,
        ).pack(side="left", padx=(1, 0))

    def _on_search_return(self, event):
        if self._search_results:
            self._next_result()
        else:
            self._do_search()
        return "break"

    def _on_search_key(self, event):
        query = self.entry_search.get().strip()
        if not query:
            self._clear_search_highlight()
            self._search_results = []
            self._search_idx = 0
            self._lbl_search_count.configure(text="")
            if self._nav_frame.winfo_ismapped():
                self._nav_frame.pack_forget()
            self.entry_search.bind("<Return>", lambda e: self._do_search())
        else:
            self._do_search()

    def _clear_search_field(self):
        self.entry_search.delete(0, "end")
        self._clear_search_highlight()
        self._search_results = []
        self._search_idx = 0
        self._lbl_search_count.configure(text="")
        if self._nav_frame.winfo_ismapped():
            self._nav_frame.pack_forget()
        self._set_status("Ready", "ready")
        self.entry_search.bind("<Return>", lambda e: self._do_search())

    def _update_search_count(self):
        if self._search_results:
            self._lbl_search_count.configure(
                text=f"{self._search_idx + 1}/{len(self._search_results)}"
            )
        else:
            self._lbl_search_count.configure(text="")

    def _do_search(self):
        tag_query = self.entry_search.get().strip().upper()
        if not tag_query:
            return
        if not self._node_map:
            self._set_status("Parse a TLV message first", "error")
            return

        self._clear_search_highlight()
        self._search_results = []

        def walk(parent=""):
            for item in self._tree.get_children(parent):
                node = self._node_map.get(item)
                if node and not isinstance(node, BitmaskPseudoNode):
                    if node.tag.upper() == tag_query:
                        self._search_results.append(item)
                walk(item)
        walk()
        if not self._search_results:
            self._set_status(f"Tag [{tag_query}] not found", "error")
            self._lbl_search_count.configure(text="")
            if self._nav_frame.winfo_ismapped():
                self._nav_frame.pack_forget()
            return
        if not self._nav_frame.winfo_ismapped():
            self._nav_frame.pack(side="left", padx=(2, 0))

        self._search_idx = 0
        self._tree.selection_set(self._search_results[0])
        self._tree.see(self._search_results[0])

        self.after(60, self._draw_search_highlights)
        self._update_search_count()

        n = len(self._search_results)
        self._set_status(f"{n} occurrence(s) of [{tag_query}]  —  Press Enter to navigate", "ok")
        self.entry_search.bind("<Return>", self._on_search_return)

    def _draw_search_highlights(self):
        if not self._search_results:
            return

        self._clear_highlight_overlays()
        tree_font = tkfont.Font(font=(MONO_FONT, FONT_SIZE_TREE))

        for item in self._search_results:
            bbox = self._tree.bbox(item, column="#0")
            if not bbox:
                continue
            x, y, w, h = bbox

            full_text = self._tree.item(item, "text")
            m = re.match(r"^(\s*\[[0-9A-Fa-f]+\])", full_text)
            if not m:
                continue
            tag_text  = m.group(1)
            tag_width = tree_font.measure(tag_text)

            overlay = tk.Label(
                self._tree,
                text=tag_text,
                font=(MONO_FONT, FONT_SIZE_TREE),
                bg="#FDE68A",
                fg="#800020",
                anchor="w",
                justify="left",
                bd=0,
                padx=0, pady=0,
            )
            x_offset = x + self._tree_indent
            overlay.place(x=x_offset, y=y, width=tag_width, height=h)
            self._highlight_overlays.append(overlay)

    def _clear_highlight_overlays(self):
        for ov in self._highlight_overlays:
            ov.destroy()
        self._highlight_overlays = []

    def _prev_result(self):
        if not self._search_results:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_results)
        item = self._search_results[self._search_idx]
        self._tree.selection_set(item)
        self._tree.see(item)
        self.after(60, self._draw_search_highlights)
        self._update_search_count()
        self._set_status(
            f"Occurrence {self._search_idx + 1}/{len(self._search_results)}", "ok"
        )

    def _next_result(self):
        if not self._search_results:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_results)
        item = self._search_results[self._search_idx]
        self._tree.selection_set(item)
        self._tree.see(item)
        self.after(60, self._draw_search_highlights)
        self._update_search_count()
        self._set_status(
            f"Occurrence {self._search_idx + 1}/{len(self._search_results)}", "ok"
        )

    def _clear_search_highlight(self):
        self._clear_highlight_overlays()
        self.entry_search.bind("<Return>", self._on_search_return)
        if self._nav_frame.winfo_ismapped():
            self._nav_frame.pack_forget()

    def _build_tree_zone(self):
        outer = tk.Frame(self, bg=COLORS["accent"], bd=1, relief="flat")
        outer.pack(fill="both", expand=True, padx=15, pady=(0, 6))

        container = tk.Frame(outer, bg=COLORS["surface"])
        container.pack(fill="both", expand=True, padx=1, pady=1)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")

        style.configure("EMV.Treeview",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            rowheight=40,
            font=(MONO_FONT, FONT_SIZE_TREE),
            fieldbackground=COLORS["surface"],
            borderwidth=0, relief="flat",
            indent=28,
        )
        style.map("EMV.Treeview",
            background=[("selected", COLORS["select"])],
            foreground=[("selected", COLORS["text"])],
        )
        style.configure("EMV.Treeview", arrowsize=13)

        self._tree = ttk.Treeview(
            container, style="EMV.Treeview",
            show="tree", selectmode="browse",
        )
        self._tree.column("#0", width=2000, minwidth=800, stretch=False)

        vsb = ttk.Scrollbar(container, orient="vertical",   command=self._on_vscroll)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self._on_hscroll)
        self._tree.configure(yscrollcommand=self._on_yscroll_event,
                             xscrollcommand=self._on_xscroll_event)
        self._vsb = vsb
        self._hsb = hsb

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._tree.tag_configure("warn",   foreground=COLORS["danger"],
                                 font=(MONO_FONT, FONT_SIZE_TREE))
        self._tree.tag_configure("pseudo", foreground=COLORS["text_muted"],
                                 font=(MONO_FONT, FONT_SIZE_TREE))

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Double-1>",         self._on_double_click)
        self._tree.bind("<<TreeviewOpen>>",  lambda e: self.after(50, self._draw_search_highlights))
        self._tree.bind("<<TreeviewClose>>", lambda e: self.after(50, self._draw_search_highlights))

        self._tree_indent = 28

    def _on_vscroll(self, *args):
        self._tree.yview(*args)
        self._draw_search_highlights()

    def _on_hscroll(self, *args):
        self._tree.xview(*args)
        self._draw_search_highlights()

    def _on_yscroll_event(self, *args):
        self._vsb.set(*args)
        self._draw_search_highlights()

    def _on_xscroll_event(self, *args):
        self._hsb.set(*args)
        self._draw_search_highlights()

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
        tag_name = node.tech_name or node.name or "Unknown Tag"
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

        full_text    = self._tree.item(item, "text")
        marker       = "Value: "
        idx          = full_text.find(marker)
        prefix_text  = full_text[: idx + len(marker)] if idx != -1 else full_text
        tree_font    = tkfont.Font(font=(MONO_FONT, FONT_SIZE_TREE))
        prefix_width = tree_font.measure(prefix_text)
        offset_x     = prefix_width + 4
        entry_width  = max(w - offset_x - 6, 160)

        self._edit_frame = tk.Frame(self._tree, bg=COLORS["accent"], bd=1)
        self._edit_frame.place(x=x + offset_x, y=y + 1,
                               width=entry_width, height=h - 2)

        self._edit_entry = tk.Entry(
            self._edit_frame,
            font=(MONO_FONT, FONT_SIZE_TREE),
            fg=COLORS["text"], bg=COLORS["surface"],
            bd=0, relief="flat",
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
            self._set_status("Invalid hex — even length, digits 0-9 A-F only", "error")
            return
        try:
            node.value = bytes.fromhex(new_val)
            if hasattr(node, "_enhance"):
                node._enhance()
            self._tree.item(item, text=self._format_node_text(node))
            self._set_status(
                f"[{node.tag}] modified → {new_val}  |  Click Generate to update the TLV message",
                "warn",
            )
        except Exception as e:
            self._set_status(f"Error: {e}", "error")

    def _cancel_edit(self):
        if self._edit_frame:
            self._edit_frame.destroy()
            self._edit_frame = None
        self._edit_entry = None

    def _format_node_text(self, node) -> str:
        if isinstance(node, BitmaskPseudoNode):
            return f"  {node.text}"
        tag       = node.tag
        name      = getattr(node, "display_name", node.tech_name or node.name or "Unknown tag")
        length    = node.length
        if node.is_constructed:
            return f"[{tag}]  Name: {name}  —  Length: {length}"
        else:
            value_hex = node.value.hex().upper() if node.value else ""
            return f"[{tag}]  Name: {name}  —  Length: {length}  —  Value: {value_hex}"

    def _populate_tree(self, nodes, parent=""):
        for node in nodes:
            text = self._format_node_text(node)
            if isinstance(node, BitmaskPseudoNode):
                tags = ("pseudo",)
            elif not getattr(node, "is_valid_parent", True):
                tags = ("warn",)
            else:
                tags = ()

            item = self._tree.insert(parent, "end", text=text, tags=tags, open=True)
            self._node_map[item] = node

            children   = list(getattr(node, "children", []) or [])
            bitmask_ch = list(getattr(node, "_bitmask_children", []) or [])
            dol_ch     = list(getattr(node, "_dol_children", []) or [])
            mapped_ch  = list(getattr(node, "_mapped_children", []) or [])
            position_ch = list(getattr(node, "_position_children", []) or [])

            if children + bitmask_ch + dol_ch + mapped_ch + position_ch:
                self._populate_tree(children + bitmask_ch + dol_ch + mapped_ch + position_ch, item)


    def _cache_bitmasks(self, nodes):
        for node in nodes:
            try:
                metadata = Dictionary.lookup_by_tag(node.tag)
                if metadata:
                    node.tech_name = metadata.get("tech_name", "")
                    node.display_name = node.tech_name or metadata.get("name", node.name)

                    if metadata.get("value_format") == "position" or "positions" in metadata:
                        node._cached_bitmask = {"format": "position", "positions": metadata.get("positions", [])}
                    elif "bytes" in metadata:
                        node._cached_bitmask = {"bytes": metadata["bytes"]}
                    elif "bitmask" in metadata:
                        node._cached_bitmask = metadata["bitmask"]
                    else:
                        node._cached_bitmask = None
                else:
                    node.tech_name = ""
                    node.display_name = node.name or "Unknown tag"
                    node._cached_bitmask = None
            except Exception as e:
                print(f"DEBUG: _cache_bitmasks error for {node.tag}: {e}")
                traceback.print_exc()
                node.tech_name = ""
                node.display_name = node.name or "Unknown tag"
                node._cached_bitmask = None

            if node.children:
                self._cache_bitmasks(node.children)

    def _attach_bitmask_nodes(self, nodes):
     for node in nodes:
        try:
            bitmask = getattr(node, "_cached_bitmask", None)
            if bitmask and isinstance(bitmask, dict) and "bytes" in bitmask:
                value_bytes = node.value
                bitmask_children = []
                for byte_info in bitmask["bytes"]:
                    byte_idx = byte_info.get("index", 1) - 1
                    if byte_idx < 0 or byte_idx >= len(value_bytes):
                        continue
                    byte_val = value_bytes[byte_idx]
                    label = byte_info.get("label", "")
                    byte_display = f"Byte {byte_idx + 1} ({byte_val:02X})"
                    if label:
                        byte_display += f" — {label}"
                    byte_node = BitmaskPseudoNode(byte_display, is_constructed=True)

                    for bit_info in byte_info.get("bits", []):
                        bit_num = bit_info.get("bit", 0)
                        if bit_num < 1 or bit_num > 8:
                            continue
                        label_bit = bit_info.get("label", "")
                        mask = 1 << (bit_num - 1)
                      
                        if byte_val & mask:
                            bit_text = f"Bit {bit_num} (Mask 0x{mask:02X}) → {label_bit}"
                            bit_node = BitmaskPseudoNode(bit_text)
                            byte_node.children.append(bit_node)

                 
                    if byte_node.children:
                        bitmask_children.append(byte_node)

                node._bitmask_children = bitmask_children

            elif bitmask and isinstance(bitmask, list):
               
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
                    byte_node = BitmaskPseudoNode(
                        f"Byte {byte_idx + 1} ({byte_data['value']:02X})",
                        is_constructed=True,
                    )
                    for bit in byte_data["bits"]:
                        mask = bit.get("mask", 0)
                        label = bit.get("name", "")
                        bit_val = byte_data["value"] & mask if mask else 0
                        if bit_val:
                            bit_text = f"Bit {bit.get('bit', 0)} (Mask 0x{mask:02X}, value 0x{bit_val:02X}) → {label}" if mask else label
                            byte_node.children.append(BitmaskPseudoNode(bit_text))
                    if byte_node.children:
                        bitmask_children.append(byte_node)
                node._bitmask_children = bitmask_children

        except Exception as e:
            print(f"DEBUG: _attach_bitmask_nodes error for {node.tag}: {e}")
            traceback.print_exc()

        if node.children:
            self._attach_bitmask_nodes(node.children)

    def _attach_dol_children(self, nodes):
        for node in nodes:
            try:
                metadata = Dictionary.lookup_by_tag(node.tag)
                if metadata and metadata.get("value_format") == "dol":
                    dol_fields = metadata.get("dol_fields", [])
                    if dol_fields:
                        dol_children = []
                        for field in dol_fields:
                            tag = field.get("tag")
                            tech_name = field.get("tech_name", "")
                            length = field.get("length", 0)
                            child_node = BitmaskPseudoNode(
                                f"[{tag}]  Name: {tech_name}  —  Length: {length}",
                                is_constructed=False,
                            )
                            child_node.tag = tag
                            child_node.name = tech_name
                            child_node.length = length
                            dol_children.append(child_node)
                        node._dol_children = dol_children
            except Exception as e:
                print(f"DEBUG: _attach_dol_children error for {node.tag}: {e}")
                traceback.print_exc()
            if node.children:
                self._attach_dol_children(node.children)

    def _attach_mapped_children(self, nodes):
        for node in nodes:
            try:
                metadata = Dictionary.lookup_by_tag(node.tag)
                if metadata and "mapping" in metadata:
                    mapping = metadata["mapping"]
                    if mapping and node.value:
                        value_hex = node.value.hex().upper()
                        if value_hex in mapping:
                            mapped_text = mapping[value_hex]
                            child_node = BitmaskPseudoNode(
                                f"{value_hex} ({mapped_text})",
                                is_constructed=False,
                            )
                            if not hasattr(node, "_mapped_children"):
                                node._mapped_children = []
                            node._mapped_children.append(child_node)
            except Exception as e:
                print(f"DEBUG: _attach_mapped_children error for {node.tag}: {e}")
                traceback.print_exc()
            if node.children:
                self._attach_mapped_children(node.children)

    def _attach_position_children(self, nodes):
        for node in nodes:
            try:
                bitmask = getattr(node, "_cached_bitmask", None)
                if bitmask and isinstance(bitmask, dict) and bitmask.get("format") == "position":
                    positions_config = bitmask.get("positions", [])
                    if isinstance(node.value, bytes):
                        raw_value = node.value.hex().upper()
                    else:
                        raw_value = str(node.value).upper()

                    if raw_value and positions_config:
                        position_children = []
                        for index, char in enumerate(raw_value):
                            position_num = index + 1
                            try:
                                val_int = int(char, 16)
                            except ValueError:
                                continue

                            pos_meta = next((p for p in positions_config if p.get("position") == position_num), None)
                            if pos_meta:
                                parent_label = pos_meta.get("label", f"Position {position_num}")
                                values_mapping = pos_meta.get("values", {})
                            else:
                                parent_label = "RFU"
                                values_mapping = {}

                            description = values_mapping.get(str(val_int))
                            if not description:
                                description = "0" if val_int == 0 else f"Value {val_int}"

                            pos_node = BitmaskPseudoNode(
                                f"Position {position_num} : {parent_label}",
                                is_constructed=True,
                            )
                            child_text = f"{val_int}: {description}"
                            pos_node.children.append(BitmaskPseudoNode(child_text))
                            position_children.append(pos_node)

                        node._position_children = position_children
            except Exception as e:
                print(f"DEBUG: _attach_position_children error for {node.tag}: {e}")
                traceback.print_exc()
            if node.children:
                self._attach_position_children(node.children)


    def _do_parse(self):
        raw = self.entry_tlv.get("1.0", "end").strip()
        if not raw or raw == self._placeholder:
            self._set_status("Please enter a hexadecimal TLV message", "error")
            return

        self._do_clear()
        raw_hex = "".join(raw.split()).upper()

        try:
            fmt = validate_hex(raw_hex, level="format")
            if not fmt.valid:
                self._set_status(f"[FORMAT ERROR] {fmt.errors[0].message}", "error")
                return

            struct = validate_hex(fmt.cleaned_hex, level="structure")
            if not struct.valid:
                self._set_status(f"[STRUCTURE ERROR] {struct.errors[0].message}", "error")
                return

            self._set_status("Parsing in progress...", "ready")
            self.update_idletasks()

            cleaned = fmt.cleaned_hex

            if len(cleaned) < 4096:
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

                def _bg():
                    try:
                        t = parse(cleaned, "raw")
                    except Exception:
                        try:
                            t = parse(cleaned, "config")
                        except Exception as e2:
                            self._parse_result_queue.put(("error", str(e2)))
                            return
                    self._parse_result_queue.put(("ok", t))

                threading.Thread(target=_bg, daemon=True).start()
                self.after(50, self._poll_parse_result)

        except Exception as e:
            traceback.print_exc()
            self._set_status(f"Unexpected error: {e}", "error")

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
        try:
            self._root_nodes = tree

            def count(nodes):
                n = len(nodes)
                for node in nodes:
                    n += count(node.children)
                return n

            total = count(self._root_nodes)

            self._cache_bitmasks(self._root_nodes)
            self._attach_bitmask_nodes(self._root_nodes)
            self._attach_dol_children(self._root_nodes)
            self._attach_mapped_children(self._root_nodes)
            self._attach_position_children(self._root_nodes)
            self._populate_tree(self._root_nodes)
            self._set_status(f"Parsed {total} tag(s) successfully", "ok")
        except Exception as e:
            traceback.print_exc()
            self._set_status(f"Error during parsing: {e}", "error")

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=42, fg_color=COLORS["bg"], corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", fill="y", padx=20)

        self._status_dot = ctk.CTkFrame(
            left, width=8, height=8, corner_radius=4,
            fg_color="#93C5FD",
        )
        self._status_dot.pack(side="left", padx=(0, 10), pady=17)

        self._lbl_status = ctk.CTkLabel(
            left,
            text="Ready",
            font=ctk.CTkFont(UI_FONT, 15, "bold"),
            text_color="#FFFFFF",
            anchor="w",
        )
        self._lbl_status.pack(side="left", pady=10)

    def _set_status(self, msg: str, level: str = "ready"):
        palette = {
            "ready": "#93C5FD",
            "ok":    "#6EE7B7",
            "error": "#FCA5A5",
            "warn":  "#FCD34D",
        }
        color = palette.get(level, "#93C5FD")
        self._lbl_status.configure(text=msg, text_color=color)
        self._status_dot.configure(fg_color=color)

    def _do_clear(self):
        self._cancel_edit()
        self._clear_search_highlight()
        self._search_results = []
        self._search_idx = 0
        self._tree.delete(*self._tree.get_children())
        self._node_map.clear()
        self._root_nodes = []
        self._set_status("Ready", "ready")

    def _do_generate(self):
        if not self._root_nodes:
            self._set_status("Nothing to generate — parse a TLV message first", "error")
            return
        try:
            new_hex = serialize(self._root_nodes)
            self.entry_tlv.delete("1.0", "end")
            self.entry_tlv.insert("1.0", new_hex)
            self.entry_tlv.configure(fg=COLORS["text"])
            self._set_status(f"Generated {len(new_hex) // 2} bytes — TLV message updated", "ok")
        except Exception as e:
            self._set_status(f"Serialization error: {e}", "error")


if __name__ == "__main__":
    app = App()
    app.mainloop()