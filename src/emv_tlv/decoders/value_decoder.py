"""
ValueDecoder - Decodes EMV tag values to human-readable formats.

Each EMV tag has specific encoding rules:
- BCD (Binary Coded Decimal) for numeric values
- ASCII for text values
- Bitmask for flags and options

This module provides tag-specific decoding for common EMV values.
"""

# ISO 3166-1 numeric country codes
_COUNTRY_CODES: dict[str, str] = {
    "040": "Austria",
    "056": "Belgium",
    "250": "France",
    "276": "Germany",
    "280": "Germany",
    "380": "Italy",
    "528": "Netherlands",
    "724": "Spain",
    "826": "United Kingdom",
    "840": "United States",
    "756": "Switzerland",
    "036": "Australia",
    "124": "Canada",
    "392": "Japan",
    "410": "South Korea",
    "156": "China",
    "356": "India",
    "076": "Brazil",
    "643": "Russia",
    "554": "New Zealand",
    "012": "Algeria",
    "484": "Mexico",
    "702": "Singapore",
    "158": "Taiwan",
    "360": "Indonesia",
    "458": "Malaysia",
    "608": "Philippines",
    "764": "Thailand",
    "414": "Kuwait",
    "784": "United Arab Emirates",
    "682": "Saudi Arabia",
    "422": "Lebanon",
    "504": "Morocco",
    "818": "Egypt",
    "710": "South Africa",
    "011": "Benin",
    "204": "Cameroon",
    "388": "Jamaica",
    "591": "Panama",
    "340": "Honduras",
    "188": "Costa Rica",
    "320": "Guatemala",
}

# ISO 4217 currency codes
_CURRENCY_CODES: dict[str, str] = {
    "978": "EUR",
    "840": "USD",
    "826": "GBP",
    "756": "CHF",
    "124": "CAD",
    "036": "AUD",
    "392": "JPY",
    "410": "KRW",
    "156": "CNY",
    "356": "INR",
    "076": "BRL",
    "643": "RUB",
    "554": "NZD",
    "578": "NOK",
    "752": "SEK",
    "208": "DKK",
    "348": "HUF",
    "203": "CZK",
    "616": "PLN",
    "946": "RON",
    "710": "ZAR",
    "818": "EGP",
    "352": "ISK",
    "032": "ARS",
    "152": "CLP",
    "484": "MXN",
    "604": "PEN",
    "170": "COP",
    "986": "BRL",
}

# CVM (Cardholder Verification Method) types
_CVM_TYPES: dict[int, str] = {
    0x00: "No CVM",
    0x01: "Plaintext PIN (ICC verification)",
    0x02: "Enciphered PIN (online)",
    0x1E: "Signature (paper)",
    0x1F: "No CVM required",
    0x41: "Plaintext PIN and signature",
    0x42: "Enciphered PIN and signature",
}


