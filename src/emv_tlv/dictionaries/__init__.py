"""
Tag Dictionaries Index

Merges EMVCo and ZKA tag dictionaries for unified lookup.
Provides functions to lookup tag metadata by tag hex or name.
"""

import json
import os

# Load dictionaries from JSON files
_dict_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_dict_dir, "emvco_tags.json")) as f:
    _emvco_tags = json.load(f)

with open(os.path.join(_dict_dir, "zka_tags.json")) as f:
    _zka_tags = json.load(f)

# Combined dictionary (ZKA tags take precedence for overlapping entries)
_all_tags = {**_emvco_tags, **_zka_tags}


class Dictionary:
    """Unified tag dictionary with lookup utilities."""

    @staticmethod
    def lookup_by_tag(tag: str) -> dict | None:
        """
        Lookup tag information by tag hex value.

        Args:
            tag: Tag identifier in uppercase hex (e.g., '9A', 'DF11')

        Returns:
            Tag metadata dict or None if not found
        """
        return _all_tags.get(tag)

    @staticmethod
    def lookup_by_name(name: str) -> dict | None:
        """
        Lookup tag information by tag name.

        Args:
            name: Tag name (e.g., 'PAN', 'TAC Default')

        Returns:
            Tag metadata dict with 'tag' key or None if not found
        """
        for tag_hex, metadata in _all_tags.items():
            if metadata.get("name", "").lower() == name.lower():
                return {"tag": tag_hex, **metadata}
        return None

    @staticmethod
    def get_tags_by_source(source: str) -> dict:
        """
        Get all tags from a specific source.

        Args:
            source: Source identifier ('EMVCo' or 'ZKA')

        Returns:
            Dictionary of tags from that source
        """
        return {
            tag_hex: metadata
            for tag_hex, metadata in _all_tags.items()
            if metadata.get("source") == source
        }

    @staticmethod
    def get_emvco_tags() -> dict:
        """Get all EMVCo tags."""
        return dict(_emvco_tags)

    @staticmethod
    def get_zka_tags() -> dict:
        """Get all ZKA tags."""
        return dict(_zka_tags)

    @staticmethod
    def has_tag(tag: str) -> bool:
        """Check if a tag exists in the dictionary."""
        return tag in _all_tags

    @staticmethod
    def get_all_tags() -> list[str]:
        """Get all tag hex values."""
        return list(_all_tags.keys())

    @staticmethod
    def enhance_node(node: dict) -> dict:
        """Enhance a TLV node dict with tag metadata."""
        metadata = Dictionary.lookup_by_tag(node.get("tag", ""))
        if metadata:
            return {
                **node,
                "name": metadata["name"],
                "description": metadata.get("description", ""),
                "format": metadata.get("format", ""),
                "source": metadata.get("source", ""),
            }
        return node