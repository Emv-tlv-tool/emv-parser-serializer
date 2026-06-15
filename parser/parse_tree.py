#!/usr/bin/env python3
"""
EMV TLV Tree Generator

Reads hex data from a txt file, parses it as EMV TLV,
and generates a detailed tree hierarchy output file.

TLVNode is now self-enriching: metadata, decoded values, bitmasks,
and parent validation are all populated inline at parse time.
No second-pass enrichment is needed.
"""

from emv_tlv import parse, validate_hex


def collect_lines(node, indent=0):
    """
    Collect formatted tree lines for a TLVNode recursively.

    Since TLVNode already carries metadata, decoded values, bitmask,
    and parent validation, we read directly from the node — no extra
    dictionary lookups or enrichment needed.
    """
    lines = []

    # --- Connector prefix ---
    prefix = "  " * indent + "+--+ "

    # --- Header line ---
    tag = node["tag"]
    length = node["length"]
    value_hex = node["value"]

    if node.is_unknown:
        header = f"{tag} [UNKNOWN] (len=0x{length:02X})"
    elif node.description:
        header = f"{tag} ({node.description}, len=0x{length:02X})"
    elif node.name:
        header = f"{tag} ({node.name}, len=0x{length:02X})"
    else:
        header = f"{tag} (len=0x{length:02X})"

    if value_hex:
        header += f' value="{value_hex}"'

    # --- Parent validation warning ---
    if not node.is_valid_parent:
        header += f"  ⚠ {node.parent_validation_error}"

    lines.append(prefix + header)

    # --- Bitmask details grouped by byte ---
    bitmask = node.bitmask
    if bitmask:
        value_bytes = node.value  # bytes object via the property
        base_indent = "  " * (indent + 1)

        # Group active bits by their byte index
        bytes_map = {}
        for bit in bitmask:
            byte_idx = bit.get("byte", 0)
            if byte_idx not in bytes_map:
                byte_val = value_bytes[byte_idx] if byte_idx < len(value_bytes) else 0
                bytes_map[byte_idx] = {"value": byte_val, "bits": []}
            if bit.get("set", False):
                bytes_map[byte_idx]["bits"].append(bit)

        for i, byte_idx in enumerate(sorted(bytes_map)):
            byte_data = bytes_map[byte_idx]
            is_last_byte = (i == len(bytes_map) - 1)

            byte_line = base_indent + f"+--+ Byte {byte_idx + 1} ({byte_data['value']:02X})"
            lines.append(byte_line)

            for bit in byte_data["bits"]:
                mask = bit.get("mask", 0)
                label = bit.get("name", "")
                if mask:
                    bit_val = byte_data["value"] & mask
                    bit_line = f"{base_indent}|  +--+  Bit {bit.get('bit', 0)} (Mask 0x{mask:02X}, value 0x{bit_val:02X}) --> {label}"
                else:
                    bit_line = f"{base_indent}|  +--+  {label}"
                lines.append(bit_line)

    # --- Recurse into children ---
    for child in node.children:
        lines.extend(collect_lines(child, indent + 1))

    return lines


def generate_tree_output(hex_data, output_file="tree_output.txt"):
    """
    Parse hex data and generate formatted tree output file.

    Args:
        hex_data: Hex string (whitespace is ignored)
        output_file: Output file path
    """
    raw_data = "".join(hex_data.split())

    # --- Level 1: Format validation ---
    print("Validating format...")
    fmt_result = validate_hex(raw_data, level="format")
    if not fmt_result.valid:
        for err in fmt_result.errors:
            print(f"  [FORMAT ERROR] {err.code}: {err.message}")
        print("Aborting: input has format errors.")
        return
    for w in fmt_result.warnings:
        print(f"  [FORMAT WARNING] {w.code}: {w.message}")

    # --- Level 2: Structure validation ---
    print("Validating TLV structure...")
    struct_result = validate_hex(fmt_result.cleaned_hex, level="structure")
    if not struct_result.valid:
        for err in struct_result.errors:
            print(f"  [STRUCTURE ERROR] {err.code}: {err.message}")
        print("Aborting: input has TLV structure errors.")
        return
    for w in struct_result.warnings:
        print(f"  [STRUCTURE WARNING] {w.code}: {w.message}")

    print(
        f"Validation passed: {struct_result.metadata['tag_count']} tag(s), "
        f"max depth {struct_result.metadata['max_depth']}"
    )

    # --- Parse (TLVNode enriches itself: metadata + bitmask + parent validation) ---
    print("Parsing TLV data...")
    try:
        tree = parse(fmt_result.cleaned_hex, "raw")
    except Exception as e:
        print(f"Error parsing as 'raw': {e}")
        print("Trying 'config' mode...")
        tree = parse(fmt_result.cleaned_hex, "config")

    print(f"Parsed {len(tree)} top-level nodes")

    # --- Collect parent validation issues ---
    invalid_parents = []

    def _scan_parents(nodes):
        for node in nodes:
            if not node.is_valid_parent:
                invalid_parents.append(node)
            _scan_parents(node.children)

    _scan_parents(tree)
    if invalid_parents:
        print(f"  ⚠  {len(invalid_parents)} parent validation issue(s) found (marked in output)")

    # --- Write formatted tree ---
    all_lines = []
    for node in tree:
        all_lines.extend(collect_lines(node, indent=0))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_lines) + "\n")

    print(f"Tree output written to: {output_file}")


def main():
    """Main entry point."""
    input_file = "test2.txt"
    output_file = "tree_output2.txt"

    print(f"Reading hex data from {input_file}...")

    try:
        with open(input_file, "r") as f:
            hex_data = f.read()

        print(f"Read {len(hex_data)} characters")
        generate_tree_output(hex_data, output_file)

        print("\nDone!")
        print(f"\nYou can view the tree hierarchy in: {output_file}")

    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        print("Please create test2.txt with your hex data.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
