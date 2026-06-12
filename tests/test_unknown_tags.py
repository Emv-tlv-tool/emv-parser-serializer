"""Tests for unknown tag detection via is_unknown flag in parse tree."""

from emv_tlv import parse


class TestUnknownTagInParseTree:
    def test_known_tag_no_is_unknown(self):
        """Known tags don't have is_unknown flag."""
        tree = parse("9F330360F8C8", "raw")
        assert "is_unknown" not in tree[0]

    def test_unknown_tag_has_is_unknown(self):
        """Tag not in dictionary gets is_unknown flag from _enhance_node."""
        tree = parse("9A03210315", "raw")
        assert tree[0].get("is_unknown") is True

    def test_unknown_tag_shows_unknown_label(self):
        """collect_lines shows [UNKNOWN] for unknown tags."""
        from parser.parse_tree import collect_lines
        tree = parse("9A03210315", "raw")
        lines = collect_lines(tree[0])
        assert any("[UNKNOWN]" in line for line in lines)

    def test_known_tag_does_not_show_unknown(self):
        """collect_lines does not show [UNKNOWN] for known tags."""
        from parser.parse_tree import collect_lines
        tree = parse("9F330360F8C8", "raw")
        lines = collect_lines(tree[0])
        assert not any("[UNKNOWN]" in line for line in lines)

    def test_mixed_known_and_unknown(self):
        """Mix of known/unknown: only unknown shows [UNKNOWN]."""
        from parser.parse_tree import collect_lines
        tree = parse("E00A" + "9F1A020280" + "9A03210315", "raw")
        for child in tree[0].get("children", []):
            clines = collect_lines(child)
            if "is_unknown" in child:
                assert any("[UNKNOWN]" in l for l in clines)
            else:
                assert not any("[UNKNOWN]" in l for l in clines)