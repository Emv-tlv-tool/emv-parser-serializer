"""Tests for the public API."""

import pytest
from emv_tlv import (
    parse, serialize, find_tag, find_all_tags,
    decode_node, to_json
)


class TestParseRawTLV:
    def test_parse_raw_tlv_data(self):
        """Parse raw TLV from bytes."""
        data = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])
        result = parse(data, "raw")
        assert len(result) == 1
        assert result[0]["tag"] == "9A"
        assert result[0]["name"] == "Transaction Date"

    def test_parse_hex_string(self):
        """Parse hex string input."""
        result = parse("9A03210315", "raw")
        assert len(result) == 1
        assert result[0]["tag"] == "9A"

    def test_parse_with_decoded_values(self):
        """Parse with decoded values."""
        result = parse("9A03210315", "raw")
        assert result[0]["decoded"] == "2021-03-15"

    def test_parse_constructed_tag(self):
        """Parse constructed tag with children."""
        result = parse("6F088402A000A5025000", "raw")
        assert result[0]["tag"] == "6F"
        assert result[0]["name"] == "FCI Template"
        assert len(result[0]["children"]) == 2
        assert result[0]["children"][0]["name"] == "DF Name"

    def test_parse_empty_input(self):
        """Parse empty input."""
        result = parse("", "raw")
        assert result == []


class TestParseZVT:
    def test_parse_zvt_message(self):
        """Parse ZVT message."""
        data = bytes([
            0x06, 0x01, 0x07,
            0x9A, 0x05, 0x9A, 0x03, 0x21, 0x03, 0x15,
        ])
        result = parse(data, "zvt")
        assert result["ctrl"] == "0601"
        assert result["ctrl_name"] == "Authorisation"
        assert len(result["tlv"]) == 1
        assert result["tlv"][0]["tag"] == "9A"

    def test_parse_zvt_with_emv_extraction(self):
        """Parse ZVT with EMV extraction."""
        emv = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])
        data = bytes([0x06, 0x01, len(emv) + 2, 0x9A, len(emv)]) + emv
        result = parse(data, "zvt")
        assert len(result["tlv"]) == 1
        assert result["tlv"][0]["decoded"] == "2021-03-15"


class TestParseConfig:
    def test_parse_config_blob(self):
        """Parse Poseidon config blob."""
        data = bytes([
            0xE0, 0x09,
            0x9F, 0x1A, 0x02, 0x02, 0x80,
            0x9F, 0x35, 0x01, 0x22,
        ])
        result = parse(data, "config")
        assert len(result) == 1
        assert result[0]["tag"] == "E0"
        assert result[0]["name"] == "Terminal Configuration"

    def test_get_application_configs(self):
        """Get application configs from parsed config."""
        data = bytes([
            0xE2, 0x0C,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x02, 0x56, 0x49,
        ])
        result = parse(data, "config")
        assert hasattr(result, "application_configs")
        assert len(result.application_configs) == 1
        assert result.application_configs[0]["aid"] == "A000000004"

    def test_get_ca_keys(self):
        """Get CA keys from parsed config."""
        data = bytes([
            0xE1, 0x08,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
        ])
        result = parse(data, "config")
        assert hasattr(result, "ca_keys")
        assert len(result.ca_keys) == 1
        assert result.ca_keys[0]["rid"] == "A000000004"


class TestSerialize:
    def test_serialize_tlv_nodes(self):
        """Serialize TLV nodes back to hex."""
        data = "9A03210315"
        parsed = parse(data, "raw")
        serialized = serialize(parsed)
        assert serialized == data.upper()

    def test_serialize_constructed(self):
        """Serialize constructed nodes."""
        data = "6F088402A000A5025000"
        parsed = parse(data, "raw")
        serialized = serialize(parsed)
        assert serialized == data.upper()

    def test_round_trip_consistency(self):
        """Round-trip parse -> serialize -> same hex."""
        inputs = [
            "9A03210315",
            "6F088402A000A5025000",
            "9F0206000010000000",
            "DF1105F800000000",
        ]
        for data in inputs:
            parsed = parse(data, "raw")
            serialized = serialize(parsed)
            assert serialized == data.upper()


class TestFindTag:
    def test_find_tag_in_tree(self):
        """Find tag in tree."""
        result = parse("6F088402A000A5025000", "raw")
        found = find_tag(result, "84")
        assert found is not None
        assert found["tag"] == "84"
        assert found["value"] == "A000"

    def test_find_nested_tag(self):
        """Find nested tag."""
        result = parse("6F09A507BF0C045002ABCD", "raw")
        found = find_tag(result, "50")
        assert found is not None
        assert found["tag"] == "50"

    def test_missing_tag_returns_none(self):
        """Returns None for missing tag."""
        result = parse("6F088402A000A5025000", "raw")
        found = find_tag(result, "9A")
        assert found is None


