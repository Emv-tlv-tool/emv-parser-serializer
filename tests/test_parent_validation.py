"""Tests for TLVNode parent validation and default metadata enhancement."""

import pytest
from emv_tlv import parse
from emv_tlv.core.tlv_node import TLVNode


class TestTLVNodeEnhancementAndParentValidation:
    def test_default_enhancement_attributes(self):
        """Verify that parsed nodes have enhancement attributes by default."""
        tree = parse("9F1A022800", "raw")
        node = tree[0]
        
        # Test class properties/attributes
        assert isinstance(node, TLVNode)
        assert node.tag == "9F1A"
        assert node.name == "Terminal Country Code"
        assert node.format == "bcd"
        assert node.description == "EMVCO_TERMINAL_COUNTRY_CODE"
        assert node.source == ""
        assert node.decoded == "Germany (280)"
        assert node.is_unknown is False
        assert node.is_valid_parent is True
        assert node.parent_validation_error is None

        # Test dictionary-like access
        assert node["tag"] == "9F1A"
        assert node["name"] == "Terminal Country Code"
        assert node["format"] == "bcd"
        assert node["description"] == "EMVCO_TERMINAL_COUNTRY_CODE"
        assert node["source"] == ""
        assert node["decoded"] == "Germany (280)"
        assert "is_unknown" not in node
        assert node["is_valid_parent"] is True
        assert "parent_validation_error" not in node

    def test_root_node_is_valid_parent(self):
        """Root nodes (with no parent) have is_valid_parent set to True."""
        node = TLVNode("9F1A", bytes([0x28, 0x00]))
        assert node.parent is None
        assert node.is_valid_parent is True
        assert node.parent_validation_error is None
        assert node["is_valid_parent"] is True

    def test_valid_parent_relationship(self):
        """Verify parent validation is True when the parent tag is allowed in metadata."""
        # E0 is an allowed parent tag for 9F1A in emvco_tags.json
        parent = TLVNode("E0", b"", is_constructed=True)
        child = TLVNode("9F1A", bytes([0x28, 0x00]))
        
        parent.add_child(child)
        
        assert child.parent == parent
        assert child.is_valid_parent is True
        assert child.parent_validation_error is None

    def test_invalid_parent_relationship(self):
        """Verify parent validation is False when the parent tag is not allowed in metadata."""
        # F0 is NOT an allowed parent tag for 9F1A in emvco_tags.json (only DF40, DF43, E0)
        parent = TLVNode("F0", b"", is_constructed=True)
        child = TLVNode("9F1A", bytes([0x28, 0x00]))
        
        parent.add_child(child)
        
        assert child.parent == parent
        assert child.is_valid_parent is False
        assert "expected parent is one of" in child.parent_validation_error
        assert child["is_valid_parent"] is False
        assert "parent_validation_error" in child

    def test_dynamic_validation_recalculation(self):
        """Verify that validation status recalculates if node gets a new parent."""
        child = TLVNode("9F1A", bytes([0x28, 0x00]))
        assert child.is_valid_parent is True  # True because root initially
        
        invalid_parent = TLVNode("F0", b"", is_constructed=True)
        invalid_parent.add_child(child)
        assert child.is_valid_parent is False
        
        # Move child to a valid parent
        valid_parent = TLVNode("E0", b"", is_constructed=True)
        valid_parent.add_child(child)
        assert child.parent == valid_parent
        assert child.is_valid_parent is True
        assert child.parent_validation_error is None
