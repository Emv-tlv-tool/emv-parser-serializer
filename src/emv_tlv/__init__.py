"""
EMV TLV Parser & Serializer

A Python library for parsing, decoding, and serializing EMV TLV
(Tag-Length-Value) data, with support for German payment terminal
protocols: ZVT transaction messages and Poseidon terminal configuration
blobs.
"""

from emv_tlv.core.tlv_parser import TLVParser
from emv_tlv.core.tlv_serializer import TLVSerializer
from emv_tlv.core.tlv_node import TLVNode
from emv_tlv.decoders.value_decoder import ValueDecoder
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder
from emv_tlv.adapters.zvt_adapter import ZVTAdapter
from emv_tlv.adapters.config_adapter import ConfigAdapter
from emv_tlv.dictionaries import Dictionary
from emv_tlv.validators import validate_hex, ValidationResult, ValidationError


class _ConfigResult(list):
    """A list of enhanced TLV nodes with extra config attributes."""
    def __init__(self, nodes, application_configs=None, ca_keys=None):
        super().__init__(nodes)
        self.application_configs = application_configs or []
        self.ca_keys = ca_keys or []


__all__ = [
    "parse",
    "serialize",
    "find_tag",
    "find_all_tags",
    "decode_node",
    "to_json",
    "TLVParser",
    "TLVSerializer",
    "TLVNode",
    "ValueDecoder",
    "BitmaskDecoder",
    "ZVTAdapter",
    "ConfigAdapter",
    "Dictionary",
]


def _ensure_bytes(data):
    """Convert hex string to bytes if needed."""
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        return bytes.fromhex(data)
    raise TypeError("Input must be bytes or hex string")


def _enhance_node(node):
    """Enhance a TLV node with metadata and decoded values."""
    metadata = Dictionary.lookup_by_tag(node.tag)
    enhanced = {
        "tag": node.tag,
        "length": node.length,
        "value": node.value.hex().upper(),
        "is_constructed": node.is_constructed,
    }

    if metadata:
        enhanced["name"] = metadata["name"]
        enhanced["description"] = metadata.get("description", "")
        enhanced["format"] = metadata.get("format", "")
        enhanced["source"] = metadata.get("source", "")
    else:
        enhanced["is_unknown"] = True

    if not node.is_constructed and len(node.value) > 0:
        try:
            enhanced["decoded"] = ValueDecoder.decode_value(node.tag, node.value)
        except Exception:
            enhanced["decoded"] = node.value.hex().upper()
        if metadata and metadata.get("format") == "bitmask":
            enhanced["bitmask"] = BitmaskDecoder.decode_bitmask(node.tag, node.value)

    if node.is_constructed and len(node.children) > 0:
        enhanced["children"] = [_enhance_node(child) for child in node.children]

    return enhanced


def _reconstruct_node(enhanced_node):
    """Reconstruct a TLVNode from an enhanced node dict."""
    node = TLVNode(
        enhanced_node["tag"],
        bytes.fromhex(enhanced_node["value"]),
        enhanced_node.get("is_constructed", False),
    )
    if "children" in enhanced_node:
        for child in enhanced_node["children"]:
            node.add_child(_reconstruct_node(child))
    return node


def parse(data, type_="raw"):
    """
    Parse input data based on type.

    Args:
        data: Raw bytes or hex string
        type_: Parser type: 'raw', 'zvt', or 'config'

    Returns:
        Parsed data structure

    Examples:
        >>> parse('9A03210315', 'raw')
        >>> parse(buffer, 'zvt')
        >>> parse(buffer, 'config')
    """
    if type_ not in ("raw", "zvt", "config"):
        raise ValueError(f"Unknown type: {type_}. Use 'raw', 'zvt', or 'config'")

    buffer = _ensure_bytes(data)

    if type_ == "raw":
        return _parse_raw(buffer)
    elif type_ == "zvt":
        return _parse_zvt(buffer)
    else:
        return _parse_config(buffer)


