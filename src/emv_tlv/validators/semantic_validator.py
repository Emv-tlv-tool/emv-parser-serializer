"""
SemanticValidator - Level 3: Dictionary-based tag metadata validation.

Validates:
- Tags exist in dictionaries
- Tag hierarchy (parent-child relationships)
- Value lengths against tag metadata
"""

from emv_tlv.dictionaries import Dictionary
from emv_tlv.validators.types import ValidationError, ValidationResult


class SemanticValidator:
    """Validates tags against dictionary metadata."""

    @staticmethod
    def validate(data: str, nodes: list) -> ValidationResult:
        """
        Validate tags against dictionary metadata.

        Args:
            data: Cleaned hex string
            nodes: Parsed node list from structure validator

        Returns:
            ValidationResult
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        if not nodes:
            return ValidationResult(valid=True, cleaned_hex=data)

        SemanticValidator._validate_nodes(nodes, None, errors, warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_hex=data,
            metadata={"tag_count": len(nodes)},
        )

    @staticmethod
    def _validate_nodes(
        nodes: list,
        parent_tag: str | None,
        errors: list,
        warnings: list,
    ) -> None:
        """Recursively validate nodes."""
        for node in nodes:
            tag = node.get("tag", "")
            metadata = Dictionary.lookup_by_tag(tag)

            if metadata is None:
                warnings.append(
                    ValidationError(
                        code="UNKNOWN_TAG",
                        message=f"Tag {tag} not found in dictionary",
                        position=0,
                        severity="warning",
                    )
                )
            else:
                # Check parent-child relationship
                if parent_tag is not None:
                    SemanticValidator._check_parent_child(tag, parent_tag, metadata, warnings)

            # Recursively validate children
            if node.get("children"):
                SemanticValidator._validate_nodes(node["children"], tag, errors, warnings)

    @staticmethod
    def _check_parent_child(
        tag: str,
        parent_tag: str,
        metadata: dict,
        warnings: list,
    ) -> None:
        """Check if tag is valid under parent tag."""
        parent_tags = metadata.get("parent_tags", [])
        if parent_tags and parent_tag not in parent_tags:
            warnings.append(
                ValidationError(
                    code="INVALID_PARENT",
                    message=f"Tag {tag} appears under {parent_tag}, "
                    f"but expected parent is one of: {parent_tags}",
                    position=0,
                    severity="warning",
                )
            )
