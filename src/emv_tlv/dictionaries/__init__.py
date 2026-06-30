"""
Tag Dictionary — charge un seul fichier JSON (tags(4).json)
et fournit des fonctions de recherche par tag ou par nom.
"""

import json
import os

_dict_dir = os.path.dirname(os.path.abspath(__file__))
JSON_FILE = "tags (4).json"  # adaptez si le nom diffère

# Charger la liste d'objets JSON et la transformer en dict tag -> métadonnées
with open(os.path.join(_dict_dir, JSON_FILE), encoding="utf-8") as f:
    _tags_list = json.load(f)

# Indexation par "poseidon_tag" (prioritaire) ou "tai_tag"
_all_tags = {}
for entry in _tags_list:
    tag = entry.get("poseidon_tag")
    if tag:
        _all_tags[tag] = entry


class Dictionary:
    """Unified tag dictionary with lookup utilities."""

    @staticmethod
    def lookup_by_tag(tag: str) -> dict | None:
        """Retourne les métadonnées du tag (ou None)."""
        return _all_tags.get(tag)

    @staticmethod
    def lookup_by_name(name: str) -> dict | None:
        """Recherche un tag par son nom (insensible à la casse)."""
        for tag_hex, metadata in _all_tags.items():
            if metadata.get("name", "").lower() == name.lower():
                return {"tag": tag_hex, **metadata}
        return None

    @staticmethod
    def has_tag(tag: str) -> bool:
        return tag in _all_tags

    @staticmethod
    def get_all_tags() -> list[str]:
        return list(_all_tags.keys())

    @staticmethod
    def enhance_node(node: dict) -> dict:
        """Enrichit un nœud TLV avec les métadonnées du tag."""
        metadata = Dictionary.lookup_by_tag(node.get("tag", ""))
        if metadata:
            # On conserve toutes les clés utiles
            return {
                **node,
                "name": metadata.get("name", ""),
                "description": metadata.get("description", ""),
                "format": metadata.get("value_format") or metadata.get("format", ""),
                "source": metadata.get("source", ""),
                "bytes": metadata.get("bytes"),  # pour les bitmasks
                "bitmask": metadata.get("bitmask"),  # ancien format
            }
        return node
