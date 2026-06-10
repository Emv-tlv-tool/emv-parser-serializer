"""
TLVNode - Represents a single Tag-Length-Value element in EMV data structure.

EMV uses a hierarchical TLV (Tag-Length-Value) encoding:
- Tag: 1 or 2 bytes identifying the data element
- Length: 1-3 bytes specifying the value length
- Value: The actual data (primitive) or nested TLV structures (constructed)

Primitive nodes: Contain raw data values (e.g., transaction date, amount)
Constructed nodes: Contain nested TLV structures forming a tree

Example hierarchy:
    6F (FCI Template - constructed)
      ├── 84 (AID - primitive)
      └── A5 (FCI Proprietary - constructed)
            └── 50 (Label - primitive)
"""


class TLVNode:
    """A single Tag-Length-Value element in an EMV data structure."""

    def __init__(self, tag: str, value: bytes, is_constructed: bool = False):
        """
        Create a new TLVNode.

        Args:
            tag: Tag identifier in uppercase hex (e.g., '9A', '6F')
            value: Raw value bytes (empty for constructed nodes initially)
            is_constructed: True if node contains nested TLV structures
        """
        self.tag = tag
        self.value = value
        self.length = len(value) if value else 0
        self.is_constructed = is_constructed
        self.children: list["TLVNode"] = []

    def add_child(self, node: "TLVNode") -> None:
        """
        Add a child node to this constructed node.

        Only constructed nodes can have children.

        Args:
            node: Child TLVNode to add

        Raises:
            ValueError: If attempting to add child to a primitive node
        """
        if self.is_constructed:
            self.children.append(node)
        else:
            raise ValueError("Cannot add child to primitive node")

    def get_children(self) -> list["TLVNode"]:
        """Get all child nodes."""
        return self.children

    def is_primitive(self) -> bool:
        """Check if this node is primitive (contains raw data)."""
        return not self.is_constructed

    def to_dict(self) -> dict:
        """
        Convert node to a dictionary for serialization/output.

        Recursively includes children for constructed nodes.
        Value is converted to uppercase hex string for readability.
        """
        result = {
            "tag": self.tag,
            "length": self.length,
            "value": self.value.hex().upper() if self.value else "",
            "is_constructed": self.is_constructed,
        }
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result

    def __repr__(self) -> str:
        return (
            f"TLVNode(tag={self.tag}, length={self.length}, "
            f"constructed={self.is_constructed})"
        )