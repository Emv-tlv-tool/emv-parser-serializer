"""
TLVSerializer - Serializes TLVNode structures back to BER-TLV encoded bytes.

Serialization Rules:
1. Encode tag (1 or 2 bytes based on tag value)
2. Encode length (short form for < 128, long form otherwise)
3. For constructed nodes: serialize children first, then compute parent length

Output is uppercase hex string for readability and interoperability.
"""

from emv_tlv.core.tlv_node import TLVNode


class TLVSerializer:
    """Serializes TLVNode structures to BER-TLV encoded hex strings."""

    @staticmethod
    def serialize(node: TLVNode) -> str:
        """
        Serialize a TLVNode to hex string.

        Args:
            node: Node to serialize

        Returns:
            Uppercase hex string
        """
        tag_bytes = TLVSerializer._encode_tag(node.tag)
        value_bytes = TLVSerializer._serialize_value(node)
        length_bytes = TLVSerializer._encode_length(len(value_bytes))
        return (tag_bytes + length_bytes + value_bytes).hex().upper()

    @staticmethod
    def _encode_tag(tag: str) -> bytes:
        """
        Encode tag to bytes.

        Tags are encoded directly from their hex string representation.
        Supports 1-byte (e.g., '9A'), 2-byte (e.g., '9F02'), and
        3-byte (e.g., 'DF850D') tags.

        Args:
            tag: Tag in hex string format (e.g., '9A', '9F02')

        Returns:
            Tag bytes
        """
        return bytes.fromhex(tag)

    @staticmethod
    def _encode_length(length: int) -> bytes:
        """
        Encode length to bytes.

        Length encoding rules:
        - 0-127: Single byte (0x00-0x7F)
        - 128-255: Two bytes (0x81 XX)
        - 256-65535: Three bytes (0x82 XX YY)

        Args:
            length: Value length

        Returns:
            Length bytes
        """
        if length <= 127:
            # Short form: single byte
            return bytes([length])
        elif length <= 255:
            # 2-byte form: 0x81 prefix
            return bytes([0x81, length])
        elif length <= 65535:
            # 3-byte form: 0x82 prefix + 2-byte big-endian length
            return bytes([0x82, (length >> 8) & 0xFF, length & 0xFF])
        else:
            raise ValueError(
                f"Length {length} exceeds maximum supported value (65535)"
            )

    @staticmethod
    def _serialize_value(node: TLVNode) -> bytes:
        """
        Serialize node's value.

        For primitive nodes: return the value buffer.
        For constructed nodes: serialize all children and concatenate.

        Args:
            node: Node whose value to serialize

        Returns:
            Value bytes
        """
        if node.is_primitive():
            return node.value or b""
        else:
            child_buffers = [
                bytes.fromhex(TLVSerializer.serialize(child))
                for child in node.children
            ]
            return b"".join(child_buffers)

    @staticmethod
    def serialize_multiple(nodes: list[TLVNode]) -> str:
        """
        Serialize multiple nodes to hex string.

        Useful for serializing a list of top-level TLV elements.

        Args:
            nodes: List of nodes to serialize

        Returns:
            Uppercase hex string
        """
        buffers = [
            bytes.fromhex(TLVSerializer.serialize(node)) for node in nodes
        ]
        return b"".join(buffers).hex().upper()