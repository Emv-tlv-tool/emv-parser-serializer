#!/usr/bin/env python3
"""
EMV TLV Tree Generator

Reads hex data from test.txt, parses it as EMV TLV,
and generates a detailed tree hierarchy output file.
"""

from emv_tlv import parse, Dictionary
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder


def collect_lines(node, indent=0):
    """
    Collect tree lines recursively with indentation, without connectors.
    """
    lines = []
    indent_str = " " * (indent * 4)
    prop_str = " " * (indent * 4 + 2)

    # Header
    tag = node.get("tag", "")
    name = node.get("name", "")
    description = node.get("description", "")
    if name:
        header = f"[{tag}] {name}"
        if description and description != name:
            header += f" - {description}"
    else:
        header = f"[{tag}]"
        
    value_hex = node.get("value", "")
    if value_hex:
        header += f": {value_hex}"
        
    lines.append(indent_str + header)

    # Bitmask details (if any)
    if "bitmask" in node and node["bitmask"]:
        set_bits = [b for b in node["bitmask"] if b["set"]]
        if set_bits:
            lines.append(prop_str + "Bitmask details:")
            bit_indent = " " * (indent * 4 + 4)
            for bit in set_bits:
                lines.append(bit_indent + f"- Byte {bit['byte']}, Mask 0x{bit['mask']:02X}: {bit['name']}")

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
