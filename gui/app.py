import os
import threading
import queue
import sys
import re
import customtkinter as ctk
from tkinter import ttk

# Dynamically add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from emv_tlv import parse, serialize, validate_hex, Dictionary, TLVNode

# helvetica and courier are available on every Tk platform including Linux
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
    "warn_bg":    "#FEF3C7",
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


class TreeRow(ctk.CTkFrame):
    def __init__(self, master, node, depth: int,
                 on_toggle, on_edit_done, on_select, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)

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
        indent = self.depth * 24

        self._inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self._inner.pack(fill="x", padx=(indent, 0), pady=1)
        self._inner.bind("<Button-1>", self._on_click)

        is_constructed = False
        if isinstance(self.node, BitmaskPseudoNode):
            is_constructed = self.node.is_constructed
        else:
            # Use _cached_bitmask if available (set by _cache_bitmasks), fall back to getattr
            cached_bitmask = getattr(self.node, "_cached_bitmask", None)
            if cached_bitmask is None:
                cached_bitmask = getattr(self.node, "bitmask", None)
            is_constructed = self.node.is_constructed or bool(cached_bitmask)

        if is_constructed:
            self.btn_triangle = ctk.CTkButton(
                self._inner, text=">",
                width=22, height=22,
                font=ctk.CTkFont(UI_FONT, 11, "bold"),
                fg_color="transparent",
                hover_color=COLORS["hover"],
                text_color=COLORS["text_muted"],
                corner_radius=4,
                command=self._do_toggle,
            )
            self.btn_triangle.pack(side="left", padx=(0, 4))
        else:
            ctk.CTkLabel(self._inner, text="", width=26).pack(side="left", padx=(0, 4))

        self.lbl_text = ctk.CTkLabel(
            self._inner, text="",
            font=ctk.CTkFont(MONO_FONT, 12),
            text_color=COLORS["text"], anchor="w",
        )
        self.lbl_text.pack(side="left", fill="x", expand=True)
        self.lbl_text.bind("<Button-1>", self._on_click)
        if not isinstance(self.node, BitmaskPseudoNode) and not self.node.is_constructed:
            self.lbl_text.bind("<Double-1>", self._on_double_click)

        self.refresh_text()

        self._inner.bind("<Enter>", self._on_hover_in)
        self._inner.bind("<Leave>", self._on_hover_out)

    def refresh_text(self):
        if isinstance(self.node, BitmaskPseudoNode):
            self.lbl_text.configure(text=self.node.text)
            return

        # Real TLVNode formatting to match parse_tree.py
        tag = self.node.tag
        length = self.node.length
        value_hex = self.node["value"]

        if self.node.is_unknown:
            header = f"{tag} [UNKNOWN] (len=0x{length:02X})"
        elif self.node.description:
            header = f"{tag} ({self.node.description}, len=0x{length:02X})"
        elif self.node.name:
            header = f"{tag} ({self.node.name}, len=0x{length:02X})"
        else:
            header = f"{tag} (len=0x{length:02X})"

        if value_hex:
            header += f' value="{value_hex}"'

        if not self.node.is_valid_parent:
            header += f"  ⚠ {self.node.parent_validation_error}"

        self.lbl_text.configure(text=header)

    def _do_toggle(self):
        self.is_open = not self.is_open
        self.btn_triangle.configure(text="v" if self.is_open else ">")
        self.on_toggle(self, self.is_open)

    def _on_click(self, event=None):
        self.on_select(self)

    def _on_double_click(self, event=None):
        if not self.node.is_constructed:
            self._start_edit()

    def _on_hover_in(self, event=None):
        if not self.selected:
            self._inner.configure(fg_color=COLORS["hover"])

    def _on_hover_out(self, event=None):
        if not self.selected:
            self._inner.configure(fg_color="transparent")

    def set_selected(self, sel: bool):
        self.selected = sel
        self._inner.configure(fg_color=COLORS["select"] if sel else "transparent")

    def _start_edit(self):
        if self._entry:
            return
        self.lbl_text.pack_forget()

        tag = self.node.tag
        prefix = f"{tag} value: "

        self.lbl_prefix = ctk.CTkLabel(
            self._inner, text=prefix,
            font=ctk.CTkFont(MONO_FONT, 12),
            text_color=COLORS["text"], anchor="w",
        )
        self.lbl_prefix.pack(side="left")

        self._entry = ctk.CTkEntry(
            self._inner,
            font=ctk.CTkFont(MONO_FONT, 12),
            fg_color=COLORS["surface"],
            border_color=COLORS["accent"],
            text_color=COLORS["accent"],
            width=300, height=24, corner_radius=4,
        )
        self._entry.insert(0, self.node["value"])
        self._entry.select_range(0, "end")
        self._entry.pack(side="left", padx=(0, 8))
        self._entry.focus_set()

        self._entry.bind("<Return>",   lambda _e: self._commit_edit())
        self._entry.bind("<FocusOut>", lambda _e: self._commit_edit())
        self._entry.bind("<Escape>",   lambda _e: self._cancel_edit())

    def _commit_edit(self):
        if not self._entry:
            return
        new_val = self._entry.get().strip().upper()
        self._cleanup_entry()

        if not re.fullmatch(r"[0-9A-F]*", new_val) or len(new_val) % 2 != 0:
            self.on_edit_done(self, None, "error")
            return

        try:
            self.node.value = bytes.fromhex(new_val)
            self.node._enhance()
        except Exception:
            self.on_edit_done(self, None, "error")
            return

        self.refresh_text()
        self.lbl_text.pack(side="left", fill="x", expand=True)
        self.on_edit_done(self, new_val, "ok")

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