class ValueDecoder:
    """Decodes EMV tag values to human-readable strings."""

    @staticmethod
    def decode_value(tag: str, value: bytes) -> str:
        """
        Decode a tag value to human-readable string.

        Args:
            tag: Tag identifier in uppercase hex
            value: Raw value bytes

        Returns:
            Human-readable representation
        """
        if not value or len(value) == 0:
            return ""

        decoders = {
            "5A": ValueDecoder._decode_pan,
            "5F24": ValueDecoder._decode_expiry_date,
            "5F20": ValueDecoder._decode_ascii,
            "9F02": ValueDecoder._decode_amount,
            "9F03": ValueDecoder._decode_amount,
            "9A": ValueDecoder._decode_date,
            "9F27": ValueDecoder._decode_cryptogram_type,
            "9F34": ValueDecoder._decode_cvm_results,
            "9F1A": ValueDecoder._decode_country_code,
            "5F28": ValueDecoder._decode_country_code,
            "49": ValueDecoder._decode_currency_code,
        }

        decoder = decoders.get(tag)
        if decoder:
            return decoder(value)
        return value.hex().upper()

    @staticmethod
    def _decode_pan(value: bytes) -> str:
        """
        Decode PAN (Primary Account Number).

        BCD format, right-padded with F, masked with spaces every 4 digits.
        """
        pan = ""
        for byte in value:
            high = (byte >> 4) & 0x0F
            low = byte & 0x0F
            if high <= 9:
                pan += str(high)
            if low <= 9:
                pan += str(low)

        # Format with spaces every 4 digits
        groups = [pan[i : i + 4] for i in range(0, len(pan), 4)]
        return " ".join(groups)

    @staticmethod
    def _decode_expiry_date(value: bytes) -> str:
        """Decode expiry date (YYMM -> YYYY-MM)."""
        year = ValueDecoder._bcd_to_number(value[0])
        month = ValueDecoder._bcd_to_number(value[1])
        full_year = 2000 + year
        return f"{full_year}-{month:02d}"

    @staticmethod
    def _decode_ascii(value: bytes) -> str:
        """Decode ASCII text."""
        return value.decode("utf-8").strip()

    @staticmethod
    def _decode_amount(value: bytes) -> str:
        """
        Decode amount (n12 BCD -> decimal string).

        Value represents cents, output in major currency unit.
        """
        amount = ""
        for byte in value:
            amount += str(ValueDecoder._bcd_to_number(byte)).zfill(2)

        cents = int(amount[-2:])
        units = int(amount[:-2]) if amount[:-2] else 0
        return f"{units}.{cents:02d}"

    @staticmethod
    def _decode_date(value: bytes) -> str:
        """Decode transaction date (YYMMDD -> YYYY-MM-DD)."""
        year = ValueDecoder._bcd_to_number(value[0])
        month = ValueDecoder._bcd_to_number(value[1])
        day = ValueDecoder._bcd_to_number(value[2])
        full_year = 2000 + year
        return f"{full_year}-{month:02d}-{day:02d}"

    @staticmethod
    def _decode_cryptogram_type(value: bytes) -> str:
        """Decode cryptogram type."""
        type_byte = value[0]
        types = {
            0x00: "AAC (Transaction Declined)",
            0x01: "TC (Transaction Approved)",
            0x10: "ARQC (Authorization Request)",
        }
        return types.get(type_byte, f"Unknown ({type_byte:02X})")

    @staticmethod
    def _decode_cvm_results(value: bytes) -> str:
        """Decode CVM results (3 bytes)."""
        cvm_type = value[0]
        cvm_result = value[2]

        type_name = _CVM_TYPES.get(
            cvm_type, f"Unknown CVM ({cvm_type:02X})"
        )

        result_text = {
            0x00: "successful",
            0x01: "failed",
        }.get(cvm_result, f"unknown ({cvm_result:02X})")

        return f"{type_name} - {result_text}"

    @staticmethod
    def _decode_country_code(value: bytes) -> str:
        """
        Decode country code.

        2 bytes contain a 3-digit BCD code.
        """
        d0 = (value[0] >> 4) & 0x0F
        d1 = value[0] & 0x0F
        d2 = (value[1] >> 4) & 0x0F
        code_num = d0 * 100 + d1 * 10 + d2
        code = str(code_num).zfill(3)

        name = _COUNTRY_CODES.get(code, "Unknown")
        return f"{name} ({code})"

    @staticmethod
    def _decode_currency_code(value: bytes) -> str:
        """
        Decode currency code.

        2 bytes contain a 3-digit BCD code.
        """
        d0 = (value[0] >> 4) & 0x0F
        d1 = value[0] & 0x0F
        d2 = (value[1] >> 4) & 0x0F
        code_num = d0 * 100 + d1 * 10 + d2
        code = str(code_num).zfill(3)

        name = _CURRENCY_CODES.get(code, "Unknown")
        return f"{name} ({code})"

    @staticmethod
    def _bcd_to_number(byte: int) -> int:
        """Convert BCD byte to number."""
        return ((byte >> 4) & 0x0F) * 10 + (byte & 0x0F)

    @staticmethod
    def to_hex(value: bytes) -> str:
        """Convert bytes to uppercase hex string."""
        return value.hex().upper()