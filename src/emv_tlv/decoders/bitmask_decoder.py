"""
BitmaskDecoder - Bit-level decoding for EMV bitmask tags.

Decodes tags where each bit represents a specific flag or option:
- TVR (95): Terminal Verification Results
- Terminal Capabilities (9F33): Terminal feature support
- Additional Terminal Capabilities (9F40): Extended terminal features
- TAC tags (DF11, DF12, DF13): Terminal Action Codes

Returns list of {byte, mask, name, set} dicts.
"""
from emv_tlv.dictionaries import Dictionary

# TVR (Terminal Verification Results) - Tag 95, 5 bytes
_TVR_BITS = [
    # Byte 1 - Offline data authentication results
    [
        {"mask": 0x80, "name": "Offline data authentication was not performed"},
        {"mask": 0x40, "name": "SDA failed"},
        {"mask": 0x20, "name": "ICC data missing"},
        {"mask": 0x10, "name": "Card appears on terminal exception file"},
        {"mask": 0x08, "name": "DDA failed"},
        {"mask": 0x04, "name": "CDA failed"},
        {"mask": 0x02, "name": "SDA selected but not supported"},
        {"mask": 0x01, "name": "CDA selected but not supported"},
    ],
    # Byte 2 - Cardholder verification results
    [
        {"mask": 0x80, "name": "Cardholder verification was not successful"},
        {"mask": 0x40, "name": "Unrecognised CVM"},
        {"mask": 0x20, "name": "PIN Try Limit exceeded"},
        {"mask": 0x10, "name": "PIN entry required and PIN pad not present or not working"},
        {"mask": 0x08, "name": "PIN entry required, PIN pad present, but PIN was not entered"},
        {"mask": 0x04, "name": "Online PIN entered"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 3 - Transaction risk management
    [
        {"mask": 0x80, "name": "Transaction exceeds floor limit"},
        {"mask": 0x40, "name": "Lower consecutive offline limit exceeded"},
        {"mask": 0x20, "name": "Upper consecutive offline limit exceeded"},
        {"mask": 0x10, "name": "Transaction selected randomly for online processing"},
        {"mask": 0x08, "name": "Merchant forced transaction online"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 4 - Issuer authentication results
    [
        {"mask": 0x80, "name": "Default TDOL rejected"},
        {"mask": 0x40, "name": "Issuer authentication failed"},
        {"mask": 0x20, "name": "Reserved for use by EMVCo"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "Transaction not permitted on card"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 5 - Relay resistance/terminal actions
    [
        {"mask": 0x80, "name": "Relay resistance threshold exceeded"},
        {"mask": 0x40, "name": "Relay resistance time limits exceeded"},
        {"mask": 0x20, "name": "Reserved for use by EMVCo"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "Reserved for use by EMVCo"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
]

# Terminal Capabilities - Tag 9F33, 3 bytes
_TERMINAL_CAPABILITIES_BITS = [
    # Byte 1 - Card data input capability
    [
        {"mask": 0x80, "name": "Reserved for use by EMVCo"},
        {"mask": 0x40, "name": "Manual key entry"},
        {"mask": 0x20, "name": "Magnetic stripe"},
        {"mask": 0x10, "name": "IC with contacts"},
        {"mask": 0x08, "name": "Reserved for use by EMVCo"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 2 - CVM capability
    [
        {"mask": 0x80, "name": "Plaintext PIN for ICC verification"},
        {"mask": 0x40, "name": "Enciphered PIN for online verification"},
        {"mask": 0x20, "name": "Signature (paper)"},
        {"mask": 0x10, "name": "Enciphered PIN for offline verification"},
        {"mask": 0x08, "name": "Reserved for use by EMVCo"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 3 - Security capability
    [
        {"mask": 0x80, "name": "SDA"},
        {"mask": 0x40, "name": "DDA"},
        {"mask": 0x20, "name": "Card capture"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "CDA"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
]

# Additional Terminal Capabilities - Tag 9F40, 5 bytes
_ADDITIONAL_TERMINAL_CAPABILITIES_BITS = [
    # Byte 1 - Transaction type capability
    [
        {"mask": 0x80, "name": "Goods and services"},
        {"mask": 0x40, "name": "Cash"},
        {"mask": 0x20, "name": "Cashback"},
        {"mask": 0x10, "name": "Inquiry"},
        {"mask": 0x08, "name": "Transfer"},
        {"mask": 0x04, "name": "Payment"},
        {"mask": 0x02, "name": "Administrative"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 2-5 - Reserved
    *[
        [
            {"mask": mask, "name": "Reserved for use by EMVCo"}
            for mask in (0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01)
        ]
        for _ in range(4)
    ],
]

# TAC (Terminal Action Code) - Tags DF11, DF12, DF13, 5 bytes
_TAC_BITS = [
    # Byte 1 - Offline authentication results
    [
        {"mask": 0x80, "name": "Offline PIN try limit exceeded"},
        {"mask": 0x40, "name": "Offline PIN entered"},
        {"mask": 0x20, "name": "PIN try limit exceeded"},
        {"mask": 0x10, "name": "Offline PIN not supported"},
        {"mask": 0x08, "name": "Offline PIN entered successfully"},
        {"mask": 0x04, "name": "Cardholder verification not successful"},
        {"mask": 0x02, "name": "Unrecognised CVM"},
        {"mask": 0x01, "name": "PIN try limit exceeded (No CVM)"},
    ],
    # Byte 2 - Card risk management
    [
        {"mask": 0x80, "name": "Card is on exception file"},
        {"mask": 0x40, "name": "New card"},
        {"mask": 0x20, "name": "Reserved for use by EMVCo"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "Reserved for use by EMVCo"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 3 - Transaction risk management
    [
        {"mask": 0x80, "name": "Transaction exceeds floor limit"},
        {"mask": 0x40, "name": "Lower consecutive offline limit exceeded"},
        {"mask": 0x20, "name": "Upper consecutive offline limit exceeded"},
        {"mask": 0x10, "name": "Transaction selected randomly for online processing"},
        {"mask": 0x08, "name": "Merchant forced transaction online"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 4 - Issuer authentication and script
    [
        {"mask": 0x80, "name": "Issuer authentication failed"},
        {"mask": 0x40, "name": "Script processing failed"},
        {"mask": 0x20, "name": "Reserved for use by EMVCo"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "Transaction not permitted on card"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
    # Byte 5 - Relay resistance and other
    [
        {"mask": 0x80, "name": "Relay resistance threshold exceeded"},
        {"mask": 0x40, "name": "Relay resistance time limits exceeded"},
        {"mask": 0x20, "name": "Reserved for use by EMVCo"},
        {"mask": 0x10, "name": "Reserved for use by EMVCo"},
        {"mask": 0x08, "name": "Reserved for use by EMVCo"},
        {"mask": 0x04, "name": "Reserved for use by EMVCo"},
        {"mask": 0x02, "name": "Reserved for use by EMVCo"},
        {"mask": 0x01, "name": "Reserved for use by EMVCo"},
    ],
]

# Map tags to their bit definitions
_BITMASK_DEFINITIONS: dict[str, list] = {
    "95": _TVR_BITS,
    "9F33": _TERMINAL_CAPABILITIES_BITS,
    "9F40": _ADDITIONAL_TERMINAL_CAPABILITIES_BITS,
    "DF11": _TAC_BITS,
    "DF12": _TAC_BITS,
    "DF13": _TAC_BITS,
}


class BitmaskDecoder:
    """Bit-level decoding for EMV bitmask tags."""

    @staticmethod
    def decode_bitmask(tag: str, value: bytes) -> list[dict]:
        """
        Decode a bitmask tag value.

        Args:
            tag: Tag identifier in uppercase hex
            value: Raw value bytes

        Returns:
            List of {byte, bit, mask, name, set} dicts
        """
        # Try to decode using the dictionary metadata bytes definitions first
        metadata = Dictionary.lookup_by_tag(tag)
        if metadata:
            bytes_defs = metadata.get("bytes")
            if bytes_defs:
                results = []
                for byte_def in bytes_defs:
                    byte_index = byte_def.get("index", 1) - 1  # 1-based to 0-based
                    if byte_index >= len(value):
                        continue
                    
                    byte_value = value[byte_index]
                    
                    for bit_def in byte_def.get("bits", []):
                        if "multi_bit" in bit_def and bit_def["multi_bit"]:
                            results.append({
                                "byte": byte_index,
                                "bit": 0,
                                "mask": 0x00,
                                "name": bit_def.get("label", ""),
                                "set": byte_value != 0,
                            })
                        else:
                            bit_raw = bit_def.get("bit", 0)
                            # Handle string values like "2-1" (multi-bit range) or "value"
                            try:
                                bit = int(bit_raw)
                            except (ValueError, TypeError):
                                bit = 0
                            # For multi-bit ranges like "2-1", treat as multi-bit field
                            if isinstance(bit_raw, str) and "-" in bit_raw:
                                # Multi-bit field: show as set if any of the bits are set
                                try:
                                    parts = bit_raw.split("-")
                                    high = int(parts[0])
                                    low = int(parts[1])
                                    multi_mask = 0
                                    for b in range(low, high + 1):
                                        multi_mask |= (1 << (b - 1))
                                    mask = multi_mask
                                    bit = high  # Use highest bit for display
                                except (ValueError, IndexError):
                                    mask = 0
                            else:
                                mask = 1 << (bit - 1) if bit > 0 else 0
                            results.append({
                                "byte": byte_index,
                                "bit": bit,
                                "mask": mask,
                                "name": bit_def.get("label", ""),
                                "set": bool(byte_value & mask),
                            })
                if results:
                    return results

        # Fallback to hardcoded definitions if no dictionary definitions exist
        definitions = _BITMASK_DEFINITIONS.get(tag)
        if not definitions:
            return []

        results: list[dict] = []

        for byte_index, byte_bits in enumerate(definitions):
            byte_value = value[byte_index] if byte_index < len(value) else 0

            for bit_def in byte_bits:
                mask = bit_def["mask"]
                # Calculate bit number from mask (e.g. 0x80 -> bit 8)
                bit = mask.bit_length() if mask > 0 else 0
                results.append({
                    "byte": byte_index,
                    "bit": bit,
                    "mask": mask,
                    "name": bit_def["name"],
                    "set": bool(byte_value & mask),
                })

        return results

    @staticmethod
    def get_set_bits(tag: str, value: bytes) -> list[dict]:
        """Get only set bits from a bitmask."""
        return [
            b for b in BitmaskDecoder.decode_bitmask(tag, value) if b["set"]
        ]

    @staticmethod
    def get_definition(tag: str) -> list | None:
        """Get bitmask definition for a tag."""
        return _BITMASK_DEFINITIONS.get(tag)