from emv_tlv.core.tlv_node import TLVNode


class TLVParser:
    """Parser for BER-TLV encoded data."""

    @staticmethod
    def parse(data: bytes, clean_edges: bool = True) -> list[TLVNode]:
        """
        Parse a buffer containing TLV-encoded data.

        Args:
            data: Raw TLV data bytes
            clean_edges: If True, remove leading/trailing 0x00 and 0xFF padding
                         (use False for recursive parsing of sub-fields)

        Returns:
            List of parsed TLVNode objects

        Raises:
            ValueError: If data is malformed or truncated
        """
        # Optionnel : nettoyer les extrêmes (uniquement pour le buffer racine)
        if clean_edges:
            start = 0
            end = len(data)

            # Enlever les padding 0x00 et 0xFF au début
            while start < end and data[start] in (0x00, 0xFF):
                start += 1

            # Enlever les padding 0x00 et 0xFF à la fin
            while end > start and data[end - 1] in (0x00, 0xFF):
                end -= 1

            if start >= end:
                return []

            data = data[start:end]

        # Parsing proprement dit (sans jamais sauter d'octet)
        nodes = []
        offset = 0
        while offset < len(data):
            node, next_offset = TLVParser._parse_node(data, offset)
            nodes.append(node)
            offset = next_offset

        return nodes

    @staticmethod
    def _parse_node(data: bytes, offset: int) -> tuple[TLVNode, int]:
        """
        Parse a single TLV node from buffer starting at offset.
        """
        first_tag_byte = data[offset]

        tag, tag_length = TLVParser._parse_tag(data, offset)
        offset += tag_length

        length, length_bytes = TLVParser._parse_length(data, offset)
        offset += length_bytes

        if offset + length > len(data):
            raise ValueError(
                f"Buffer overrun: insufficient bytes for value "
                f"(need {length}, have {len(data) - offset})"
            )

        value = data[offset : offset + length]
        offset += length

        is_constructed = bool(first_tag_byte & 0x20)

        node = TLVNode(tag, value, is_constructed)

        # Appel récursif : on désactive le nettoyage des extrémités
        if is_constructed and length > 0:
            children = TLVParser.parse(value, clean_edges=False)
            for child in children:
                node.add_child(child)

        return node, offset

    @staticmethod
    def _parse_tag(data: bytes, offset: int) -> tuple[str, int]:
        if offset >= len(data):
            raise ValueError("Buffer overrun: cannot read tag")

        first_byte = data[offset]
        tag_length = 1

        if (first_byte & 0x1F) == 0x1F:
            while offset + tag_length < len(data):
                next_byte = data[offset + tag_length]
                tag_length += 1
                if (next_byte & 0x80) == 0:
                    break
            if offset + tag_length > len(data):
                raise ValueError("Buffer overrun: incomplete multi-byte tag")

        tag = data[offset : offset + tag_length].hex().upper()
        return tag, tag_length

    @staticmethod
    def _parse_length(data: bytes, offset: int, lenient: bool = True) -> tuple[int, int]:
        if offset >= len(data):
            raise ValueError("Buffer overrun: cannot read length")

        first_byte = data[offset]

        if first_byte <= 0x7F:
            return first_byte, 1
        elif first_byte == 0x81:
            if offset + 1 >= len(data):
                raise ValueError("Buffer overrun: cannot read extended length")
            return data[offset + 1], 2
        elif first_byte == 0x82:
            if offset + 2 >= len(data):
                raise ValueError("Buffer overrun: cannot read extended length")
            length = (data[offset + 1] << 8) | data[offset + 2]
            return length, 3
        elif lenient and 0x83 <= first_byte <= 0xFE:
            num_bytes = first_byte - 0x80
            if offset + num_bytes + 1 > len(data):
                raise ValueError(
                    f"Buffer overrun: cannot read ZKA extended length ({num_bytes} bytes)"
                )
            length = 0
            for i in range(num_bytes):
                length = (length << 8) | data[offset + 1 + i]
            return length, 1 + num_bytes
        else:
            raise ValueError(f"Invalid length encoding: 0x{first_byte:02x}")