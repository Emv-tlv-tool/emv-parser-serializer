"""Tests for ConfigAdapter."""

from emv_tlv.adapters.config_adapter import ConfigAdapter
from emv_tlv.core.tlv_node import TLVNode
from emv_tlv.core.tlv_parser import TLVParser


class TestConfigAdapter:
    def test_parse_e0(self):
        """Parse E0 terminal configuration template."""
        data = bytes([
            0xE0, 0x09,
            0x9F, 0x1A, 0x02, 0x02, 0x80,
            0x9F, 0x35, 0x01, 0x22,
        ])
        tree = ConfigAdapter.parse(data)
        assert len(tree) == 1
        assert tree[0].tag == "E0"
        assert tree[0].is_constructed is True

    def test_parse_e1(self):
        """Parse E1 CA keys template."""
        data = bytes([
            0xE1, 0x0C,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x02, 0x01, 0x01,
        ])
        tree = ConfigAdapter.parse(data)
        assert len(tree) == 1
        assert tree[0].tag == "E1"
        assert len(tree[0].children) == 2

    def test_parse_e2(self):
        """Parse E2 application configuration template."""
        data = bytes([
            0xE2, 0x13,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,
            0xDF, 0x11, 0x02, 0xF8, 0x00,
        ])
        tree = ConfigAdapter.parse(data)
        assert len(tree) == 1
        assert tree[0].tag == "E2"
        assert len(tree[0].children) == 3

    def test_parse_multiple_templates(self):
        """Parse multiple templates in same blob."""
        data = bytes([
            0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80,
            0xE1, 0x04, 0xDF, 0x02, 0x01, 0x01,
            0xE2, 0x04, 0x4F, 0x02, 0xA0, 0x00,
        ])
        tree = ConfigAdapter.parse(data)
        assert len(tree) == 3
        assert tree[0].tag == "E0"
        assert tree[1].tag == "E1"
        assert tree[2].tag == "E2"

    def test_get_application_configs_single(self):
        """Extract single application config."""
        data = bytes([
            0xE2, 0x16,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,
            0xDF, 0x11, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00,
        ])
        tree = TLVParser.parse(data)
        configs = ConfigAdapter.get_application_configs(tree)
        assert len(configs) == 1
        assert configs[0]["aid"] == "A000000004"
        assert configs[0]["label"] == "VISA"

    def test_get_application_configs_multiple(self):
        """Extract multiple application configs."""
        data = bytes([
            0xE2, 0x11,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x02, 0x56, 0x49,
            0xDF, 0x11, 0x02, 0xF8, 0x00,
            0xE2, 0x11,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
            0xDF, 0x04, 0x02, 0x4D, 0x43,
            0xDF, 0x11, 0x02, 0xF8, 0x00,
        ])
        tree = TLVParser.parse(data)
        configs = ConfigAdapter.get_application_configs(tree)
        assert len(configs) == 2
        assert configs[0]["aid"] == "A000000004"
        assert configs[1]["aid"] == "A000000005"

    def test_get_application_configs_all_fields(self):
        """Extract all application config fields."""
        data = bytes([
            0xE2, 0x33,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,
            0xDF, 0x11, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x12, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x13, 0x05, 0xDC, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x05, 0x04, 0x00, 0x10, 0x00, 0x00,
            0x9F, 0x33, 0x03, 0xE0, 0xE8, 0xC8,
        ])
        tree = TLVParser.parse(data)
        configs = ConfigAdapter.get_application_configs(tree)
        assert len(configs) == 1
        assert configs[0]["aid"] == "A000000004"
        assert configs[0]["label"] == "VISA"
        assert configs[0]["tac_default"] == "F800000000"
        assert configs[0]["tac_denial"] == "0000000000"
        assert configs[0]["tac_online"] == "DC00000000"
        assert "floor_limit" in configs[0]
        assert configs[0]["terminal_capabilities"] == "E0E8C8"

    def test_get_application_configs_missing_fields(self):
        """Handle missing optional fields."""
        data = bytes([
            0xE2, 0x07,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
        ])
        tree = TLVParser.parse(data)
        configs = ConfigAdapter.get_application_configs(tree)
        assert len(configs) == 1
        assert configs[0]["aid"] == "A000000004"
        assert "label" not in configs[0]

    def test_get_ca_keys_single(self):
        """Extract single CA key."""
        e1 = TLVNode("E1", b"", True)
        e1.add_child(TLVNode("DF01", bytes([0xA0, 0x00, 0x00, 0x00, 0x04]), False))
        e1.add_child(TLVNode("DF02", bytes([0x08]), False))
        e1.add_child(TLVNode("E6", bytes([0x01, 0x02, 0x03, 0x04, 0x05]), False))
        e1.add_child(TLVNode("E7", bytes([0x03]), False))
        tree = [e1]
        keys = ConfigAdapter.get_ca_keys(tree)
        assert len(keys) == 1
        assert keys[0]["rid"] == "A000000004"
        assert keys[0]["key_index"] == 8
        assert keys[0]["modulus"] == "0102030405"
        assert keys[0]["exponent"] == "03"

    def test_get_ca_keys_multiple(self):
        """Extract multiple CA keys."""
        data = bytes([
            0xE1, 0x0C,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x02, 0x01, 0x08,
            0xE1, 0x0C,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
            0xDF, 0x02, 0x01, 0x07,
        ])
        tree = TLVParser.parse(data)
        keys = ConfigAdapter.get_ca_keys(tree)
        assert len(keys) == 2
        assert keys[0]["rid"] == "A000000004"
        assert keys[1]["rid"] == "A000000005"

    def test_get_ca_keys_with_checksum(self):
        """Extract CA key with checksum."""
        e1 = TLVNode("E1", b"", True)
        e1.add_child(TLVNode("DF01", bytes([0xA0, 0x00, 0x00, 0x00, 0x04]), False))
        e1.add_child(TLVNode("DF02", bytes([0x08]), False))
        e1.add_child(TLVNode("E6", bytes([0xAB]), False))
        e1.add_child(TLVNode("E7", bytes([0x03]), False))
        e1.add_child(TLVNode("DF03", bytes([0xCD]), False))
        tree = [e1]
        keys = ConfigAdapter.get_ca_keys(tree)
        assert keys[0]["checksum"] == "CD"

    def test_get_ca_keys_missing_fields(self):
        """Handle missing CA key fields."""
        data = bytes([
            0xE1, 0x08,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
        ])
        tree = TLVParser.parse(data)
        keys = ConfigAdapter.get_ca_keys(tree)
        assert len(keys) == 1
        assert keys[0]["rid"] == "A000000004"
        assert "key_index" not in keys[0]

    def test_find_template(self):
        """Find E0 template."""
        data = bytes([
            0xE1, 0x04, 0xDF, 0x02, 0x01, 0x01,
            0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80,
            0xE2, 0x04, 0x4F, 0x02, 0xA0, 0x00,
        ])
        tree = TLVParser.parse(data)
        e0 = ConfigAdapter.find_template(tree, "E0")
        assert e0 is not None
        assert e0.tag == "E0"

    def test_real_world_scenario(self):
        """Parse complete Poseidon configuration."""
        data = bytes([
            0xE0, 0x09,
            0x9F, 0x1A, 0x02, 0x02, 0x80,
            0x9F, 0x35, 0x01, 0x22,
            0xE1, 0x0C,
            0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x02, 0x01, 0x08,
            0xE2, 0x13,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
            0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,
            0xDF, 0x11, 0x02, 0xF8, 0x00,
            0xE2, 0x13,
            0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
            0xDF, 0x04, 0x04, 0x4D, 0x41, 0x53, 0x54,
            0xDF, 0x11, 0x02, 0xF8, 0x00,
        ])
        tree = ConfigAdapter.parse(data)
        app_configs = ConfigAdapter.get_application_configs(tree)
        ca_keys = ConfigAdapter.get_ca_keys(tree)

        assert len(tree) == 4
        assert len(app_configs) == 2
        assert len(ca_keys) == 1

        assert app_configs[0]["aid"] == "A000000004"
        assert app_configs[0]["label"] == "VISA"
        assert app_configs[1]["aid"] == "A000000005"
        assert app_configs[1]["label"] == "MAST"