"""Tests for TLVSerializer."""

import pytest
from emv_tlv.core.tlv_node import TLVNode
from emv_tlv.core.tlv_serializer import TLVSerializer
from emv_tlv.core.tlv_parser import TLVParser


class TestSerializerPrimitive:
    def test_serialize_primitive(self):
        """Serialize a primitive tag."""
        node = TLVNode("9A", bytes([0x21, 0x03, 0x15]), False)
        result = TLVSerializer.serialize(node)
        assert result == "9A03210315"

    def test_serialize_zero_length(self):
        """Serialize primitive with zero length."""
        node = TLVNode("9A", b"", False)
        result = TLVSerializer.serialize(node)
        assert result == "9A00"

    def test_serialize_2_byte_tag(self):
        """Serialize 2-byte primitive tag."""
        node = TLVNode("9F02", bytes([0x00, 0x10, 0x00, 0x00]), False)
        result = TLVSerializer.serialize(node)
        assert result == "9F020400100000"

    def test_serialize_short_form_length(self):
        """Use short-form length for values < 128."""
        value = bytes([0xAB]) * 50
        node = TLVNode("9A", value, False)
        result = TLVSerializer.serialize(node)
        # Length byte should be 0x32 (50)
        assert result[2:4] == "32"

    def test_serialize_0x81_length(self):
        """Use 0x81 prefix for length 128."""
        value = bytes([0xCD]) * 128
        node = TLVNode("9A", value, False)
        result = TLVSerializer.serialize(node)
        assert result[:6] == "9A8180"

    def test_serialize_0x82_length(self):
        """Use 0x82 prefix for length 256."""
        value = bytes([0x12]) * 256
        node = TLVNode("9A", value, False)
        result = TLVSerializer.serialize(node)
        assert result[:8] == "9A820100"

    def test_serialize_zka_tag(self):
        """Serialize ZKA DFxx tags."""
        node = TLVNode("DF11", bytes([0xF8, 0x00, 0x00, 0x00, 0x00]), False)
        result = TLVSerializer.serialize(node)
        assert result == "DF1105F800000000"

    def test_uppercase_output(self):
        """Output should be uppercase hex."""
        node = TLVNode("9A", bytes([0xab, 0xcd, 0xef]), False)
        result = TLVSerializer.serialize(node)
        assert result == "9A03ABCDEF"
        assert result == result.upper()

    def test_length_boundaries(self):
        """Length encoding boundaries."""
        # 127
        n127 = TLVNode("9A", bytes(127), False)
        assert TLVSerializer.serialize(n127)[:4] == "9A7F"
        # 128
        n128 = TLVNode("9A", bytes(128), False)
        assert TLVSerializer.serialize(n128)[:6] == "9A8180"
        # 255
        n255 = TLVNode("9A", bytes(255), False)
        assert TLVSerializer.serialize(n255)[:6] == "9A81FF"
        # 256
        n256 = TLVNode("9A", bytes(256), False)
        assert TLVSerializer.serialize(n256)[:8] == "9A820100"


class TestSerializerConstructed:
    def test_serialize_constructed(self):
        """Serialize constructed tag with children."""
        parent = TLVNode("6F", b"", True)
        parent.add_child(TLVNode("84", bytes([0xA0, 0x00]), False))
        parent.add_child(TLVNode("A5", bytes([0x50, 0x00]), False))
        result = TLVSerializer.serialize(parent)
        assert result == "6F088402A000A5025000"

    def test_serialize_3_level_nested(self):
        """Serialize 3-level nested constructed tags."""
        level3 = TLVNode("50", bytes([0xAB, 0xCD]), False)
        level2 = TLVNode("BF0C", b"", True)
        level2.add_child(level3)
        level1 = TLVNode("A5", b"", True)
        level1.add_child(level2)
        root = TLVNode("6F", b"", True)
        root.add_child(level1)
        result = TLVSerializer.serialize(root)
        assert result == "6F09A507BF0C045002ABCD"

    def test_serialize_2_byte_constructed(self):
        """Serialize 2-byte constructed tag."""
        parent = TLVNode("BF0C", b"", True)
        parent.add_child(TLVNode("50", bytes([0x54, 0x45, 0x53, 0x54]), False))
        result = TLVSerializer.serialize(parent)
        assert result == "BF0C06500454455354"

    def test_serialize_empty_constructed(self):
        """Serialize empty constructed tag."""
        node = TLVNode("6F", b"", True)
        result = TLVSerializer.serialize(node)
        assert result == "6F00"

    def test_serialize_multiple(self):
        """Serialize multiple top-level nodes."""
        node1 = TLVNode("9A", bytes([0x21, 0x03, 0x15]), False)
        node2 = TLVNode("82", bytes([0x39, 0x00]), False)
        result = TLVSerializer.serialize_multiple([node1, node2])
        assert result == "9A0321031582023900"


class TestRoundTrip:
    def test_primitive_roundtrip(self):
        """Parse -> Serialize -> verify identical."""
        original = "9A03210315"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_constructed_roundtrip(self):
        """Roundtrip for constructed tag."""
        original = "6F088402A000A5025000"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_3_level_roundtrip(self):
        """Roundtrip for 3-level nested structure."""
        original = "6F09A507BF0C045002ABCD"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_2_byte_tag_roundtrip(self):
        """Roundtrip for 2-byte tag."""
        original = "9F0206000010000000"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_zka_tag_roundtrip(self):
        """Roundtrip for ZKA tag."""
        original = "DF1105F800000000"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_long_length_0x81_roundtrip(self):
        """Roundtrip with 0x81 length."""
        value = bytes([0xAB]) * 150
        data = bytes([0x9A, 0x81, 150]) + value
        original = data.hex().upper()
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_long_length_0x82_roundtrip(self):
        """Roundtrip with 0x82 length."""
        value = bytes([0xCD]) * 300
        data = bytes([0x9A, 0x82, 0x01, 0x2C]) + value
        original = data.hex().upper()
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_complex_real_world(self):
        """Roundtrip for complex real-world EMV data."""
        original = "6F1B8407A0000000041010A510500B5649534120435245444954870101"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original
        assert len(nodes[0].children) == 2
        assert nodes[0].children[0].tag == "84"
        assert nodes[0].children[1].tag == "A5"

    def test_multiple_nodes_roundtrip(self):
        """Roundtrip multiple top-level nodes."""
        original = "9A03210315820239009F0206000010000000"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize_multiple(nodes)
        assert serialized == original

    def test_empty_value_roundtrip(self):
        """Roundtrip for empty value."""
        original = "9A00"
        data = bytes.fromhex(original)
        nodes = TLVParser.parse(data)
        serialized = TLVSerializer.serialize(nodes[0])
        assert serialized == original

    def test_serialize_after_dict_modification(self):
        """Test serializing after modifying node via dictionary keys."""
        node = TLVNode("9A", bytes([0x21, 0x03, 0x15]), False)
        node["tag"] = "9B"
        node["value"] = "1122"
        result = TLVSerializer.serialize(node)
        assert result == "9B021122"

    def test_serialize_constructed_dict_modification(self):
        """Test serializing constructed node modified via dict keys."""
        parent = TLVNode("6F", b"", True)
        child = TLVNode("84", bytes([0xA0, 0x00]), False)
        parent["children"] = [child]
        result = TLVSerializer.serialize(parent)
        assert result == "6F048402A000"