def _parse_raw(buffer):
    """Parse raw TLV data."""
    nodes = TLVParser.parse(buffer)
    return [_enhance_node(node) for node in nodes]


def _parse_zvt(buffer):
    """Parse ZVT message."""
    message = ZVTAdapter.parse(buffer)
    tlv_nodes = ZVTAdapter.extract_emv_tlv(message)

    return {
        "ctrl": message["ctrl"],
        "ctrl_name": message["ctrl_name"],
        "length": message["length"],
        "bmp_fields": message["bmp_fields"],
        "tlv": [_enhance_node(node) for node in tlv_nodes],
    }


def _parse_config(buffer):
    """Parse Poseidon config blob."""
    nodes = ConfigAdapter.parse(buffer)
    enhanced_nodes = [_enhance_node(node) for node in nodes]

    application_configs = ConfigAdapter.get_application_configs(nodes)
    ca_keys = ConfigAdapter.get_ca_keys(nodes)

    return _ConfigResult(
        enhanced_nodes,
        application_configs=application_configs,
        ca_keys=ca_keys,
    )


def serialize(nodes):
    """
    Serialize TLV nodes to hex string.

    Args:
        nodes: A single node dict or a list of node dicts

    Returns:
        Hex string
    """
    if not isinstance(nodes, list):
        nodes = [nodes]

    parts = []
    for node in nodes:
        if hasattr(node, "_raw_node"):
            parts.append(TLVSerializer.serialize(node._raw_node))
        else:
            tlv_node = _reconstruct_node(node)
            parts.append(TLVSerializer.serialize(tlv_node))

    return "".join(parts)


def find_tag(tree, tag_hex):
    """
    Find a tag in the TLV tree (depth-first search).

    Args:
        tree: TLV tree (list of enhanced nodes)
        tag_hex: Tag to find in hex format (e.g., '9A', '84')

    Returns:
        Found node dict or None
    """
    for node in tree:
        if node["tag"] == tag_hex:
            return node
        if "children" in node:
            found = find_tag(node["children"], tag_hex)
            if found:
                return found
    return None


def find_all_tags(tree, tag_hex):
    """
    Find all occurrences of a tag in the TLV tree (depth-first search).

    Args:
        tree: TLV tree (list of enhanced nodes)
        tag_hex: Tag to find in hex format

    Returns:
        List of found node dicts
    """
    results = []
    for node in tree:
        if node["tag"] == tag_hex:
            results.append(node)
        if "children" in node:
            results.extend(find_all_tags(node["children"], tag_hex))
    return results


def decode_node(node):
    """
    Re-decode a node's value.

    Args:
        node: TLV node dict

    Returns:
        Node dict with updated decoded value and/or bitmask
    """
    result = dict(node)

    if not node.get("is_constructed", False) and node.get("value"):
        value_bytes = bytes.fromhex(node["value"])
        try:
            result["decoded"] = ValueDecoder.decode_value(node["tag"], value_bytes)
        except Exception:
            result["decoded"] = node["value"]
        metadata = Dictionary.lookup_by_tag(node["tag"])
        if metadata and metadata.get("format") == "bitmask":
            result["bitmask"] = BitmaskDecoder.decode_bitmask(node["tag"], value_bytes)

    return result


def to_json(tree):
    """
    Convert TLV tree to JSON-friendly format.

    Args:
        tree: TLV tree (list of enhanced nodes)

    Returns:
        List of cleaned node dicts
    """
    result = []
    for node in tree:
        item = {
            "tag": node["tag"],
            "name": node.get("name"),
            "length": node["length"],
            "value": node["value"],
        }
        if "decoded" in node:
            item["decoded"] = node["decoded"]
        if "bitmask" in node:
            item["bitmask"] = node["bitmask"]
        if "children" in node and node["children"]:
            item["children"] = to_json(node["children"])
        result.append(item)
    return result