"""
Config Adapter - Parses Poseidon terminal configuration blobs.

Poseidon configs are pure TLV with no envelope - parse directly.

Key templates:
- E0: Terminal configuration (terminal-wide settings)
- E1: CA public keys per RID (certificate authority keys)
- E2: Application configuration per AID (payment app settings)

Application Configuration (E2) contains:
- AID (4F): Application Identifier
- Label (DF04): Application display name
- TAC Default (DF11): Terminal Action Code - Default
- TAC Denial (DF12): Terminal Action Code - Denial
- TAC Online (DF13): Terminal Action Code - Online
- Floor Limit (DF05): Offline transaction limit
- Terminal Capabilities (9F33): Terminal feature flags

CA Keys (E1) contains:
- RID (DF01): Registered Application Provider Identifier
- Key Index (DF02): CA Public Key Index
- Modulus (E6): CA Public Key Modulus
- Exponent (E7): CA Public Key Exponent
- Checksum (DF03): Key checksum
"""

from emv_tlv.core.tlv_parser import TLVParser
from emv_tlv.core.tlv_node import TLVNode


class ConfigAdapter:
    """Adapter for parsing Poseidon terminal configuration blobs."""

    @staticmethod
    def parse(data: bytes) -> list[TLVNode]:
        """
        Parse a Poseidon configuration blob.

        Args:
            data: Raw config blob bytes

        Returns:
            Parsed TLV tree (list of TLVNode)
        """
        return TLVParser.parse(data)

    @staticmethod
    def get_application_configs(tree: list[TLVNode]) -> list[dict]:
        """
        Extract all application configurations from E2 templates.

        Args:
            tree: Parsed TLV tree

        Returns:
            List of application config dicts
        """
        configs: list[dict] = []
        e2_nodes = ConfigAdapter._find_all_templates(tree, "E2")

        for e2 in e2_nodes:
            config = ConfigAdapter._extract_app_config(e2)
            configs.append(config)

        return configs

    @staticmethod
    def _extract_app_config(e2_node: TLVNode) -> dict:
        """
        Extract application configuration from a single E2 node.

        Args:
            e2_node: E2 template node

        Returns:
            Application configuration dict
        """
        config: dict = {}

        # Find each field
        aid = ConfigAdapter._find_child(e2_node, "4F")
        label = ConfigAdapter._find_child(e2_node, "DF04")
        tac_default = ConfigAdapter._find_child(e2_node, "DF11")
        tac_denial = ConfigAdapter._find_child(e2_node, "DF12")
        tac_online = ConfigAdapter._find_child(e2_node, "DF13")
        floor_limit = ConfigAdapter._find_child(e2_node, "DF05")
        terminal_capabilities = ConfigAdapter._find_child(e2_node, "9F33")

        if aid:
            config["aid"] = aid.value.hex().upper()
        if label:
            config["label"] = label.value.decode("ascii")
        if tac_default:
            config["tac_default"] = tac_default.value.hex().upper()
        if tac_denial:
            config["tac_denial"] = tac_denial.value.hex().upper()
        if tac_online:
            config["tac_online"] = tac_online.value.hex().upper()
        if floor_limit:
            config["floor_limit"] = ConfigAdapter._parse_amount(floor_limit.value)
        if terminal_capabilities:
            config["terminal_capabilities"] = terminal_capabilities.value.hex().upper()

        return config

    @staticmethod
    def get_ca_keys(tree: list[TLVNode]) -> list[dict]:
        """
        Extract all CA keys from E1 templates.

        Args:
            tree: Parsed TLV tree

        Returns:
            List of CA key dicts
        """
        keys: list[dict] = []
        e1_nodes = ConfigAdapter._find_all_templates(tree, "E1")

        for e1 in e1_nodes:
            key = ConfigAdapter._extract_ca_key(e1)
            keys.append(key)

        return keys

    @staticmethod
    def _extract_ca_key(e1_node: TLVNode) -> dict:
        """
        Extract CA key from a single E1 node.

        Args:
            e1_node: E1 template node

        Returns:
            CA key dict
        """
        key: dict = {}

        rid = ConfigAdapter._find_child(e1_node, "DF01")
        key_index = ConfigAdapter._find_child(e1_node, "DF02")
        modulus = ConfigAdapter._find_child(e1_node, "E6")
        exponent = ConfigAdapter._find_child(e1_node, "E7")
        checksum = ConfigAdapter._find_child(e1_node, "DF03")

        if rid:
            key["rid"] = rid.value.hex().upper()
        if key_index:
            key["key_index"] = key_index.value[0]
        if modulus:
            key["modulus"] = modulus.value.hex().upper()
        if exponent:
            key["exponent"] = exponent.value.hex().upper()
        if checksum:
            key["checksum"] = checksum.value.hex().upper()

        return key

    @staticmethod
    def find_template(tree: list[TLVNode], tag: str) -> TLVNode | None:
        """Find a template by tag in the tree (DFS)."""
        for node in tree:
            if node.tag == tag:
                return node
            if node.is_constructed:
                found = ConfigAdapter.find_template(node.children, tag)
                if found:
                    return found
        return None

    @staticmethod
    def _find_all_templates(tree: list[TLVNode], tag: str) -> list[TLVNode]:
        """Find all templates by tag in the tree (DFS)."""
        results: list[TLVNode] = []

        for node in tree:
            if node.tag == tag:
                results.append(node)
            if node.is_constructed:
                child_results = ConfigAdapter._find_all_templates(
                    node.children, tag
                )
                results.extend(child_results)

        return results

    @staticmethod
    def _find_child(parent: TLVNode, tag: str) -> TLVNode | None:
        """Find a child node by tag (direct children only)."""
        for child in parent.children:
            if child.tag == tag:
                return child
        return None

    @staticmethod
    def _parse_amount(value: bytes) -> int:
        """Parse amount from BCD buffer."""
        amount = 0
        for byte in value:
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            amount = amount * 100 + high * 10 + low
        return amount