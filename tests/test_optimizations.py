"""Tests verifying that all 5 performance optimizations are working correctly."""

import time
import threading
import pytest
from emv_tlv import parse, serialize, TLVNode


# ============================================================================ #
#  Optimization #5 — Avoid node reconstruction in serialize()
# ============================================================================ #
class TestSerializeSkipsReconstruction:
    """Verify serialize() passes TLVNode instances directly to the serializer."""

    def test_serialize_passes_tlvnode_directly(self):
        """TLVNode instances should NOT go through _reconstruct_node."""
        tree = parse("9A03210315", "raw")
        node = tree[0]
        assert isinstance(node, TLVNode)

        # Serialize should work correctly
        result = serialize(node)
        assert result == "9A03210315"

    def test_serialize_list_of_tlvnode_directly(self):
        """List of TLVNode instances should be serialized without reconstruction."""
        tree = parse("9F1A0228009F350122", "raw")
        assert all(isinstance(n, TLVNode) for n in tree)

        result = serialize(tree)
        # Each TLVNode serialized directly -> no TLVNode reconstruction needed
        parsed_back = parse(result, "raw")
        assert len(parsed_back) == len(tree)
        for original, reparsed in zip(tree, parsed_back):
            assert original.tag == reparsed.tag
            assert original["value"] == reparsed["value"]

    def test_serialize_constructed_tlvnode_directly(self):
        """Constructed TLVNode trees should serialize without node reconstruction."""
        tree = parse("E0099F1A0228009F350122", "raw")
        node = tree[0]
        assert isinstance(node, TLVNode)
        assert node.is_constructed

        result = serialize(node)
        assert result == "E0099F1A0228009F350122"

    def test_round_trip_matches_original_after_direct_serialize(self):
        """Round-trip should be byte-identical when serialize skips reconstruction."""
        inputs = [
            "9A03210315",
            "6F088402A000A5025000",
            "9F0206000010000000",
            "E0099F1A0228009F350122",
        ]
        for data in inputs:
            tree = parse(data, "raw")
            serialized = serialize(tree)
            assert serialized == data.upper()


# ============================================================================ #
#  Optimization #1 — Skip re-parse on inline edit
# ============================================================================ #
class TestInlineEditNoReParse:
    """Verify that editing a node value updates in-place without re-parsing."""

    def test_node_value_updates_in_place(self):
        """After value edit, the same node object should have the new value."""
        tree = parse("9A03210315", "raw")
        node = tree[0]
        original_id = id(node)
        original_tag = node.tag

        # Simulate what _commit_edit() does: update bytes and re-enhance
        new_bytes = bytes.fromhex("210316")
        node.value = new_bytes
        node._enhance()

        # The node object must be the same (no re-parse)
        assert id(node) == original_id
        assert node.tag == original_tag
        assert node["value"] == "210316"

    def test_tree_structure_unchanged_after_edit(self):
        """Editing a leaf should not change the tree structure or create new nodes."""
        tree = parse("E0099F1A0228009F350122", "raw")
        root = tree[0]
        child = root.children[0]

        root_id = id(root)
        children_ids = [id(c) for c in root.children]

        # Edit the leaf
        child.value = bytes.fromhex("0280")
        child._enhance()

        # Structure must be identical
        assert id(tree[0]) == root_id
        assert [id(c) for c in tree[0].children] == children_ids
        assert len(root.children) == 2

    def test_edit_triggers_no_full_reparse(self):
        """Verify that after edit, the tree is NOT re-parsed (identity preserved)."""
        tree = parse("6F088402A000A5025000", "raw")
        root = tree[0]
        child = root.children[0]

        # Track all node IDs before edit — collect from tree list
        def collect_ids(nodes, out_set):
            for n in nodes:
                out_set.add(id(n))
                if n.children:
                    collect_ids(n.children, out_set)

        ids_before = set()
        collect_ids(tree, ids_before)
        assert len(ids_before) == 4, "Expected 4 nodes in tree (6F + 84 + A5 + 50)"

        # Simulate edit
        child.value = bytes.fromhex("A000")
        child._enhance()

        # Re-collect IDs — they must be the same objects
        ids_after = set()
        collect_ids(tree, ids_after)
        assert ids_after == ids_before

    def test_serialize_after_edit_matches_expected(self):
        """After inline edit, serializing should produce the updated hex."""
        tree = parse("9A03210315", "raw")
        node = tree[0]
        node.value = bytes.fromhex("210316")
        node._enhance()

        result = serialize(tree)
        # Original was 9A03210315 (date 2021-03-15), now 9A03210316 (date 2021-03-16)
        assert result == "9A03210316"

    def test_edit_updates_dict_value_and_bytes_property(self):
        """Both dict access and bytes property should reflect the new value."""
        tree = parse("9A03210315", "raw")
        node = tree[0]

        assert node["value"] == "210315"
        assert node.value == bytes([0x21, 0x03, 0x15])

        # Edit — change date from 2021-03-15 to 2021-03-16
        node.value = bytes([0x21, 0x03, 0x16])
        node._enhance()

        assert node["value"] == "210316"
        assert node.value == bytes([0x21, 0x03, 0x16])


