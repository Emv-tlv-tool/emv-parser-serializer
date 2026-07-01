from emv_tlv.core.tlv_node import TLVNode


class TLVParser:
    """Parser for BER-TLV encoded data."""

    @staticmethod
    def parse(data: bytes) -> list[TLVNode]:
        """
        Parse a buffer containing TLV-encoded data.

        Args:
            data: Raw TLV data bytes

        Returns:
            List of parsed TLVNode objects

        Raises:
            ValueError: If data is malformed or truncated
        """
        nodes = []
        offset = 0
        while offset < len(data):
            # Ne pas sauter 0x00 ni 0xFF !
            node, next_offset = TLVParser._parse_node(data, offset)
            nodes.append(node)
            offset = next_offset
        return nodes

    @staticmethod
    def _parse_node(data: bytes, offset: int) -> tuple[TLVNode, int]:
        """
        Parse a single TLV node from buffer starting at offset.

        Args:
            data: Source buffer
            offset: Starting position

        Returns:
            Tuple of (TLVNode, next_offset)

        Raises:
            ValueError: If insufficient bytes available
        """
        # Save first byte for constructed detection
        first_tag_byte = data[offset]

        # Parse tag (1 or 2 bytes)
        tag, tag_length = TLVParser._parse_tag(data, offset)
        offset += tag_length

        # Parse length (1-3 bytes)
        length, length_bytes = TLVParser._parse_length(data, offset)
        offset += length_bytes

        # Check buffer bounds
        if offset + length > len(data):
            raise ValueError(
                f"Buffer overrun: insufficient bytes for value "
                f"(need {length}, have {len(data) - offset})"
            )

        # Extract value
        value = data[offset : offset + length]
        offset += length

        # Determine if constructed (bit 6 of first tag byte)
        is_constructed = bool(first_tag_byte & 0x20)

        # Create node
        node = TLVNode(tag, value, is_constructed)

        # Recursively parse children for constructed nodes
        if is_constructed and length > 0:
            children = TLVParser.parse(value)
            for child in children:
                node.add_child(child)

        return node, offset

    @staticmethod
    def _parse_tag(data: bytes, offset: int) -> tuple[str, int]:
        """
        Parse tag bytes from buffer.

        Tag encoding rules:
        - If lower 5 bits of first byte are 0x1F, tag is multi-byte
        - For multi-byte tags, continue reading while bit 8 is set (0x80)
        - Otherwise, tag is single byte

        Args:
            data: Source buffer
            offset: Starting position

        Returns:
            Tuple of (tag_hex_string, tag_length_in_bytes)
        """
        if offset >= len(data):
            raise ValueError("Buffer overrun: cannot read tag")

        first_byte = data[offset]
        tag_length = 1

        # Check if lower 5 bits are all 1s (0x1F) - indicates multi-byte tag
        if (first_byte & 0x1F) == 0x1F:
            # Multi-byte tag: continue reading while bit 8 is set
            while offset + tag_length < len(data):
                next_byte = data[offset + tag_length]
                tag_length += 1
                # If bit 8 is NOT set, this is the last byte
                if (next_byte & 0x80) == 0:
                    break

            # Check if we have all bytes
            if offset + tag_length > len(data):
                raise ValueError("Buffer overrun: incomplete multi-byte tag")

        tag = data[offset : offset + tag_length].hex().upper()
        return tag, tag_length

    @staticmethod
    def _parse_length(data: bytes, offset: int, lenient: bool = True) -> tuple[int, int]:
        """
        Parse length bytes from buffer.

        Length encoding rules:
        - 0x00-0x7F: Direct length value (1 byte)
        - 0x81: Next byte contains length (2 bytes total)
        - 0x82: Next 2 bytes contain length (3 bytes total)
        - 0x83-0xFE: ZKA/Poseidon extended forms (lenient mode)
          - 0x83: Next 3 bytes contain length (4 bytes total)
          - 0x84: Next 4 bytes contain length (5 bytes total)
          - etc. (first_byte - 0x80 = number of subsequent length bytes)
        - 0xFF: Reserved/invalid in standard BER-TLV

        Args:
            data: Source buffer
            offset: Starting position
            lenient: Accept ZKA extended-length forms (default: True)

        Returns:
            Tuple of (length, length_bytes)
        """
        if offset >= len(data):
            raise ValueError("Buffer overrun: cannot read length")

        first_byte = data[offset]

        if first_byte <= 0x7F:
            # Short form: length is in first byte
            return first_byte, 1

        elif first_byte == 0x81:
            # 2-byte form: next byte is length
            if offset + 1 >= len(data):
                raise ValueError("Buffer overrun: cannot read extended length")
            return data[offset + 1], 2

        elif first_byte == 0x82:
            # 3-byte form: next 2 bytes are length (big-endian)
            if offset + 2 >= len(data):
                raise ValueError("Buffer overrun: cannot read extended length")
            length = (data[offset + 1] << 8) | data[offset + 2]
            return length, 3

        elif lenient and 0x83 <= first_byte <= 0xFE:
            # ZKA/Poseidon extended-length forms
            # Number of subsequent bytes = first_byte - 0x80
            num_bytes = first_byte - 0x80

            if offset + num_bytes + 1 > len(data):
                raise ValueError(
                    f"Buffer overrun: cannot read ZKA extended length " f"({num_bytes} bytes)"
                )

            # Read length as big-endian
            length = 0
            for i in range(num_bytes):
                length = (length << 8) | data[offset + 1 + i]
            return length, 1 + num_bytes

        else:
            raise ValueError(f"Invalid length encoding: 0x{first_byte:02x}")
