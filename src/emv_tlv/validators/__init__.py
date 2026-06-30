"""
EMV TLV Validators Package

Provides multi-level validation for hexadecimal TLV input:
- Level 1 (format): Basic hex character and length validation
- Level 2 (structure): TLV tag-length-value structure validation
- Level 3 (semantic): Dictionary-based tag metadata validation
"""

from emv_tlv.validators.format_validator import FormatValidator
from emv_tlv.validators.semantic_validator import SemanticValidator
from emv_tlv.validators.structure_validator import StructureValidator
from emv_tlv.validators.types import (
    ValidationError as ValidationError,
)
from emv_tlv.validators.types import (
    ValidationResult as ValidationResult,
)


def validate_hex(
    data: str | bytes,
    level: str = "format",
    strict: bool = False,
) -> ValidationResult:
    """
    Validate hexadecimal TLV input at the specified level.

    Args:
        data: Hex string or bytes to validate
        level: Validation depth - "format", "structure", or "semantic"
        strict: If True, raises exception on first error. If False,
                returns ValidationResult with all errors/warnings.

    Returns:
        ValidationResult with valid flag, errors, warnings, cleaned hex, and metadata.

    Raises:
        ValueError: If strict=True and validation fails
        ValueError: If level is unknown
    """
    if level not in ("format", "structure", "semantic"):
        raise ValueError(
            f"Unknown validation level: '{level}'. " f"Use 'format', 'structure', or 'semantic'."
        )

    # Convert bytes to hex string if needed
    if isinstance(data, bytes):
        data = data.hex()

    # Level 1: Format validation
    result = FormatValidator.validate(data)
    if not result.valid:
        if strict:
            raise ValueError(f"Format validation failed: {result.errors[0].message}")
        return result  # Stop early if format is invalid
    if level == "format":
        return result

    # Level 2: Structure validation
    result = StructureValidator.validate(result.cleaned_hex)
    if strict and not result.valid:
        raise ValueError(f"Structure validation failed: {result.errors[0].message}")
    if level == "structure":
        return result

    # Level 3: Semantic validation
    result = SemanticValidator.validate(
        result.cleaned_hex or data, result.metadata.get("nodes", [])
    )
    if strict and not result.valid:
        raise ValueError(f"Semantic validation failed: {result.errors[0].message}")

    return result
