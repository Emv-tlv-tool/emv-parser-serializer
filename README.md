# EMV TLV Parser & Serializer 

A Python library for parsing, decoding, and serializing EMV TLV (Tag-Length-Value) data, with first-class support for German payment terminal protocols: **ZVT** transaction messages and **Poseidon** terminal configuration blobs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-pytest-green.svg)](https://docs.pytest.org)

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Supported Formats](#supported-formats)
- [Project Structure](#project-structure)
- [Tag Dictionaries](#tag-dictionaries)
- [Value & Bitmask Decoding](#value--bitmask-decoding)
- [Running Tests](#running-tests)
- [Specification Compliance](#specification-compliance)
- [License](#license)

---

## Features

- **Full BER-TLV parser/serializer** — handles 1- and 2-byte tags, primitive and constructed types, short (1-byte) and long (0x81/0x82) length encodings.
- **Three input modes**:
  - `raw` — pure TLV data (EMVCo / ZKA blobs)
  - `zvt` — ZVT protocol messages with CTRL codes and BMP fields
  - `config` — Poseidon terminal configuration blobs
- **EMVCo + ZKA tag dictionaries** — over 100 known tags with names, descriptions, formats, and source attribution.
- **Human-readable value decoding** — PAN masking, BCD dates, currency/country code lookups, cryptogram types, and more.
- **EMV-spec bitmask decoding** — TVR, TSI, Terminal Capabilities, and TAC tags.
- **Zero external dependencies** — everything implemented from spec, no third-party parsing libraries.
- **Round-trip safe** — `parse → serialize → parse` is byte-identical for any valid input.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/chameauu/emv-tool.git

cd emv-tool

# Install with uv (recommended)
uv sync

```

No runtime dependencies — the library is self-contained.

---

## Quick Start

```python
from emv_tlv import parse, serialize, find_tag, find_all_tags, to_json

# 1. Parse raw EMV TLV from a hex string
tree = parse('9A03210315', 'raw')
print(tree[0])
# {
#   'tag': '9A',
#   'name': 'Transaction Date',
#   'length': 3,
#   'value': '210315',
#   'decoded': '2021-03-15',
#   'is_constructed': False
# }

# 2. Parse a ZVT transaction message from bytes
zvt = parse(data, 'zvt')
print(zvt['ctrl_name'])  # e.g. 'Authorisation'
print(zvt['tlv'])        # EMV TLV extracted from BMP fields

# 3. Parse a Poseidon terminal config blob
config = parse(data, 'config')
print(config.application_configs)  # AID, label, TAC, floor limit, ...
print(config.ca_keys)              # RID, index, modulus, exponent, ...

# 4. Serialize a TLV tree back to hex
hex_str = serialize(tree)
print(hex_str)  # '9A03210315'

# 5. Find a tag by hex value
aid = find_tag(tree, '84')
print(aid)  # {'tag': '84', 'name': 'DF Name', ...}
```

---

## API Reference

### `parse(data, type='raw')`

Parses input data based on the specified type.

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `bytes` \| `str` | Raw bytes or hex-encoded string |
| `type` | `str` | One of `'raw'`, `'zvt'`, or `'config'` (default: `'raw'`) |

**Returns:** `list[dict]` — an enhanced TLV tree with metadata, decoded values, and (for bitmask tags) bit-level breakdown.

**Config mode returns** a list-like object with extra attributes:
- `result.application_configs` — list of app config dicts
- `result.ca_keys` — list of CA key dicts

### `serialize(nodes)`

Serializes one or more TLV nodes back into a hex string.

| Parameter | Type | Description |
|-----------|------|-------------|
| `nodes` | `dict` \| `list[dict]` | A single enhanced node or a list of nodes |

**Returns:** `str` — concatenated hex representation of the TLV tree(s).

### `find_tag(tree, tag_hex)`

Depth-first search returning the first node matching `tag_hex`.

```python
aid = find_tag(tree, '84')
```

### `find_all_tags(tree, tag_hex)`

Depth-first search returning all nodes matching `tag_hex`.

```python
all_amounts = find_all_tags(tree, '9F02')
```

### `decode_node(node)`

Re-decodes a node's value (e.g. after manual modification).

### `to_json(tree)`

Strips a TLV tree down to a clean JSON-friendly shape (tag, name, length, value, decoded, bitmask, children).

### Exposed Internals

For advanced use, the core components are also exported:

```python
from emv_tlv import (
    TLVParser, TLVSerializer, TLVNode,
    ValueDecoder, BitmaskDecoder,
    ZVTAdapter, ConfigAdapter,
    Dictionary,
)
```

---

## Supported Formats

### Raw TLV

Standard BER-TLV as used by EMVCo specifications. Supports:

- 1-byte and 2-byte tags
- Primitive (`0x__`) and constructed (`0x__` with bit 6 set) nodes
- Short (1-byte) lengths
- Long-form lengths prefixed with `0x81` (2 bytes) or `0x82` (3 bytes)
- Automatic skipping of `0x00` and `0xFF` padding bytes

### ZVT Messages

ZVT (Zahlungsverkehrsterminal) is the protocol used by German payment terminals. Supported CTRL codes include:

| CTRL | Name |
|------|------|
| `0601` | Authorisation |
| `060F` | Authorisation Response |
| `061E` | End of Day |
| `060B` | Status Enquiry |
| `068A` | Print Line |
| `8000` | ACK |
| `8400` | Abort |

EMV TLV is automatically extracted from BMP fields (tags `0x9A`, `0xAA`, `0x3B`).

### Poseidon Config Blobs

Pure TLV used to configure Poseidon terminals. Two key templates are recognized:

- **`E0`** — Terminal configuration
- **`E1`** — CA public keys (RID, index, modulus, exponent, checksum)
- **`E2`** — Application configurations (AID, label, TAC Online/Default/Denial, floor limit, terminal capabilities)

---

## Project Structure

```
emv-tool-python/
├── src/
│   ├── emv_tlv/
│   │   ├── __init__.py              # Public API entry point
│   │   ├── core/
│   │   │   ├── tlv_node.py          # TLV node class with tree traversal
│   │   │   ├── tlv_parser.py        # Recursive BER-TLV parser
│   │   │   └── tlv_serializer.py    # Recursive serializer
│   │   ├── dictionaries/
│   │   │   ├── emvco_tags.json      # EMVCo tag reference data
│   │   │   ├── zka_tags.json        # ZKA (German) tag reference data
│   │   │   └── __init__.py          # Merged dictionary + lookup API
│   │   ├── adapters/
│   │   │   ├── zvt_adapter.py       # ZVT protocol parser
│   │   │   └── config_adapter.py    # Poseidon config blob parser
│   │   └── decoders/
│   │       ├── value_decoder.py     # Human-readable value decoding
│   │       └── bitmask_decoder.py   # EMV bitmask spec decoding
│   └── ... (package metadata)
├── tests/
│   ├── test_tlv_node.py             # Node & parser tests
│   ├── test_serializer.py           # Serializer & round-trip tests
│   ├── test_decoder.py              # Value & bitmask decoder tests
│   ├── test_zvt.py                  # ZVT adapter tests
│   ├── test_config.py               # Config adapter tests
│   └── test_api.py                  # Public API integration tests
├── pyproject.toml
└── README.md
```

---

## Tag Dictionaries

The library ships with reference data for **EMVCo** (Book 3, Book 4) and **ZKA** (Zentraler Kreditausschuss) tags. Each entry contains:

| Field | Description |
|-------|-------------|
| `name` | Short human-readable name |
| `description` | Long-form description |
| `source` | `'EMVCo'`, `'ZKA'`, etc. |
| `format` | `'numeric'`, `'bcd'`, `'bitmask'`, `'ascii'`, `'binary'`, etc. |
| `minLength` / `maxLength` | Length constraints |
| `constructed` | Whether the tag contains nested TLV |

**Lookup API:**

```python
from emv_tlv.dictionaries import Dictionary

Dictionary.lookup_by_tag('9A')   # {'name': 'Transaction Date', ...}
Dictionary.lookup_by_name('PAN') # {'tag': '5A', ...}
```

---

## Value & Bitmask Decoding

### Value Decoding

The `ValueDecoder` knows how to render specific tags as human-readable strings:

| Tag | Decoded as |
|-----|------------|
| `5A` | PAN, masked with spaces (`XXXX XXXX XXXX 1234`) |
| `5F24` | Expiry date `YYMM` → `YYYY-MM` |
| `5F20` | ASCII cardholder name |
| `9F02`, `9F03` | BCD amount → decimal string |
| `9A` | BCD date → `YYYY-MM-DD` |
| `9F27` | Cryptogram type (`AAC` / `TC` / `ARQC`) |
| `9F34` | CVM results (3-byte decoded form) |
| `9F1A`, `5F28` | ISO country code → country name |
| `49` | Currency code → ISO currency name |

Unknown tags fall back to an uppercase hex string.

### Bitmask Decoding

The `BitmaskDecoder` provides per-bit decoding for tags whose `format` is `bitmask`. It uses a **dual-source approach**:

1. **Dictionary metadata** — checks for a `bytes` array in the tag's JSON dictionary entry. If found, uses those bit-level definitions (supports ZKA tags like `DF07`, `DF11`–`DF13`, `DF27`, `DF28`, `DF2A`, and many more).
2. **Hardcoded fallback** — EMV-spec compliant definitions for core tags:
   - `95` — Terminal Verification Results (TVR)
   - `9B` — Transaction Status Information (TSI)
   - `9F33` — Terminal Capabilities
   - `9F40` — Additional Terminal Capabilities
   - `DF11`, `DF12`, `DF13` — TAC Online / Default / Denial

Each bit is returned as `{byte, bit, mask, name, set}`:

```python
[
    {'byte': 2, 'bit': 8, 'mask': 0x80, 'name': 'Plaintext PIN for ICC verification', 'set': True},
    {'byte': 2, 'bit': 7, 'mask': 0x40, 'name': 'Enciphered PIN for online verification', 'set': False},
    {'byte': 3, 'bit': 8, 'mask': 0x80, 'name': 'SDA', 'set': True},
]
```

**Usage:**

```python
from emv_tlv import parse
from emv_tlv.decoders.bitmask_decoder import BitmaskDecoder

# Automatic: parse detects 'bitmask' format and decodes inline
tree = parse("9F330360F8C8", "raw")
print(tree[0]["bitmask"])
# [{'byte': 1, 'bit': 7, 'mask': 0x40, 'name': 'Magnetic stripe', 'set': True}, ...]

# Manual: decode any tag with dictionary bit definitions
bits = BitmaskDecoder.decode_bitmask("DF27", bytes.fromhex("20F0C8"))
for b in bits:
    if b["set"]:
        print(f"  Byte {b['byte']+1}, Bit {b['bit']}: {b['name']}")
```

### Tree Output With Bitmask Visualization

The `parser/parse_tree.py` script generates a visual tree with per-byte bitmask details:

```
+--+ 9F33 (EMVCO_TERMINAL_CAPABILITIES, len=0x03) value="60F8C8"
    +--+ Byte 1 (60)
    |  +--+  Bit 7 (Mask 0x40, value 0x40) --> Magnetic stripe
    |  +--+  Bit 6 (Mask 0x20, value 0x20) --> IC with contacts
    +--+ Byte 2 (F8)
    |  +--+  Bit 8 (Mask 0x80, value 0x80) --> Plaintext PIN for ICC verification
    |  +--+  Bit 7 (Mask 0x40, value 0x40) --> Enciphered PIN for online verification
    |  +--+  Bit 5 (Mask 0x10, value 0x10) --> Enciphered PIN for offline verification
    +--+ Byte 3 (C8)
       +--+  Bit 8 (Mask 0x80, value 0x80) --> SDA
       +--+  Bit 7 (Mask 0x40, value 0x40) --> DDA
       +--+  Bit 4 (Mask 0x08, value 0x08) --> CDA
```

Run the tree generator:
```bash
cd parser && python parse_tree.py
```

---

## Running Tests

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Quick mode
uv run pytest -q

# Run specific test file
uv run pytest tests/test_tlv_node.py

# Run specific test class
uv run pytest tests/test_tlv_node.py::TestTLVParserPadding
```

The test suite covers:

- Parser correctness (single, nested, constructed, long-form lengths, padding)
- Serializer correctness and round-trip integrity
- ZVT message parsing for all supported CTRL codes
- Poseidon config blob template extraction
- Value decoder accuracy (PAN, dates, amounts, cryptograms, ISO codes)
- Bitmask decoder accuracy (TVR, TSI, TAC, Terminal Capabilities)

---

## Specification Compliance

- **EMVCo 4.3** — Book 3 (Application Specification) and Book 4.3 (Terminal Specification) tag definitions.
- **ISO/IEC 7816-4** — BER-TLV encoding (tag octets, length octets, padding).
- **ZKA TA 7.1 / 7.2** — German terminal specification for tags in the `DF__` / `E_` range.
- **ZVT 13.02** — German payment terminal protocol (relevant CTRL codes and BMP structure).

---

## License

[MIT](https://opensource.org/licenses/MIT) — see [`pyproject.toml`](./pyproject.toml).

Originally developed as part of [emv-tools](https://github.com/lumag/emv-tools). Python port from the JavaScript version.