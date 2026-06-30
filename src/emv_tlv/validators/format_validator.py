"""
FormatValidator - Level 1: Basic hex format validation.

Checks:
- Empty input
- Valid hex characters (0-9, A-F, a-f)
- Even length (hex must be in byte pairs)
- Strips common formatting (spaces, newlines, hyphens, colons)
"""

import re

from emv_tlv.validators.types import ValidationError, ValidationResult


class FormatValidator:
    """Validates hex string format."""

    # Characters to strip from hex input
    _STRIP_CHARS = re.compile(r"[\s\-:.,;]")

    # Valid hex character pattern
    _HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]*$")

    @staticmethod
    def clean_hex(data: str) -> str:
        """Strip formatting characters from a hex string."""
        return FormatValidator._STRIP_CHARS.sub("", data)

    @staticmethod
    def validate(data: str) -> ValidationResult:
        """
        Validate hex string format.

        Args:
            data: Raw hex string (possibly with formatting)

        Returns:
            ValidationResult
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        # Check empty input
        stripped = data.strip()
        if not stripped:
            errors.append(
                ValidationError(
                    code="EMPTY_INPUT",
                    message="Input is empty or contains only whitespace",
                    position=0,
                    severity="error",
                )
            )
            return ValidationResult(valid=False, errors=errors, cleaned_hex=None)

        # Clean the hex string
        cleaned = FormatValidator.clean_hex(stripped)

        # Check if any non-hex characters were stripped (warning)
        if cleaned != stripped:
            pass  # Normal, formatting was present

        # Check for invalid hex characters
        if not FormatValidator._HEX_PATTERN.match(cleaned):
            # Find the first invalid character position in cleaned string
            for i, c in enumerate(cleaned):
                if c not in "0123456789ABCDEFabcdef":
                    # Map position back to original string
                    pos = FormatValidator._find_original_position(stripped, cleaned, i)
                    errors.append(
                        ValidationError(
                            code="INVALID_HEX_CHAR",
                            message=f"Invalid hex character '{c}' at position {pos}",
                            position=pos,
                            severity="error",
                        )
                    )
                    break  # Report first invalid character
            return ValidationResult(valid=False, errors=errors, cleaned_hex=None)

        # Check for odd length
        if len(cleaned) % 2 != 0:
            errors.append(
                ValidationError(
                    code="ODD_LENGTH",
                    message=f"Hex string has odd length ({len(cleaned)} characters); "
                    f"TLV requires byte pairs (even length)",
                    position=len(cleaned),
                    severity="error",
                )
            )
            return ValidationResult(valid=False, errors=errors, cleaned_hex=cleaned)

        # Success
        metadata = {
            "original_length": len(stripped),
            "cleaned_length": len(cleaned),
            "byte_count": len(cleaned) // 2,
        }

        return ValidationResult(
            valid=True,
            errors=[],
            warnings=warnings,
            cleaned_hex=cleaned,
            metadata=metadata,
        )

    @staticmethod
    def _find_original_position(raw: str, _cleaned: str, cleaned_pos: int) -> int:
        """Map a position in the cleaned string back to the original string."""
        raw_idx = 0
        clean_idx = 0
        while raw_idx < len(raw) and clean_idx <= cleaned_pos:
            if raw[raw_idx] in " \t\n\r\\-:.,;":
                raw_idx += 1
                continue
            if clean_idx == cleaned_pos:
                return raw_idx
            raw_idx += 1
            clean_idx += 1
        return raw_idx
