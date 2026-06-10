"""Tests for TLVNode class."""

import pytest
from emv_tlv.core.tlv_node import TLVNode


class TestTLVNode:
    def test_create_primitive_node(self):
        """Test creating a primitive node with tag, value."""
        node = TLVNode("9A", bytes([0x21, 0x03, 0x15]), False)
        assert node.tag == "9A"
        assert node.length == 3
        assert node.value == bytes([0x21, 0x03, 0x15])
        assert node.is_constructed is False
        assert node.children == []

    def test_create_constructed_node(self):
        """Test creating a constructed node."""
        node = TLVNode("6F", b"", True)
        assert node.tag == "6F"
        assert node.is_constructed is True
        assert node.children == []

    def test_add_child_to_constructed(self):
        """Test adding child to constructed node."""
        parent = TLVNode("6F", b"", True)
        child = TLVNode("84", bytes([0x01, 0x02]), False)
        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0] is child

    def test_cannot_add_child_to_primitive(self):
        """Test that primitive nodes reject children."""
        parent = TLVNode("9A", bytes([0x21]), False)
        child = TLVNode("84", bytes([0x01]), False)
        with pytest.raises(ValueError, match="Cannot add child to primitive node"):
            parent.add_child(child)

    def test_get_children(self):
        """Test retrieving children list."""
        parent = TLVNode("6F", b"", True)
        child1 = TLVNode("84", bytes([0x01]), False)
        child2 = TLVNode("A5", b"", True)
        parent.add_child(child1)
        parent.add_child(child2)
        assert parent.get_children() == [child1, child2]

    def test_is_primitive(self):
        """Test is_primitive() returns correct value."""
        assert TLVNode("9A", bytes([0x21]), False).is_primitive() is True
        assert TLVNode("6F", b"", True).is_primitive() is False

    def test_to_dict_primitive(self):
        """Test to_dict for primitive node."""
        node = TLVNode("9A", bytes([0x21, 0x03, 0x15]), False)
        d = node.to_dict()
        assert d["tag"] == "9A"
        assert d["length"] == 3
        assert d["value"] == "210315"
        assert d["is_constructed"] is False
        assert "children" not in d

    def test_to_dict_constructed(self):
        """Test to_dict for constructed node with children."""
        parent = TLVNode("6F", b"", True)
        parent.add_child(TLVNode("84", bytes([0xA0, 0x00]), False))
        d = parent.to_dict()
        assert d["tag"] == "6F"
        assert len(d["children"]) == 1
        assert d["children"][0]["tag"] == "84"

    def test_repr(self):
        """Test string representation."""
        node = TLVNode("9A", bytes([0x21]), False)
        r = repr(node)
        assert "9A" in r
        assert "constructed=False" in r


class TestTLVParserPrimitive:
    """Tests for TLVParser with primitive tags."""

    def test_parse_single_primitive(self):
        """Parse single 1-byte tag primitive."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x9A, 0x03, 0x21, 0x03, 0x15])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].tag == "9A"
        assert nodes[0].length == 3
        assert nodes[0].value == bytes([0x21, 0x03, 0x15])
        assert nodes[0].is_constructed is False

    def test_parse_zero_length(self):
        """Parse primitive with zero length."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x9A, 0x00])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].length == 0
        assert nodes[0].value == b""

    def test_parse_multiple_primitives(self):
        """Parse multiple primitive tags sequentially."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x9A, 0x03, 0x21, 0x03, 0x15,
            0x9F, 0x02, 0x04, 0x00, 0x00, 0x10, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 2
        assert nodes[0].tag == "9A"
        assert nodes[1].tag == "9F02"

    def test_parse_empty_buffer(self):
        """Parse empty buffer returns empty list."""
        from emv_tlv.core.tlv_parser import TLVParser
        nodes = TLVParser.parse(b"")
        assert nodes == []

    def test_truncated_value_raises(self):
        """Test buffer overrun raises error."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x9A, 0x05, 0x21, 0x03])
        with pytest.raises(ValueError, match="Buffer overrun"):
            TLVParser.parse(data)


class TestTLVParserConstructed:
    def test_parse_constructed_with_children(self):
        """Parse constructed tag with children."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x6F, 0x08,
            0x84, 0x02, 0xA0, 0x00,
            0xA5, 0x02, 0x50, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].tag == "6F"
        assert nodes[0].is_constructed is True
        assert len(nodes[0].children) == 2
        assert nodes[0].children[0].tag == "84"
        assert nodes[0].children[1].tag == "A5"

    def test_parse_3_level_nested(self):
        """Parse 3-level nested constructed tags."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x6F, 0x09,
            0xA5, 0x07,
            0xBF, 0x0C, 0x04,
            0x50, 0x02, 0xAB, 0xCD,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        root = nodes[0]
        assert root.tag == "6F"
        assert len(root.children) == 1
        level1 = root.children[0]
        assert level1.tag == "A5"
        assert len(level1.children) == 1
        level2 = level1.children[0]
        assert level2.tag == "BF0C"
        assert len(level2.children) == 1
        level3 = level2.children[0]
        assert level3.tag == "50"
        assert level3.is_primitive() is True

    def test_parse_constructed_no_children(self):
        """Parse constructed tag with no children."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x6F, 0x00])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].is_constructed is True
        assert len(nodes[0].children) == 0

    def test_parse_mixed_primitive_constructed(self):
        """Parse mixed primitive and constructed tags."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x9A, 0x03, 0x21, 0x03, 0x15,
            0x6F, 0x05, 0x84, 0x03, 0xA0, 0x00, 0x01,
            0x9F, 0x02, 0x06, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 3
        assert nodes[0].is_primitive() is True
        assert nodes[1].is_constructed is True
        assert nodes[2].is_primitive() is True