class TestFindAllTags:
    def test_find_all_occurrences(self):
        """Find all occurrences of a tag."""
        data = bytes([0x9A, 0x01, 0x01, 0x82, 0x01, 0x02, 0x9A, 0x01, 0x03])
        result = parse(data, "raw")
        found = find_all_tags(result, "9A")
        assert len(found) == 2
        assert found[0]["value"] == "01"
        assert found[1]["value"] == "03"

    def test_find_all_nested(self):
        """Find tags in nested structure."""
        data = bytes([
            0x6F, 0x0A,
            0x84, 0x02, 0xA0, 0x00,
            0xA5, 0x04,
            0x50, 0x02, 0x56, 0x49,
        ])
        result = parse(data, "raw")
        found = find_all_tags(result, "50")
        assert len(found) == 1

    def test_missing_tag_returns_empty(self):
        """Returns empty list for missing tag."""
        result = parse("9A03210315", "raw")
        found = find_all_tags(result, "82")
        assert found == []


class TestDecodeNode:
    def test_decode_node_value(self):
        """Decode node value."""
        result = parse("9A03210315", "raw")
        decoded = decode_node(result[0])
        assert decoded["decoded"] == "2021-03-15"

    def test_decode_pan(self):
        """Decode PAN."""
        result = parse("5A084276123456789012FFFF", "raw")
        decoded = decode_node(result[0])
        assert decoded["decoded"] == "4276 1234 5678 9012"

    def test_decode_tvr_bitmask(self):
        """Decode TVR bitmask."""
        result = parse("95050000000000", "raw")
        decoded = decode_node(result[0])
        assert "bitmask" in decoded
        assert len(decoded["bitmask"]) > 0
        assert all(b["set"] is False for b in decoded["bitmask"])


class TestToJSON:
    def test_convert_tree_to_json(self):
        """Convert tree to JSON format."""
        result = parse("6F088402A000A5025000", "raw")
        json_data = to_json(result)
        assert isinstance(json_data, list)
        assert json_data[0]["tag"] == "6F"
        assert json_data[0]["name"] == "FCI Template"
        assert "children" in json_data[0]

    def test_json_includes_decoded(self):
        """JSON includes decoded values."""
        result = parse("9A03210315", "raw")
        json_data = to_json(result)
        assert json_data[0]["decoded"] == "2021-03-15"


class TestErrorHandling:
    def test_invalid_type(self):
        """Invalid type raises error."""
        with pytest.raises(ValueError, match="Unknown type"):
            parse("test", "invalid")

    def test_malformed_tlv(self):
        """Malformed TLV raises error."""
        with pytest.raises(ValueError):
            parse("9A05AB", "raw")

    def test_empty_input(self):
        """Empty input returns empty list."""
        result = parse("", "raw")
        assert result == []


class TestIntegration:
    def test_full_workflow(self):
        """Full workflow - parse, find, serialize."""
        # Parse
        tree = parse("6F088402A000A5025000", "raw")
        # Find
        aid = find_tag(tree, "84")
        assert aid is not None
        # Serialize
        serialized = serialize(tree)
        assert serialized == "6F088402A000A5025000"
        # Re-parse
        reparsed = parse(serialized, "raw")
        assert reparsed[0]["tag"] == "6F"

    def test_real_world_zvt(self):
        """Handle real-world ZVT message."""
        tlv1 = bytes([0x82, 0x02, 0x39, 0x00, 0x50, 0x00])
        tlv2 = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])

        zvt_msg = bytes([
            0x06, 0x01,
            len(tlv1) + 2 + len(tlv2) + 2,
            0x9A, len(tlv1),
        ]) + tlv1 + bytes([0xAA, len(tlv2)]) + tlv2

        result = parse(zvt_msg, "zvt")
        assert result["ctrl"] == "0601"
        assert result["ctrl_name"] == "Authorisation"
        assert len(result["tlv"]) == 3

    def test_real_world_config(self):
        """Handle real-world config blob."""
        config = bytes([
            0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80,
            0xE2, 0x0B, 0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x01, 0x56,
        ])
        result = parse(config, "config")
        assert len(result) == 2
        assert len(result.application_configs) == 1
        assert result.application_configs[0]["label"] == "V"

    def test_dictionary_lookup(self):
        """Test dictionary lookup."""
        from emv_tlv.dictionaries import Dictionary
        assert Dictionary.lookup_by_tag("9A") is not None
        assert Dictionary.lookup_by_tag("9A")["name"] == "Transaction Date"
        assert Dictionary.lookup_by_name("PAN") is not None
        assert Dictionary.has_tag("9A") is True
        assert Dictionary.has_tag("ZZ") is False