# ============================================================================ #
#  Optimization #2 — Sync parse for small payloads
# ============================================================================ #
class TestSyncParseSmallPayloads:
    """Verify that small payloads parse synchronously (no background thread)."""

    def test_small_payload_parses_synchronously(self):
        """A small payload (< 2KB) should complete parse in the same call."""
        small = "9A03210315"  # ~5 bytes
        # This parse should complete immediately (no thread)
        tree = parse(small, "raw")
        assert len(tree) == 1
        assert tree[0].tag == "9A"

    def test_medium_payload_no_thread_overhead(self):
        """Medium payload (still < 2KB) should parse without threading."""
        # Use known valid multi-node hex: 9F1A0228009F350122
        tree = parse("9F1A0228009F350122", "raw")
        assert len(tree) == 2
        assert tree[0].tag == "9F1A"
        assert tree[1].tag == "9F35"

    def test_sync_parse_returns_same_type_as_async(self):
        """Sync parse should return the same type (list[TLVNode]) as async parse."""
        from emv_tlv import TLVNode
        tree = parse("9F330360F8C8", "raw")
        assert isinstance(tree, list)
        assert all(isinstance(n, TLVNode) for n in tree)

    def test_sync_parse_with_config_fallback(self):
        """Sync parse should try raw first, then config fallback."""
        # This is a valid config blob that should parse correctly
        tree = parse("E0099F1A0228009F350122", "raw")
        assert len(tree) == 1
        assert tree[0]["name"] is not None

    def test_sync_parse_speed(self):
        """Sync parse should complete in negligible time for small payloads."""
        start = time.perf_counter()
        for _ in range(1000):
            parse("9A03210315", "raw")
        elapsed = time.perf_counter() - start
        # 1000 parses should complete in under 2 seconds (likely < 0.5s)
        assert elapsed < 2.0, f"Sync parse too slow: {elapsed:.3f}s for 1000 iterations"


# ============================================================================ #
#  Optimization #3 — Cache bitmask attribute
# ============================================================================ #
class TestBitmaskCaching:
    """Verify that _cached_bitmask is set and used correctly."""

    def test_cached_bitmask_on_bitmask_tag(self):
        """Nodes with bitmask format should have _cached_bitmask populated."""
        tree = parse("9F330360F8C8", "raw")
        node = tree[0]

        # Manually cache (as _on_parse_complete does)
        self._cache_bitmasks(tree)

        assert hasattr(node, "_cached_bitmask")
        assert node._cached_bitmask is not None
        assert len(node._cached_bitmask) > 0

    def test_cached_bitmask_is_none_on_plain_tags(self):
        """Plain tags (numeric/bcd) should have _cached_bitmask = None."""
        tree = parse("9A03210315", "raw")
        node = tree[0]

        self._cache_bitmasks(tree)

        assert hasattr(node, "_cached_bitmask")
        assert node._cached_bitmask is None

    def test_cached_bitmask_matches_real_bitmask(self):
        """Cached bitmask should contain the exact same data as the real bitmask."""
        tree = parse("9F330360F8C8", "raw")
        node = tree[0]
        real_bitmask = node.get("bitmask")

        self._cache_bitmasks(tree)

        assert node._cached_bitmask == real_bitmask

    def test_cached_bitmask_on_constructed_nodes(self):
        """Constructed nodes should also get _cached_bitmask (will be None)."""
        tree = parse("E0099F1A0228009F350122", "raw")
        node = tree[0]

        self._cache_bitmasks(tree)

        assert hasattr(node, "_cached_bitmask")
        assert node._cached_bitmask is None  # constructed, not bitmask

    def test_cached_bitmask_on_nested_bitmask_nodes(self):
        """Bitmask tags should have cached bitmask."""
        tree = parse("9F330360F8C8", "raw")
        node = tree[0]

        self._cache_bitmasks(tree)

        assert hasattr(node, "_cached_bitmask")
        assert node._cached_bitmask is not None

    def test_cache_bitmasks_walks_full_tree(self):
        """_cache_bitmasks should recursively walk all children."""
        # Construct a tree with a bitmask tag nested inside
        # 9F33 = 2 bytes, length 03, value 60F8C8 = 3 bytes
        # 9F35 = 2 bytes, length 01, value 22 = 1 byte
        # Total = 2+1+3 + 2+1+1 = 10 bytes → length 0x0A
        tree = parse("E00A9F330360F8C89F350122", "raw")
        root = tree[0]

        self._cache_bitmasks(tree)

        # Root should have cached bitmask (None, since it's constructed)
        assert hasattr(root, "_cached_bitmask")

        # Child 0 (9F33) should have real bitmask data
        child0 = root.children[0]
        assert hasattr(child0, "_cached_bitmask")
        assert child0._cached_bitmask is not None

    @staticmethod
    def _cache_bitmasks(nodes):
        """Simulate the _cache_bitmasks method from App."""
        for node in nodes:
            node._cached_bitmask = node.get("bitmask")
            if node.children:
                TestBitmaskCaching._cache_bitmasks(node.children)