class TestTLVParserTwoByteTags:
    def test_parse_2_byte_primitive(self):
        """Parse 2-byte primitive tag."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x9F, 0x02, 0x06,
            0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].tag == "9F02"
        assert nodes[0].is_primitive() is True

    def test_parse_2_byte_constructed(self):
        """Parse 2-byte constructed tag."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0xBF, 0x0C, 0x06,
            0x50, 0x04, 0x54, 0x45, 0x53, 0x54,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].tag == "BF0C"
        assert nodes[0].is_constructed is True
        assert len(nodes[0].children) == 1
        assert nodes[0].children[0].tag == "50"

    def test_parse_mixed_1_and_2_byte_tags(self):
        """Parse mix of 1-byte and 2-byte tags."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x9A, 0x03, 0x21, 0x03, 0x15,
            0x9F, 0x02, 0x04, 0x00, 0x10, 0x00, 0x00,
            0x82, 0x02, 0x39, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 3
        assert nodes[0].tag == "9A"
        assert nodes[1].tag == "9F02"
        assert nodes[2].tag == "82"

    def test_detect_constructed_flag_2_byte(self):
        """Test constructed flag detection for 2-byte tags."""
        from emv_tlv.core.tlv_parser import TLVParser
        # Primitive
        prim = TLVParser.parse(bytes([0x9F, 0x02, 0x01, 0x00]))
        assert prim[0].is_primitive() is True
        # Constructed
        cons = TLVParser.parse(bytes([0xBF, 0x0C, 0x02, 0x50, 0x00]))
        assert cons[0].is_constructed is True

    def test_parse_zka_dfxx_tags(self):
        """Parse ZKA DFxx tags."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0xDF, 0x11, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00,
            0xDF, 0x12, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 2
        assert nodes[0].tag == "DF11"
        assert nodes[1].tag == "DF12"


class TestTLVParserLongLength:
    def test_parse_2_byte_length_0x81(self):
        """Parse 2-byte length with 0x81 prefix."""
        from emv_tlv.core.tlv_parser import TLVParser
        value = bytes([0xAB]) * 128
        data = bytes([0x9A, 0x81, 128]) + value
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].length == 128

    def test_parse_2_byte_length_max_255(self):
        """Parse 2-byte length at max (255)."""
        from emv_tlv.core.tlv_parser import TLVParser
        value = bytes([0xCD]) * 255
        data = bytes([0x9A, 0x81, 255]) + value
        nodes = TLVParser.parse(data)
        assert nodes[0].length == 255

    def test_parse_3_byte_length_0x82(self):
        """Parse 3-byte length with 0x82 prefix."""
        from emv_tlv.core.tlv_parser import TLVParser
        value = bytes([0xEF]) * 256
        data = bytes([0x9A, 0x82, 0x01, 0x00]) + value
        nodes = TLVParser.parse(data)
        assert nodes[0].length == 256

    def test_parse_length_boundaries(self):
        """Test length boundary values."""
        from emv_tlv.core.tlv_parser import TLVParser
        # 127 (short form)
        assert TLVParser.parse(bytes([0x9A, 0x7F]) + bytes(127))[0].length == 127
        # 128 (0x81 form)
        assert TLVParser.parse(bytes([0x9A, 0x81, 0x80]) + bytes(128))[0].length == 128
        # 255 (max 0x81)
        assert TLVParser.parse(bytes([0x9A, 0x81, 0xFF]) + bytes(255))[0].length == 255
        # 256 (0x82 form)
        assert TLVParser.parse(bytes([0x9A, 0x82, 0x01, 0x00]) + bytes(256))[0].length == 256


class TestTLVParserPadding:
    def test_skip_leading_0x00(self):
        """Skip leading 0x00 padding bytes."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x00, 0x00, 0x00, 0x9A, 0x03, 0x21, 0x03, 0x15])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1
        assert nodes[0].tag == "9A"

    def test_skip_leading_0xFF(self):
        """Skip leading 0xFF padding bytes."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0xFF, 0xFF, 0x9A, 0x03, 0x21, 0x03, 0x15])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1

    def test_skip_mixed_padding(self):
        """Skip mixed 0x00 and 0xFF padding."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x00, 0xFF, 0x00, 0xFF, 0x9A, 0x03, 0x21, 0x03, 0x15])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1

    def test_skip_trailing_padding(self):
        """Skip trailing padding bytes."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([0x9A, 0x03, 0x21, 0x03, 0x15, 0x00, 0x00, 0xFF, 0xFF])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 1

    def test_skip_padding_between_elements(self):
        """Skip padding between TLV elements."""
        from emv_tlv.core.tlv_parser import TLVParser
        data = bytes([
            0x9A, 0x03, 0x21, 0x03, 0x15,
            0x00, 0xFF, 0x00,
            0x82, 0x02, 0x39, 0x00,
        ])
        nodes = TLVParser.parse(data)
        assert len(nodes) == 2

    def test_only_padding_returns_empty(self):
        """Buffer with only padding returns empty list."""
        from emv_tlv.core.tlv_parser import TLVParser
        nodes = TLVParser.parse(bytes([0x00, 0x00, 0xFF, 0xFF, 0x00]))
        assert nodes == []