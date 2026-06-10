"""Tests for ValueDecoder and BitmaskDecoder."""

from emv_tlv.decoders.value_decoder import ValueDecoder
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder


class TestValueDecoder:
    def test_pan_f_padding(self):
        """Decode PAN with F padding."""
        value = bytes([0x42, 0x76, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0xFF, 0xFF])
        result = ValueDecoder.decode_value("5A", value)
        assert result == "4276 1234 5678 9012"

    def test_pan_16_digit(self):
        """Decode 16-digit PAN."""
        value = bytes([0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0x34, 0x56])
        result = ValueDecoder.decode_value("5A", value)
        assert result == "1234 5678 9012 3456"

    def test_pan_15_digit_amex(self):
        """Decode 15-digit Amex PAN."""
        value = bytes([0x37, 0x82, 0x82, 0x24, 0x63, 0x10, 0x00, 0x5F])
        result = ValueDecoder.decode_value("5A", value)
        assert result == "3782 8224 6310 005"

    def test_expiry_date(self):
        """Decode expiry date."""
        value = bytes([0x25, 0x12])
        result = ValueDecoder.decode_value("5F24", value)
        assert result == "2025-12"

    def test_expiry_year_2000(self):
        """Decode expiry date in year 2000."""
        value = bytes([0x00, 0x01])
        result = ValueDecoder.decode_value("5F24", value)
        assert result == "2000-01"

    def test_expiry_year_2099(self):
        """Decode expiry date in year 2099."""
        value = bytes([0x99, 0x12])
        result = ValueDecoder.decode_value("5F24", value)
        assert result == "2099-12"

    def test_cardholder_name(self):
        """Decode ASCII cardholder name."""
        value = b"JOHN DOE"
        result = ValueDecoder.decode_value("5F20", value)
        assert result == "JOHN DOE"

    def test_cardholder_name_special(self):
        """Decode name with special characters."""
        value = "MÜLLER/SUCCESS".encode("utf-8")
        result = ValueDecoder.decode_value("5F20", value)
        assert result == "MÜLLER/SUCCESS"

    def test_amount(self):
        """Decode BCD amount."""
        value = bytes([0x00, 0x00, 0x00, 0x01, 0x00, 0x00])
        result = ValueDecoder.decode_value("9F02", value)
        assert result == "100.00"

    def test_amount_with_cents(self):
        """Decode amount with cents."""
        value = bytes([0x00, 0x00, 0x00, 0x01, 0x23, 0x45])
        result = ValueDecoder.decode_value("9F02", value)
        assert result == "123.45"

    def test_amount_zero(self):
        """Decode zero amount."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = ValueDecoder.decode_value("9F02", value)
        assert result == "0.00"

    def test_amount_large(self):
        """Decode large amount."""
        value = bytes([0x99, 0x99, 0x99, 0x99, 0x99, 0x99])
        result = ValueDecoder.decode_value("9F02", value)
        assert result == "9999999999.99"

    def test_amount_other_9f03(self):
        """Decode 9F03 amount other."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x50, 0x00])
        result = ValueDecoder.decode_value("9F03", value)
        assert result == "50.00"

    def test_date(self):
        """Decode transaction date."""
        value = bytes([0x21, 0x03, 0x15])
        result = ValueDecoder.decode_value("9A", value)
        assert result == "2021-03-15"

    def test_date_year_2000(self):
        """Decode date in year 2000."""
        value = bytes([0x00, 0x01, 0x01])
        result = ValueDecoder.decode_value("9A", value)
        assert result == "2000-01-01"

    def test_date_year_2099(self):
        """Decode date in 2099."""
        value = bytes([0x99, 0x12, 0x31])
        result = ValueDecoder.decode_value("9A", value)
        assert result == "2099-12-31"

    def test_cryptogram_aac(self):
        """Decode AAC (00)."""
        value = bytes([0x00])
        result = ValueDecoder.decode_value("9F27", value)
        assert result == "AAC (Transaction Declined)"

    def test_cryptogram_tc(self):
        """Decode TC (01)."""
        value = bytes([0x01])
        result = ValueDecoder.decode_value("9F27", value)
        assert result == "TC (Transaction Approved)"

    def test_cryptogram_arqc(self):
        """Decode ARQC (10)."""
        value = bytes([0x10])
        result = ValueDecoder.decode_value("9F27", value)
        assert result == "ARQC (Authorization Request)"

    def test_cryptogram_unknown(self):
        """Decode unknown cryptogram value."""
        value = bytes([0xFF])
        result = ValueDecoder.decode_value("9F27", value)
        assert result == "Unknown (FF)"

    def test_cvm_pin_verified(self):
        """Decode CVM - PIN verified."""
        value = bytes([0x41, 0x00, 0x00])
        result = ValueDecoder.decode_value("9F34", value)
        assert "PIN" in result
        assert "successful" in result

    def test_cvm_signature(self):
        """Decode CVM - Signature."""
        value = bytes([0x1E, 0x00, 0x00])
        result = ValueDecoder.decode_value("9F34", value)
        assert "Signature" in result

    def test_cvm_no_cvm(self):
        """Decode CVM - No CVM."""
        value = bytes([0x1F, 0x00, 0x00])
        result = ValueDecoder.decode_value("9F34", value)
        assert "No CVM" in result

    def test_country_code_austria(self):
        """Decode country code 040 (Austria)."""
        value = bytes([0x04, 0x00])
        result = ValueDecoder.decode_value("9F1A", value)
        assert result == "Austria (040)"

    def test_country_code_germany(self):
        """Decode country code 280 (Germany)."""
        value = bytes([0x28, 0x00])
        result = ValueDecoder.decode_value("9F1A", value)
        assert result == "Germany (280)"

    def test_country_code_usa(self):
        """Decode country code 840 (USA)."""
        value = bytes([0x84, 0x00])
        result = ValueDecoder.decode_value("9F1A", value)
        assert result == "United States (840)"

    def test_issuer_country_code(self):
        """Decode issuer country code 5F28."""
        value = bytes([0x28, 0x00])
        result = ValueDecoder.decode_value("5F28", value)
        assert result == "Germany (280)"

    def test_currency_eur(self):
        """Decode currency 978 (EUR)."""
        value = bytes([0x97, 0x80])
        result = ValueDecoder.decode_value("49", value)
        assert result == "EUR (978)"

    def test_currency_usd(self):
        """Decode currency 840 (USD)."""
        value = bytes([0x84, 0x00])
        result = ValueDecoder.decode_value("49", value)
        assert result == "USD (840)"

    def test_currency_gbp(self):
        """Decode currency 826 (GBP)."""
        value = bytes([0x82, 0x60])
        result = ValueDecoder.decode_value("49", value)
        assert result == "GBP (826)"

    def test_unknown_tag(self):
        """Unknown tags return uppercase hex."""
        value = bytes([0xAB, 0xCD, 0xEF])
        result = ValueDecoder.decode_value("FFFF", value)
        assert result == "ABCDEF"

    def test_empty_value(self):
        """Empty value returns empty string."""
        result = ValueDecoder.decode_value("5A", b"")
        assert result == ""