# ====================================================================== #
#  Main Application
# ====================================================================== #
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

        # Immediate close on window X button — bypass slow widget-by-widget teardown
        self.protocol("WM_DELETE_WINDOW", self._immediate_close)

    def _immediate_close(self):
        """Close instantly without cascading destroy of each TreeRow."""
        self.withdraw()          # hide window immediately (user sees instant close)
        self.quit()              # stop the mainloop
        self.destroy()           # force destroy all widgets at once

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
            bar, text="Generate Hex", command=self._do_generate,
            font=ctk.CTkFont(UI_FONT, 12, "bold"),
            fg_color=COLORS["success"], hover_color="#047857",
            text_color="#fff", width=130, height=32, corner_radius=6,
        ).pack(side="left", padx=6)

    def _build_tree_zone(self):
        outer = ctk.CTkFrame(
            self, fg_color=COLORS["surface"],
            corner_radius=8, border_color=COLORS["border"], border_width=1,
        )
        outer.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        self._canvas = ctk.CTkCanvas(outer, bg=COLORS["surface"], highlightthickness=0)
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        sv = ttk.Scrollbar(outer, orient="vertical",   command=self._canvas.yview)
        sv.grid(row=0, column=1, sticky="ns")
        sh = ttk.Scrollbar(outer, orient="horizontal", command=self._canvas.xview)
        sh.grid(row=1, column=0, sticky="ew")

        self._canvas.configure(yscrollcommand=sv.set, xscrollcommand=sh.set)

        self._tree_frame = ctk.CTkFrame(
            self._canvas, fg_color=COLORS["surface"], corner_radius=0,
        )
        self._win_id = self._canvas.create_window(
            (0, 0), window=self._tree_frame, anchor="nw",
        )

        self._tree_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",     self._on_canvas_configure)
        self._canvas.bind_all(
            "<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"),
        )
        # Linux scroll events
        self._canvas.bind_all(
            "<Button-4>", lambda e: self._canvas.yview_scroll(-1, "units")
        )
        self._canvas.bind_all(
            "<Button-5>", lambda e: self._canvas.yview_scroll(1, "units")
        )

    def _on_frame_configure(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None):
        self._canvas.itemconfig(self._win_id, width=event.width)

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

    # ------------------------------------------------------------------ #
    #  Tree building
    # ------------------------------------------------------------------ #
    def _make_row(self, node: TLVNode, depth: int, parent_row) -> TreeRow:
        row = TreeRow(
            self._tree_frame, node, depth,
            on_toggle=self._on_toggle,
            on_edit_done=self._on_edit_done,
            on_select=self._on_select_row,
        )
        row._child_rows = []
        row._parent_row = parent_row
        self._rows.append(row)
        return row

    def _collect_all_rows(self, nodes, parent_row, depth) -> list:
        """
        Walk the full node tree and return a flat ordered list of
        (row, should_pack) tuples. Only top-level rows are packed;
        child rows are built but start hidden.
        Handles both nested children and bitmask pseudo-nodes.
        """
        result = []
        for node in nodes:
            row = self._make_row(node, depth, parent_row)
            is_root = (parent_row is None)
            result.append((row, is_root))

            sub_rows = []

            # Recurse children first if constructed
            if node.is_constructed and node.children:
                sub = self._collect_all_rows(node.children, row, depth + 1)
                result.extend(sub)
                for child_row, _ in sub:
                    if child_row._parent_row is row:
                        sub_rows.append(child_row)

            # Recurse bitmask details if present (use cached bitmask from _cache_bitmasks)
            bitmask = getattr(node, "_cached_bitmask", None)
            if bitmask is None:
                bitmask = getattr(node, "bitmask", None)
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

                for byte_idx in sorted(bytes_map):
                    byte_data = bytes_map[byte_idx]
                    byte_text = f"Byte {byte_idx + 1} ({byte_data['value']:02X})"

                    byte_node = BitmaskPseudoNode(byte_text, is_constructed=True)
                    byte_row = self._make_row(byte_node, depth + 1, row)
                    result.append((byte_row, False))
                    sub_rows.append(byte_row)

                    byte_child_rows = []
                    for bit in byte_data["bits"]:
                        mask = bit.get("mask", 0)
                        label = bit.get("name", "")
                        if mask:
                            bit_val = byte_data["value"] & mask
                            bit_text = f"Bit {bit.get('bit', 0)} (Mask 0x{mask:02X}, value 0x{bit_val:02X}) --> {label}"
                        else:
                            bit_text = label

                        bit_node = BitmaskPseudoNode(bit_text, is_constructed=False)
                        bit_row = self._make_row(bit_node, depth + 2, byte_row)
                        result.append((bit_row, False))
                        byte_child_rows.append(bit_row)

                    byte_row._child_rows = byte_child_rows

            if sub_rows:
                row._child_rows = sub_rows

        return result

    def _build_tree_rows(self, nodes):
        """
        Collect all rows first (fast), then pack them in small batches
        via after() so the Tk event loop is never blocked.
        """
        all_items = self._collect_all_rows(nodes, None, 0)
        self._start_batch_pack(all_items, 0)

    def _start_batch_pack(self, items: list, start: int, batch: int = 30):
        """Pack `batch` rows, then reschedule the next batch via after()."""
        end = min(start + batch, len(items))
        for row, is_root in items[start:end]:
            if is_root:
                row.pack(fill="x", pady=0)
            # child rows start hidden — no pack

        if end < len(items):
            # Yield control back to Tk, then continue
            self.after(1, lambda: self._start_batch_pack(items, end, batch))
        else:
            # All rows are built — update scroll region and final status
            self._on_frame_configure()
            self._finish_parse()

    def _on_toggle(self, row: TreeRow, is_open: bool):
        if is_open:
            self._show_children(row)
        else:
            self._hide_children(row)
        self._on_frame_configure()

    def _show_children(self, row: TreeRow):
        prev = row
        for child_row in row._child_rows:
            child_row.pack(fill="x", pady=0, after=prev)
            prev = child_row
            if child_row.is_open:
                self._show_children(child_row)

    def _hide_children(self, row: TreeRow):
        for child_row in row._child_rows:
            self._hide_children(child_row)
            child_row.pack_forget()

    def _on_select_row(self, row: TreeRow):
        if self._selected_row and self._selected_row is not row:
            self._selected_row.set_selected(False)
        row.set_selected(True)
        self._selected_row = row

        if isinstance(row.node, BitmaskPseudoNode):
            self._set_status(row.node.text, "ready")
            return

        tag_name = row.node.name or "Unknown Tag"
        length   = get_node_display_length(row.node)
        msg      = f"[{row.node.tag}]  {tag_name}  |  {length} bytes"

        if not row.node.is_valid_parent:
            msg += f"  [!] {row.node.parent_validation_error}"
            self._set_status(msg, "warn")
        else:
            self._set_status(msg, "ready")

    def _on_edit_done(self, row: TreeRow, new_val, level: str):
        if level == "ok":
            try:
                # Optimization #1: Update in-place instead of re-parsing entire tree
                # The node value was already updated in TreeRow._commit_edit()
                # Just refresh the hex input field without rebuilding the tree
                new_hex = serialize(self._root_nodes)
                self.entry_tlv.delete(0, "end")
                self.entry_tlv.insert(0, new_hex)
                self._set_status(f"Updated [{row.node.tag}] to {new_val}", "ok")
            except Exception as e:
                self._set_status(f"Serialization error: {e}", "error")
        else:
            self._set_status(
                "Invalid hex -- must be even-length digits 0-9 A-F only",
                "error",
            )

    # ------------------------------------------------------------------ #
    #  Actions — identical logic to parse_tree.py
    # ------------------------------------------------------------------ #
    def _do_parse(self):
        raw = self.entry_tlv.get().strip()
        if not raw:
            self._set_status("Please enter a TLV hex payload", "error")
            return

        self._do_clear()
        raw_hex = "".join(raw.split()).upper()

        # 1. Format validation (fast — keep on main thread)
        fmt = validate_hex(raw_hex, level="format")
        if not fmt.valid:
            self._set_status(f"[FORMAT ERROR] {fmt.errors[0].message}", "error")
            return

        # 2. Structure validation
        struct = validate_hex(fmt.cleaned_hex, level="structure")
        if not struct.valid:
            self._set_status(f"[STRUCTURE ERROR] {struct.errors[0].message}", "error")
            return

        # Optimization #4: Single update_idletasks before parse
        self._set_status("Parsing... (please wait)", "ready")
        self.update_idletasks()

        cleaned = fmt.cleaned_hex
        
        # Optimization #2: Use sync parse for small payloads (< 2KB / 2048 chars)
        FAST_THRESHOLD = 2048
        
        if len(cleaned) < FAST_THRESHOLD:
            # Parse synchronously for small payloads - fast enough to not block UI
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
            # 3. Parse large payloads on a background thread so the UI stays responsive
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
            # Poll every 50 ms until background thread finishes
            self.after(50, self._poll_parse_result)

    def _poll_parse_result(self):
        """Check if the background parse is done; reschedule if not."""
        try:
            status, payload = self._parse_result_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_parse_result)
            return

        if status == "error":
            self._set_status(f"Parse error: {payload}", "error")
            return

        tree = payload
        self._on_parse_complete(tree)

    def _on_parse_complete(self, tree):
        """Common completion handler for both sync and async parse."""
        self._root_nodes = tree

        # Count nodes and parent issues
        def count(nodes):
            n = len(nodes)
            for node in nodes:
                n += count(node.children)
            return n
        self._total_nodes = count(self._root_nodes)

        self._invalid_nodes = []
        def scan(nodes):
            for node in nodes:
                if not node.is_valid_parent:
                    self._invalid_nodes.append(node)
                scan(node.children)
        scan(self._root_nodes)

        # Cache bitmask attributes for fast access during tree building
        self._cache_bitmasks(self._root_nodes)

        self._set_status(
            f"Building tree ({self._total_nodes} tags)...", "ready"
        )
        self.update_idletasks()
        # Build rows in batches so Tk event loop stays alive
        self._build_tree_rows(self._root_nodes)

    def _finish_parse(self):
        """Called after all rows are packed."""
        total   = self._total_nodes
        invalid = self._invalid_nodes
        if invalid:
            self._set_status(
                f"Parsed {total} tag(s)  |  [!] {len(invalid)} parent issue(s) detected",
                "warn",
            )
        else:
            self._set_status(f"Parsed {total} tag(s) successfully", "ok")

    def _do_clear(self):
        # Destroy the container's children in one shot to avoid the
        # cascading destroy-during-iteration crash
        for widget in list(self._tree_frame.winfo_children()):
            widget.destroy()
        self._rows.clear()
        self._selected_row = None
        self._root_nodes   = []
        self._set_status("Ready", "ready")

    # Optimization #3: Cache bitmask on all nodes to avoid repeated getattr() lookups
    def _cache_bitmasks(self, nodes):
        for node in nodes:
            node._cached_bitmask = getattr(node, "bitmask", None)
            if node.children:
                self._cache_bitmasks(node.children)

    def _do_generate(self):
        if not self._root_nodes:
            self._set_status("Nothing to generate -- parse a payload first", "error")
            return
        try:
            new_hex = serialize(self._root_nodes)
            self.entry_tlv.delete(0, "end")
            self.entry_tlv.insert(0, new_hex)
            self._set_status(
                f"Generated {len(new_hex) // 2} bytes -- input field updated", "ok",
            )
        except Exception as e:
            self._set_status(f"Serialization error: {e}", "error")


if __name__ == "__main__":
    app = App()
    app.mainloop()
