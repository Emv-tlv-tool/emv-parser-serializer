"""
StructureValidator - Level 2: TLV structure validation.

Parses the hex data as BER-TLV and validates:
- Tag format (1 or 2 bytes, proper multi-byte encoding)
- Length encoding (valid prefixes, matches actual value)
- Buffer bounds (no truncated values)
- Constructed nodes have valid children
- Padding bytes (0x00, 0xFF) are properly handled
"""

from emv_tlv.validators.types import ValidationError, ValidationResult


class StructureValidator:
    """Validates TLV structure of hex data."""

    @staticmethod
    def validate(data: str) -> ValidationResult:
        """
        Validate TLV structure of hex data.

        Args:
            data: Cleaned hex string (no formatting)

        Returns:
            ValidationResult
        """
        errors: list[ValidationError] = []
        warnings: list[ValidationError] = []

        try:
            data_bytes = bytes.fromhex(data)
        except ValueError as e:
            errors.append(
                ValidationError(
                    code="INVALID_HEX",
                    message=f"Invalid hex data: {e}",
                    position=0,
                    severity="error",
                )
            )
            return ValidationResult(valid=False, errors=errors)

        byte_offset = 0  # byte position
        hex_offset = 0  # hex char position
        nodes = []
        padding_count = 0

        while byte_offset < len(data_bytes):
            # Skip padding bytes (0x00 and 0xFF)
            if data_bytes[byte_offset] in (0x00, 0xFF):
                hex_offset += 2
                byte_offset += 1
                padding_count += 1
                continue

            # Try to parse a node
            node, byte_offset, hex_offset, node_errors = StructureValidator._parse_node(
                data_bytes, byte_offset, hex_offset, 0
            )
            errors.extend(node_errors)
            if node:
                nodes.append(node)

        if padding_count > 0:
            warnings.append(
                ValidationError(
                    code="PADDING_BYTES",
                    message=f"Found {padding_count} padding byte(s) (0x00/0xFF) skipped in data",
                    position=0,
                    severity="warning",
                )
            )

        tag_count = sum(1 for _ in StructureValidator._count_all(nodes))
        leaf_count = sum(1 for _ in StructureValidator._count_leaves(nodes))
        max_depth = max((n["depth"] for n in StructureValidator._count_leaves(nodes)), default=0)

        metadata = {
            "byte_count": len(data_bytes),
            "tag_count": tag_count,
            "leaf_count": leaf_count,
            "max_depth": max_depth,
            "nodes": nodes,
        }

        # Separate warnings from errors
        real_errors = [e for e in errors if e.severity == "error"]
        real_warnings = [e for e in errors if e.severity == "warning"]

        return ValidationResult(
            valid=len(real_errors) == 0,
            errors=real_errors,
            warnings=warnings + real_warnings,
            cleaned_hex=data,
            metadata=metadata,
        )

    @staticmethod
    def _parse_node(
        data_bytes: bytes,
        byte_offset: int,
        hex_offset: int,
        depth: int,
    ) -> tuple[dict | None, int, int, list]:
        """
        Parse a single TLV node from bytes.

        Returns:
            (node_dict, new_byte_offset, new_hex_offset, errors)
        """
        errors: list[ValidationError] = []

        # --- Parse tag ---
        if byte_offset >= len(data_bytes):
            errors.append(
                ValidationError(
                    code="TRUNCATED_TAG",
                    message=f"Buffer truncated at byte {byte_offset}: cannot read tag",
                    position=hex_offset,
                    severity="error",
                )
            )
            return None, byte_offset, hex_offset, errors

        first_byte = data_bytes[byte_offset]
        first_tag_hex_offset = hex_offset

        tag, tag_length, tag_errors = StructureValidator._parse_tag(
            data_bytes, byte_offset, hex_offset
        )
        errors.extend(tag_errors)
        if tag is None:
            return None, byte_offset + 1, hex_offset + 2, errors

        byte_offset += tag_length
        hex_offset += tag_length * 2

        is_constructed = bool(first_byte & 0x20)

        # --- Parse length ---
        if byte_offset >= len(data_bytes):
            errors.append(
                ValidationError(
                    code="TRUNCATED_LENGTH",
                    message=f"Buffer truncated at byte {byte_offset}: cannot read length for tag {tag}",
                    position=hex_offset,
                    severity="error",
                )
            )
            return None, byte_offset, hex_offset, errors

        length, length_bytes, length_errors = StructureValidator._parse_length(
            data_bytes, byte_offset, hex_offset
        )
        errors.extend(length_errors)
        if length is None:
            return None, byte_offset + 1, hex_offset + 2, errors

        byte_offset += length_bytes
        hex_offset += length_bytes * 2

        # --- Check value bounds ---
        if byte_offset + length > len(data_bytes):
            errors.append(
                ValidationError(
                    code="TRUNCATED_VALUE",
                    message=f"Tag {tag} at byte {first_tag_hex_offset // 2}: "
                    f"value length {length} extends beyond buffer "
                    f"({byte_offset + length} > {len(data_bytes)})",
                    position=first_tag_hex_offset,
                    severity="error",
                )
            )
            return None, byte_offset, hex_offset, errors

        children = []

        # --- Recursively parse children for constructed nodes ---
        if is_constructed and length > 0:
            child_offset = byte_offset
            child_hex_offset = hex_offset
            while child_offset < byte_offset + length:
                if data_bytes[child_offset] in (0x00, 0xFF):
                    child_offset += 1
                    child_hex_offset += 2
                    continue
                child, child_offset, child_hex_offset, child_errors = (
                    StructureValidator._parse_node(
                        data_bytes, child_offset, child_hex_offset, depth + 1
                    )
                )
                errors.extend(child_errors)
                if child:
                    children.append(child)

        node = {
            "tag": tag,
            "tag_bytes": tag_length,
            "length": length,
            "length_bytes": length_bytes,
            "is_constructed": is_constructed,
            "children": children,
            "depth": depth,
        }

        byte_offset += length
        hex_offset += length * 2

        return node, byte_offset, hex_offset, errors

    @staticmethod
    def _parse_tag(
        data_bytes: bytes,
        byte_offset: int,
        hex_offset: int,
    ) -> tuple[str | None, int, list]:
        """Parse BER-TLV tag bytes."""
        errors = []
        first_byte = data_bytes[byte_offset]

        if (first_byte & 0x1F) == 0x1F:
            # Multi-byte tag
            tag_length = 1
            while byte_offset + tag_length < len(data_bytes):
                next_byte = data_bytes[byte_offset + tag_length]
                tag_length += 1
                if (next_byte & 0x80) == 0:
                    break
            else:
                errors.append(
                    ValidationError(
                        code="TRUNCATED_TAG",
                        message=f"Multi-byte tag incomplete at byte {byte_offset}",
                        position=hex_offset,
                        severity="error",
                    )
                )
                return None, 0, errors

            tag = data_bytes[byte_offset : byte_offset + tag_length].hex().upper()
            return tag, tag_length, errors
        else:
            tag = f"{first_byte:02X}"
            return tag, 1, errors

    @staticmethod
    def _parse_length(
        data_bytes: bytes,
        byte_offset: int,
        hex_offset: int,
    ) -> tuple[int | None, int, list]:
        """Parse BER-TLV length bytes."""
        errors = []
        first_byte = data_bytes[byte_offset]

        if first_byte <= 0x7F:
            return first_byte, 1, errors
        elif first_byte == 0x81:
            if byte_offset + 1 >= len(data_bytes):
                errors.append(
                    ValidationError(
                        code="TRUNCATED_LENGTH",
                        message=f"Length byte 0x81 requires 1 more byte at position {byte_offset}",
                        position=hex_offset,
                        severity="error",
                    )
                )
                return None, 0, errors
            length = data_bytes[byte_offset + 1]
            if length <= 0x7F:
                errors.append(
                    ValidationError(
                        code="LONG_FORM_LENGTH",
                        message=f"Length {length} at byte {byte_offset} uses long form unnecessarily",
                        position=hex_offset,
                        severity="warning",
                    )
                )
            return length, 2, errors
        elif first_byte == 0x82:
            if byte_offset + 2 >= len(data_bytes):
                errors.append(
                    ValidationError(
                        code="TRUNCATED_LENGTH",
                        message=f"Length byte 0x82 requires 2 more bytes at position {byte_offset}",
                        position=hex_offset,
                        severity="error",
                    )
                )
                return None, 0, errors
            length = (data_bytes[byte_offset + 1] << 8) | data_bytes[byte_offset + 2]
            if length <= 0x7F:
                errors.append(
                    ValidationError(
                        code="LONG_FORM_LENGTH",
                        message=f"Length {length} at byte {byte_offset} uses long form unnecessarily",
                        position=hex_offset,
                        severity="warning",
                    )
                )
            return length, 3, errors
        elif 0x83 <= first_byte <= 0xFE:
            num_bytes = first_byte - 0x80
            if byte_offset + num_bytes >= len(data_bytes):
                errors.append(
                    ValidationError(
                        code="TRUNCATED_LENGTH",
                        message=f"ZKA extended length (0x{first_byte:02X}) at byte {byte_offset} "
                        f"requires {num_bytes} more bytes",
                        position=hex_offset,
                        severity="error",
                    )
                )
                return None, 0, errors
            length = 0
            for i in range(num_bytes):
                length = (length << 8) | data_bytes[byte_offset + 1 + i]
            return length, 1 + num_bytes, errors
        else:
            errors.append(
                ValidationError(
                    code="INVALID_LENGTH_ENCODING",
                    message=f"Invalid length prefix 0x{first_byte:02X} at byte {byte_offset}",
                    position=hex_offset,
                    severity="error",
                )
            )
            return None, 0, errors

    @staticmethod
    def _count_all(nodes: list):
        """Yield all nodes (both constructed and primitive) recursively."""
        for n in nodes:
            yield n
            if n.get("children"):
                yield from StructureValidator._count_all(n["children"])

    @staticmethod
    def _count_leaves(nodes: list):
        """Yield all leaf (primitive) nodes recursively."""
        for n in nodes:
            if n.get("children"):
                yield from StructureValidator._count_leaves(n["children"])
            else:
                yield n