class TestBitmaskDecoder:
    def test_tvr_all_bits_set(self):
        """Decode TVR with all bits set."""
        value = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        result = BitmaskDecoder.decode_bitmask("95", value)
        assert len(result) > 0
        assert all(b["set"] for b in result)

    def test_tvr_no_bits_set(self):
        """Decode TVR with no bits set."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("95", value)
        assert len(result) > 0
        assert all(b["set"] is False for b in result)

    def test_tvr_byte1_bit8(self):
        """Decode TVR byte 1 bit 8."""
        value = bytes([0x80, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("95", value)
        bit = next(b for b in result if b["byte"] == 0 and b["mask"] == 0x80)
        assert bit["set"] is True
        assert "Offline data authentication" in bit["name"]

    def test_tvr_byte2_bit8(self):
        """Decode TVR byte 2 bit 8."""
        value = bytes([0x00, 0x80, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("95", value)
        bit = next(b for b in result if b["byte"] == 1 and b["mask"] == 0x80)
        assert bit["set"] is True

    def test_tvr_byte5_bit8(self):
        """Decode TVR byte 5 bit 8."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x80])
        result = BitmaskDecoder.decode_bitmask("95", value)
        bit = next(b for b in result if b["byte"] == 4 and b["mask"] == 0x80)
        assert bit["set"] is True
        assert "Relay resistance" in bit["name"]

    def test_tvr_return_structure(self):
        """Verify TVR return structure."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("95", value)
        for bit in result:
            assert "byte" in bit
            assert "mask" in bit
            assert "name" in bit
            assert "set" in bit
            assert isinstance(bit["byte"], int)
            assert isinstance(bit["mask"], int)
            assert isinstance(bit["name"], str)
            assert isinstance(bit["set"], bool)

    def test_terminal_capabilities(self):
        """Decode Terminal Capabilities."""
        value = bytes([0xE0, 0xE8, 0xC8])
        result = BitmaskDecoder.decode_bitmask("9F33", value)
        assert len(result) > 0
        set_bits = [b for b in result if b["set"]]
        assert len(set_bits) > 0

    def test_terminal_capabilities_manual_key(self):
        """Decode Manual key entry capability."""
        value = bytes([0x40, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("9F33", value)
        bit = next(b for b in result if b["byte"] == 0 and b["mask"] == 0x40)
        assert bit["set"] is True

    def test_additional_terminal_capabilities(self):
        """Decode Additional Terminal Capabilities."""
        value = bytes([0xF0, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("9F40", value)
        assert len(result) > 0

    def test_tac_default(self):
        """Decode TAC Default."""
        value = bytes([0xF8, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("DF11", value)
        assert len(result) > 0
        bit = next(b for b in result if b["byte"] == 0 and b["mask"] == 0x80)
        assert bit["set"] is True

    def test_tac_denial(self):
        """Decode TAC Denial."""
        value = bytes([0x00, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.decode_bitmask("DF12", value)
        assert len(result) > 0
        assert all(b["set"] is False for b in result)

    def test_tac_online(self):
        """Decode TAC Online."""
        value = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0xFF])
        result = BitmaskDecoder.decode_bitmask("DF13", value)
        assert len(result) > 0
        assert all(b["set"] for b in result)

    def test_unknown_tag(self):
        """Unknown tag returns empty list."""
        value = bytes([0xFF, 0xFF])
        result = BitmaskDecoder.decode_bitmask("9999", value)
        assert result == []

    def test_get_set_bits(self):
        """Get only set bits."""
        value = bytes([0x80, 0x00, 0x00, 0x00, 0x00])
        result = BitmaskDecoder.get_set_bits("95", value)
        assert len(result) == 1
        assert result[0]["mask"] == 0x80

    def test_get_definition(self):
        """Get bitmask definition."""
        defs = BitmaskDecoder.get_definition("95")
        assert defs is not None
        assert len(defs) == 5
        assert BitmaskDecoder.get_definition("9999") is None