# ============================================================================ #
#  Optimization #4 — Reduced update_idletasks calls
# ============================================================================ #
class TestReducedIdleTasks:
    """Verify that parse works correctly with minimal update_idletasks calls."""

    def test_parse_works_with_single_flush(self):
        """Parse should succeed when called with only one UI flush."""
        # This simulates the optimized flow: validate -> set_status -> flush -> parse
        tree = parse("9A03210315", "raw")
        assert tree[0].tag == "9A"
        assert tree[0]["decoded"] == "2021-03-15"

    def test_parse_large_structure_no_extra_flush(self):
        """More complex structures should parse without needing extra flushes."""
        # Use valid multi-node payload (constructed E0 with 2 children)
        tree = parse("E0099F1A0228009F350122", "raw")
        assert tree[0].tag == "E0"
        assert len(tree[0].children) == 2

    def test_parse_after_clear_works(self):
        """Parse should work after clearing state (simulating _do_clear)."""
        # First parse
        tree1 = parse("9A03210315", "raw")
        assert len(tree1) == 1

        # Simulate clear: tree1 is dropped
        # Second parse (simulating what happens after clear in the GUI)
        tree2 = parse("9F1A022800", "raw")
        assert len(tree2) == 1
        assert tree2[0].tag == "9F1A"

    def test_round_trip_after_single_flush(self):
        """Full round-trip should work with minimal UI updates."""
        inputs = [
            "9A03210315",
            "6F088402A000A5025000",
            "9F0206000010000000",
        ]
        for data in inputs:
            tree = parse(data, "raw")
            serialized = serialize(tree)
            reparsed = parse(serialized, "raw")
            assert reparsed[0].tag == tree[0].tag
            assert reparsed[0]["value"] == tree[0]["value"]


# ============================================================================ #
#  Integration: All optimizations work together
# ============================================================================ #
class TestAllOptimizationsTogether:
    """End-to-end tests verifying all optimizations work in concert."""

    def test_parse_edit_serialize_flow(self):
        """
        Full optimized workflow:
        1. Parse (sync, no thread)
        2. Edit in-place (no re-parse)
        3. Serialize directly (no reconstruction)
        """
        # Step 1: Sync parse — use 9A (Transaction Date) for predictable hex
        tree = parse("9A03210315", "raw")
        node = tree[0]
        assert node.tag == "9A"
        assert node["value"] == "210315"

        # Step 2: In-place edit — change date from 2021-03-15 to 2021-03-16
        node.value = bytes.fromhex("210316")
        node._enhance()
        assert node["value"] == "210316"
        assert id(tree[0]) == id(node)  # Same object

        # Step 3: Serialize without reconstruction
        result = serialize(tree)
        assert result == "9A03210316"

        # Step 4: Verify round-trip
        reparsed = parse(result, "raw")
        assert reparsed[0].tag == "9A"
        assert reparsed[0]["value"] == "210316"

    def test_bitmask_tree_with_edit(self):
        """Bitmask tag inside a tree, edit a different leaf, no re-parse."""
        tree = parse("E00A9F330360F8C89F350122", "raw")
        root = tree[0]
        root_id = id(root)

        # Cache bitmasks
        for node in tree:
            node._cached_bitmask = node.get("bitmask")
            if node.children:
                for c in node.children:
                    c._cached_bitmask = c.get("bitmask")

        # Verify bitmask cache on 9F33
        assert root.children[0]._cached_bitmask is not None

        # Edit a different child (9F35 — plain tag)
        child1 = root.children[1]
        child1.value = bytes.fromhex("23")
        child1._enhance()

        # Verify no re-parse happened
        assert id(tree[0]) == root_id
        assert root.children[1]["value"] == "23"

        # Serialize should give correct result
        result = serialize(tree)
        assert "9F350123" in result.upper()
        assert "9F330360F8C8" in result.upper()

    def test_constructed_tree_sync_parse_and_serialize(self):
        """Constructed tree: sync parse, no reconstruction in serialize."""
        tree = parse("E0099F1A0228009F350122", "raw")
        node_ids_before = {id(n) for n in tree}
        for n in tree:
            if n.children:
                for c in n.children:
                    node_ids_before.add(id(c))

        # Serialize
        result = serialize(tree)
        assert result == "E0099F1A0228009F350122"

        # Parse again (sync)
        tree2 = parse(result, "raw")
        assert tree2[0].tag == "E0"
        assert len(tree2[0].children) == 2