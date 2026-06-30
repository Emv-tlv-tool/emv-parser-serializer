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


class TLVNode(dict):
    """A single Tag-Length-Value element in an EMV data structure."""

    def __init__(
        self,
        tag: str,
        value: bytes,
        is_constructed: bool = False,
        parent: "TLVNode | None" = None,
    ):
        """
        Create a new TLVNode.

        Args:
            tag: Tag identifier in uppercase hex (e.g., '9A', '6F')
            value: Raw value bytes
            is_constructed: True if node contains nested TLV structures
            parent: Parent TLVNode if any
        """
        super().__init__()
        self._value_bytes = value or b""
        self.parent = parent

        # Initialize standard dict keys
        self["tag"] = tag
        self["length"] = len(self._value_bytes)
        self["value"] = self._value_bytes.hex().upper() if self._value_bytes else ""
        self["is_constructed"] = is_constructed

        # Run metadata enrichment and parent validation
        self._enhance()

    @property
    def tag(self) -> str:
        return self["tag"]

    @tag.setter
    def tag(self, val: str) -> None:
        self["tag"] = val

    @property
    def value(self) -> bytes:
        return self._value_bytes

    @value.setter
    def value(self, val: bytes) -> None:
        self._value_bytes = val or b""
        self["value"] = self._value_bytes.hex().upper() if self._value_bytes else ""
        self["length"] = len(self._value_bytes)

    @property
    def length(self) -> int:
        return self["length"]

    @length.setter
    def length(self, val: int) -> None:
        self["length"] = val

    @property
    def is_constructed(self) -> bool:
        return self["is_constructed"]

    @is_constructed.setter
    def is_constructed(self, val: bool) -> None:
        self["is_constructed"] = val

    @property
    def children(self) -> list["TLVNode"]:
        if "children" not in self:
            self["children"] = []
        return self["children"]

    @children.setter
    def children(self, val: list["TLVNode"]) -> None:
        self["children"] = val

    @property
    def name(self) -> str | None:
        return self.get("name")

    @name.setter
    def name(self, val: str | None) -> None:
        if val is not None:
            self["name"] = val
        elif "name" in self:
            del self["name"]

    # --- NOUVELLE PROPRIÉTÉ tech_name ---
    @property
    def tech_name(self) -> str:
        return self.get("tech_name", "")

    @tech_name.setter
    def tech_name(self, val: str) -> None:
        if val:
            self["tech_name"] = val
        elif "tech_name" in self:
            del self["tech_name"]

    @property
    def description(self) -> str:
        return self.get("description", "")

    @description.setter
    def description(self, val: str) -> None:
        if val:
            self["description"] = val
        elif "description" in self:
            del self["description"]

    @property
    def format(self) -> str:
        return self.get("format", "")

    @format.setter
    def format(self, val: str) -> None:
        if val:
            self["format"] = val
        elif "format" in self:
            del self["format"]

    @property
    def source(self) -> str:
        return self.get("source", "")

    @source.setter
    def source(self, val: str) -> None:
        if val:
            self["source"] = val
        elif "source" in self:
            del self["source"]

    @property
    def is_unknown(self) -> bool:
        return self.get("is_unknown", False)

    @is_unknown.setter
    def is_unknown(self, val: bool) -> None:
        if val:
            self["is_unknown"] = True
        elif "is_unknown" in self:
            del self["is_unknown"]

    @property
    def decoded(self) -> str | None:
        return self.get("decoded")

    @decoded.setter
    def decoded(self, val: str | None) -> None:
        if val is not None:
            self["decoded"] = val
        elif "decoded" in self:
            del self["decoded"]

    @property
    def bitmask(self) -> list[dict] | None:
        return self.get("bitmask")

    @bitmask.setter
    def bitmask(self, val: list[dict] | None) -> None:
        if val is not None:
            self["bitmask"] = val
        elif "bitmask" in self:
            del self["bitmask"]

    @property
    def is_valid_parent(self) -> bool:
        return self.get("is_valid_parent", True)

    @is_valid_parent.setter
    def is_valid_parent(self, val: bool) -> None:
        self["is_valid_parent"] = val

    @property
    def parent_validation_error(self) -> str | None:
        return self.get("parent_validation_error")

    @parent_validation_error.setter
    def parent_validation_error(self, val: str | None) -> None:
        if val is not None:
            self["parent_validation_error"] = val
        elif "parent_validation_error" in self:
            del self["parent_validation_error"]

    def _enhance(self) -> None:
        """Fetch metadata, decode value and bitmask."""
        from emv_tlv.dictionaries import Dictionary
        from emv_tlv.decoders.value_decoder import ValueDecoder
        from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder

        metadata = Dictionary.lookup_by_tag(self.tag)
        if metadata:
            self["name"] = metadata.get("name", "")
            self["tech_name"] = metadata.get("tech_name", "")  # ← ici
            self["description"] = metadata.get("description", "")
            self["format"] = metadata.get("value_format") or metadata.get("format", "")
            self["source"] = metadata.get("source", "")
        else:
            self["is_unknown"] = True

        if not self.is_constructed and self._value_bytes and len(self._value_bytes) > 0:
            try:
                decoded = ValueDecoder.decode_value(self.tag, self._value_bytes)
            except Exception:
                decoded = self._value_bytes.hex().upper()
            self["decoded"] = decoded

            fmt = metadata.get("value_format") or metadata.get("format", "") if metadata else ""
            if fmt == "bitmask":
                self["bitmask"] = BitmaskDecoder.decode_bitmask(self.tag, self._value_bytes)

        self.validate_parent()

    def validate_parent(self) -> None:
        """Validate if the current parent tag matches metadata requirements."""
        if self.parent:
            from emv_tlv.dictionaries import Dictionary

            metadata = Dictionary.lookup_by_tag(self.tag)
            if metadata:
                parent_tags = metadata.get("parent_tags", [])
                if parent_tags and self.parent.tag not in parent_tags:
                    self["is_valid_parent"] = False
                    self["parent_validation_error"] = (
                        f"Tag {self.tag} appears under parent {self.parent.tag}, "
                        f"but expected parent is one of: {parent_tags}"
                    )
                else:
                    self["is_valid_parent"] = True
                    if "parent_validation_error" in self:
                        del self["parent_validation_error"]
            else:
                self["is_valid_parent"] = True
                if "parent_validation_error" in self:
                    del self["parent_validation_error"]
        else:
            self["is_valid_parent"] = True
            if "parent_validation_error" in self:
                del self["parent_validation_error"]

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
            if "children" not in self:
                self["children"] = []
            self.children.append(node)
            node.parent = self
            node.validate_parent()
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