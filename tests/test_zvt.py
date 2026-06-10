"""Tests for ZVTAdapter."""

from emv_tlv.adapters.zvt_adapter import ZVTAdapter
from emv_tlv.core.tlv_parser import TLVParser


class TestZVTAdapter:
    def test_parse_message_header(self):
        """Parse ZVT message header."""
        data = bytes([
            0x06, 0x01,
            0x05,
            0x9A, 0x03, 0x21, 0x03, 0x15,
        ])
        msg = ZVTAdapter.parse(data)
        assert msg["ctrl"] == "0601"
        assert msg["ctrl_name"] == "Authorisation"
        assert msg["length"] == 5

    def test_parse_extended_length(self):
        """Parse extended length with 0xFF prefix."""
        payload = bytes(256)
        data = bytes([0x06, 0x01, 0xFF, 0x01, 0x00]) + payload
        msg = ZVTAdapter.parse(data)
        assert msg["ctrl"] == "0601"
        assert msg["length"] == 256

    def test_parse_single_bmp_field(self):
        """Parse single BMP field."""
        data = bytes([
            0x06, 0x01, 0x05,
            0x9A, 0x03, 0x21, 0x03, 0x15,
        ])
        msg = ZVTAdapter.parse(data)
        assert len(msg["bmp_fields"]) == 1
        assert msg["bmp_fields"][0]["tag"] == "9A"
        assert msg["bmp_fields"][0]["length"] == 3

    def test_parse_multiple_bmp_fields(self):
        """Parse multiple BMP fields."""
        data = bytes([
            0x06, 0x01, 0x0B,
            0x9A, 0x03, 0x21, 0x03, 0x15,
            0x82, 0x02, 0x39, 0x00,
            0x9F, 0x02, 0x06,
        ])
        msg = ZVTAdapter.parse(data)
        assert len(msg["bmp_fields"]) == 3

    def test_extract_emv_from_bmp_9a(self):
        """Extract EMV TLV from BMP tag 0x9A."""
        emv = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])
        data = bytes([0x06, 0x01, len(emv) + 2, 0x9A, len(emv)]) + emv
        msg = ZVTAdapter.parse(data)
        tlv = ZVTAdapter.extract_emv_tlv(msg)
        assert len(tlv) == 1
        assert tlv[0].tag == "9A"

    def test_extract_emv_from_bmp_aa(self):
        """Extract EMV TLV from BMP tag 0xAA."""
        emv = bytes([0x82, 0x02, 0x39, 0x00])
        data = bytes([0x06, 0x01, len(emv) + 2, 0xAA, len(emv)]) + emv
        msg = ZVTAdapter.parse(data)
        tlv = ZVTAdapter.extract_emv_tlv(msg)
        assert len(tlv) == 1
        assert tlv[0].tag == "82"

    def test_extract_emv_from_bmp_3b(self):
        """Extract EMV TLV from BMP tag 0x3B."""
        emv = bytes([0x6F, 0x08, 0x84, 0x02, 0xA0, 0x00, 0xA5, 0x02, 0x50, 0x00])
        data = bytes([0x06, 0x01, len(emv) + 2, 0x3B, len(emv)]) + emv
        msg = ZVTAdapter.parse(data)
        tlv = ZVTAdapter.extract_emv_tlv(msg)
        assert len(tlv) == 1
        assert tlv[0].tag == "6F"
        assert len(tlv[0].children) == 2

    def test_extract_multiple_emv(self):
        """Extract EMV TLV from multiple BMP tags."""
        emv1 = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])
        emv2 = bytes([0x82, 0x02, 0x39, 0x00])
        data = bytes([
            0x06, 0x01,
            len(emv1) + 2 + len(emv2) + 2,
            0x9A, len(emv1),
        ]) + emv1 + bytes([0xAA, len(emv2)]) + emv2
        msg = ZVTAdapter.parse(data)
        tlv = ZVTAdapter.extract_emv_tlv(msg)
        assert len(tlv) == 2

    def test_ctrl_0601(self):
        """CTRL 0601 = Authorisation."""
        msg = ZVTAdapter.parse(bytes([0x06, 0x01, 0x00]))
        assert msg["ctrl_name"] == "Authorisation"

    def test_ctrl_060f(self):
        """CTRL 060F = Authorisation Response."""
        msg = ZVTAdapter.parse(bytes([0x06, 0x0F, 0x00]))
        assert msg["ctrl_name"] == "Authorisation Response"

    def test_ctrl_061e(self):
        """CTRL 061E = End of Day."""
        msg = ZVTAdapter.parse(bytes([0x06, 0x1E, 0x00]))
        assert msg["ctrl_name"] == "End of Day"

    def test_ctrl_060b(self):
        """CTRL 060B = Status Enquiry."""
        msg = ZVTAdapter.parse(bytes([0x06, 0x0B, 0x00]))
        assert msg["ctrl_name"] == "Status Enquiry"

    def test_ctrl_068a(self):
        """CTRL 068A = Print Line."""
        msg = ZVTAdapter.parse(bytes([0x06, 0x8A, 0x00]))
        assert msg["ctrl_name"] == "Print Line"

    def test_ctrl_8000(self):
        """CTRL 8000 = ACK."""
        msg = ZVTAdapter.parse(bytes([0x80, 0x00, 0x00]))
        assert msg["ctrl_name"] == "ACK"

    def test_ctrl_8400(self):
        """CTRL 8400 = Abort."""
        msg = ZVTAdapter.parse(bytes([0x84, 0x00, 0x00]))
        assert msg["ctrl_name"] == "Abort"

    def test_unknown_ctrl(self):
        """Unknown CTRL code."""
        msg = ZVTAdapter.parse(bytes([0xFF, 0xFF, 0x00]))
        assert msg["ctrl"] == "FFFF"
        assert msg["ctrl_name"] == "Unknown"

    def test_serialize_roundtrip(self):
        """Roundtrip parse -> serialize."""
        original = bytes([0x06, 0x01, 0x05, 0x9A, 0x03, 0x21, 0x03, 0x15])
        msg = ZVTAdapter.parse(original)
        serialized = ZVTAdapter.serialize(msg)
        assert serialized == original

    def test_get_ctrl_name(self):
        """Get CTRL name."""
        assert ZVTAdapter.get_ctrl_name("0601") == "Authorisation"
        assert ZVTAdapter.get_ctrl_name("FFFF") == "Unknown"

    def test_is_emv_bmp_tag(self):
        """Check EMV BMP tags."""
        assert ZVTAdapter.is_emv_bmp_tag("9A") is True
        assert ZVTAdapter.is_emv_bmp_tag("AA") is True
        assert ZVTAdapter.is_emv_bmp_tag("3B") is True
        assert ZVTAdapter.is_emv_bmp_tag("82") is False