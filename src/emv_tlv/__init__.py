"""
EMV TLV Parser & Serializer

A Python library for parsing, decoding, and serializing EMV TLV
(Tag-Length-Value) data, with support for German payment terminal
protocols: ZVT transaction messages and Poseidon terminal configuration
blobs.
"""

from emv_tlv.adapters.config_adapter import ConfigAdapter
from emv_tlv.adapters.zvt_adapter import ZVTAdapter
from emv_tlv.core.tlv_node import TLVNode
from emv_tlv.core.tlv_parser import TLVParser
from emv_tlv.core.tlv_serializer import TLVSerializer
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder
from emv_tlv.decoders.value_decoder import ValueDecoder
from emv_tlv.dictionaries import Dictionary
from emv_tlv.validators import validate_hex


class _ConfigResult(list):
    """A list of enhanced TLV nodes with extra config attributes."""

    def __init__(self, nodes, application_configs=None, ca_keys=None):
        super().__init__(nodes)
        self.application_configs = application_configs or []
        self.ca_keys = ca_keys or []


__all__ = [
    "parse",
    "serialize",
    "validate_hex",
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
    return node


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
            # ZVT adapter nodes have a _raw_node reference
            parts.append(TLVSerializer.serialize(node._raw_node))
        elif isinstance(node, TLVNode):
            # Optimization #5: TLVNode instances can be passed directly
            # to the serializer without reconstruction
            parts.append(TLVSerializer.serialize(node))
        else:
            # Plain dict nodes need reconstruction into TLVNode
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
