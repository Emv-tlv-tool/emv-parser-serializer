"""
ZVT Adapter - Parses ZVT (ZahlVerkehrsTerminal) messages.

ZVT is the protocol used in German payment terminals.

Message Structure:
- CTRL (2 bytes): Message type/command code
- Length (1-3 bytes): Payload length
  - 0x00-0xFE: Direct length value
  - 0xFF: Extended length (next 2 bytes)
- BMP Fields: Tag-Length-Value encoded data
  - Each BMP field: 1-byte tag, 1-byte length, variable value

EMV TLV data is embedded in BMP tags:
- 0x9A: Transaction-related EMV data
- 0xAA: Additional EMV data
- 0x3B: Card-related EMV data
"""

from emv_tlv.core.tlv_parser import TLVParser

# ZVT CTRL codes
_CTRL_CODES: dict[str, str] = {
    "0601": "Authorisation",
    "060F": "Authorisation Response",
    "061E": "End of Day",
    "060B": "Status Enquiry",
    "068A": "Print Line",
    "8000": "ACK",
    "8400": "Abort",
}

# BMP tags that contain EMV TLV data
_EMV_BMP_TAGS = {0x9A, 0xAA, 0x3B}


class ZVTAdapter:
    """Adapter for parsing and serializing ZVT messages."""

    @staticmethod
    def parse(data: bytes) -> dict:
        """
        Parse a ZVT message buffer.

        Args:
            data: Raw ZVT message bytes

        Returns:
            Parsed message dict with ctrl, ctrl_name, length, and bmp_fields
        """
        offset = 0

        # Parse CTRL (2 bytes)
        ctrl = data[0:2].hex().upper()
        offset += 2

        # Parse Length (1-3 bytes)
        if data[offset] == 0xFF:
            # Extended length: 0xFF + 2 bytes
            length = (data[offset + 1] << 8) | data[offset + 2]
            length_bytes = 3
        else:
            # Direct length
            length = data[offset]
            length_bytes = 1
        offset += length_bytes

        # Parse BMP fields
        bmp_fields: list[dict] = []
        payload_end = offset + length

        while offset < payload_end:
            bmp_tag = data[offset]
            bmp_length = data[offset + 1]
            offset += 2

            bmp_value = data[offset : offset + bmp_length]
            offset += bmp_length

            bmp_fields.append({
                "tag": f"{bmp_tag:02X}",
                "length": bmp_length,
                "value": bmp_value,
            })

        return {
            "ctrl": ctrl,
            "ctrl_name": _CTRL_CODES.get(ctrl, "Unknown"),
            "length": length,
            "bmp_fields": bmp_fields,
        }

    @staticmethod
    def extract_emv_tlv(message: dict) -> list:
        """
        Extract EMV TLV data from BMP fields.

        BMP tags 0x9A, 0xAA, and 0x3B contain EMV TLV data.

        Args:
            message: Parsed ZVT message dict

        Returns:
            List of parsed TLVNode trees
        """
        tlv_trees: list = []

        for bmp in message["bmp_fields"]:
            tag_value = int(bmp["tag"], 16)

            if tag_value in _EMV_BMP_TAGS:
                # Parse the BMP value as EMV TLV
                nodes = TLVParser.parse(bmp["value"])
                tlv_trees.extend(nodes)

        return tlv_trees

    @staticmethod
    def serialize(message: dict) -> bytes:
        """
        Serialize a ZVT message.

        Args:
            message: Message dict with ctrl and bmp_fields

        Returns:
            Serialized ZVT message bytes
        """
        parts: list[bytes] = []

        # CTRL (2 bytes)
        ctrl_bytes = bytes.fromhex(message["ctrl"])
        parts.append(ctrl_bytes)

        # Calculate payload length
        payload_length = 0
        for bmp in message["bmp_fields"]:
            payload_length += 2 + len(bmp["value"])  # Tag(1) + Length(1) + Value

        # Length encoding
        if payload_length <= 0xFE:
            length_bytes = bytes([payload_length])
        else:
            length_bytes = bytes([
                0xFF,
                (payload_length >> 8) & 0xFF,
                payload_length & 0xFF,
            ])
        parts.append(length_bytes)

        # BMP fields
        for bmp in message["bmp_fields"]:
            tag_byte = bytes([int(bmp["tag"], 16)])
            len_byte = bytes([len(bmp["value"])])
            parts.append(tag_byte)
            parts.append(len_byte)
            parts.append(bmp["value"])

        return b"".join(parts)

    @staticmethod
    def get_ctrl_name(ctrl: str) -> str:
        """Get CTRL code name."""
        return _CTRL_CODES.get(ctrl, "Unknown")

    @staticmethod
    def is_emv_bmp_tag(bmp_tag: str) -> bool:
        """Check if BMP tag contains EMV data."""
        tag_value = int(bmp_tag, 16)
        return tag_value in _EMV_BMP_TAGS