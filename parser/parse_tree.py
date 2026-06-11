#!/usr/bin/env python3
"""
EMV TLV Tree Generator

Reads hex data from test.txt, parses it as EMV TLV,
and generates a detailed tree hierarchy output file.
"""

from emv_tlv import parse, Dictionary
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder


def decode_dictionary_bitmask(node):
    """
    Decode bitmask using bytes definitions from the tag dictionary.
    
    The merged dictionaries now contain 'bytes' arrays with bit-level
    definitions for bitmask tags. This function reads those definitions
    and produces the same {byte, mask, name, set} format as BitmaskDecoder.
    """
    tag = node.get("tag", "")
    value_hex = node.get("value", "")
    if not value_hex:
        return None
    
    metadata = Dictionary.lookup_by_tag(tag)
    if not metadata:
        return None
    
    bytes_defs = metadata.get("bytes")
    if not bytes_defs:
        return None
    
    value_bytes = bytes.fromhex(value_hex)
    results = []
    
    for byte_def in bytes_defs:
        byte_index = byte_def.get("index", 1) - 1  # 1-based to 0-based
        if byte_index >= len(value_bytes):
            continue
        
        byte_value = value_bytes[byte_index]
        
        for bit_def in byte_def.get("bits", []):
            if "multi_bit" in bit_def and bit_def["multi_bit"]:
                # Multi-bit field: just show as set if any bit in the field is set
                results.append({
                    "byte": byte_index,
                    "mask": 0x00,
                    "name": bit_def.get("label", ""),
                    "set": byte_value != 0,
                })
            else:
                bit = bit_def.get("bit", 0)
                mask = 1 << (bit - 1) if bit > 0 else 0
                results.append({
                    "byte": byte_index,
                    "mask": mask,
                    "name": bit_def.get("label", ""),
                    "set": bool(byte_value & mask),
                })
    
    return results if results else None


def enrich_tree_with_bitmasks(tree):
    """Walk the tree and enrich nodes with dictionary-based bitmask data."""
    for node in tree:
        # Skip if bitmask already set by BitmaskDecoder
        if "bitmask" not in node or not node["bitmask"]:
            bitmask = decode_dictionary_bitmask(node)
            if bitmask:
                node["bitmask"] = bitmask
        
        if "children" in node:
            enrich_tree_with_bitmasks(node["children"])
    return tree


def collect_lines(node, indent=0, is_last=True):
    """
    Collect tree lines recursively with visual tree connectors.
    """
    lines = []
    
    # Connector prefix
    if indent == 0:
        prefix = "+--+ "
    else:
        prefix = "  " * indent + "+--+ "
    
    # Header
    tag = node.get("tag", "")
    name = node.get("name", "")
    description = node.get("description", "")
    length = node.get("length", 0)
    value_hex = node.get("value", "")
    
    if name:
        header = f"{tag} ({name}, len=0x{length:02X})"
        if description and description != name:
            header = f"{tag} ({description}, len=0x{length:02X})"
    else:
        header = f"{tag} (len=0x{length:02X})"
    
    if value_hex:
        header += f' value="{value_hex}"'
    
    lines.append(prefix + header)
    
    # Bitmask details grouped by byte (if any)
    if "bitmask" in node and node["bitmask"]:
        value_bytes = bytes.fromhex(value_hex) if value_hex else b""
        
        # Group bits by byte index
        bytes_map = {}
        for bit in node["bitmask"]:
            byte_idx = bit.get("byte", 0)
            mask = bit.get("mask", 0)
            if byte_idx not in bytes_map:
                byte_val = value_bytes[byte_idx] if byte_idx < len(value_bytes) else 0
                bytes_map[byte_idx] = {
                    "value": byte_val,
                    "bits": []
                }
            if bit.get("set", False):
                bytes_map[byte_idx]["bits"].append(bit)
        
        if bytes_map:
            sorted_bytes = sorted(bytes_map.keys())
            base_indent = "  " * (indent + 1)
            for i, byte_idx in enumerate(sorted_bytes):
                byte_data = bytes_map[byte_idx]
                is_last_byte = (i == len(sorted_bytes) - 1)
                pipe = "|" if not is_last_byte else " "
                
                if indent == 0:
                    byte_line = f"  +--+ Byte {byte_idx + 1} ({byte_data['value']:02X})"
                else:
                    byte_line = f"  " * (indent + 1) + f"+--+ Byte {byte_idx + 1} ({byte_data['value']:02X})"
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

    # Children
    children = node.get("children", [])
    if children:
        for child in children:
            lines.extend(collect_lines(child, indent + 1))
            
    return lines


def generate_tree_output(hex_data, output_file="tree_output.txt"):
    """
    Parse hex data and generate formatted tree output.
    
    Args:
        hex_data: Hex string to parse
        output_file: Output file path
    """
    print("Parsing TLV data...")
    
    # Remove whitespace and newlines
    hex_data = "".join(hex_data.split())
    
    # Parse as raw EMV TLV (could also try 'config' mode)
    try:
        tree = parse(hex_data, 'raw')
    except Exception as e:
        print(f"Error parsing as 'raw': {e}")
        print("Trying 'config' mode...")
        tree = parse(hex_data, 'config')
    
    print(f"Parsed {len(tree)} top-level nodes")
    
    # Enrich tree with dictionary-based bitmask data
    tree = enrich_tree_with_bitmasks(tree)
    
    # Collect all lines
    all_lines = []
    for node in tree:
        all_lines.extend(collect_lines(node, indent=0))
        
    # Generate formatted output with lines separated by blank lines
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(all_lines) + "\n")
    
    print(f"Tree output written to: {output_file}")


def main():
    """Main entry point."""
    input_file = "test.txt"
    output_file = "tree_output.txt"
    
    print(f"Reading hex data from {input_file}...")
    
    try:
        with open(input_file, 'r') as f:
            hex_data = f.read()
        
        print(f"Read {len(hex_data)} characters")
        
        generate_tree_output(hex_data, output_file)
        
        print("\nDone!")
        print(f"\nYou can view the tree hierarchy in: {output_file}")
        
    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        print("Please create test.txt with your hex data.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
