# EMV TLV Parser & Serializer - Development Plan

## Project Overview

Build a JavaScript EMV TLV parser and serializer for German payment terminals handling ZVT transaction messages and Poseidon terminal configuration blobs.

---

## Phase 1: Core TLV Engine

### 1.1 TLV Node Structure
**File**: `src/core/tlv_node.js`
- Define TLV node class with properties: tag, length, value, children, isConstructed
- Add methods for tree traversal (addChild, getChildren, findInChildren)
- Include validation methods (isValidTag, isValidLength)

### 1.2 TLV Parser
**File**: `src/core/tlv_parser.js`
- Implement recursive BER-TLV parser
- Tag parsing: 1 or 2 bytes (check lower 5 bits for 0x1F extension)
- Constructed detection: bit 6 of first tag byte
- Length parsing: 1 byte (≤0x7F), 2 bytes (0x81 prefix), 3 bytes (0x82 prefix)
- Padding skip: ignore 0x00 and 0xFF bytes
- Recursive descent for constructed nodes
- Error handling for buffer overruns, malformed input
- Export `parse(buffer)` returning TLV tree

### 1.3 TLV Serializer
**File**: `src/core/tlv_serializer.js`
- Implement recursive serializer (children before parent)
- Tag encoding: 1 or 2 bytes based on tag value
- Length encoding: shortest valid form
- Constructed nodes: serialize children, compute length, then parent
- Export `serialize(node)` returning hex string

### 1.4 TLV Utilities
**File**: `src/core/tlv_utils.js`
- Hex string ↔ Buffer conversion
- Tag validation helpers
- Length encoding helpers
- Tree traversal utilities (DFS, BFS)
- Buffer bounds checking

---

## Phase 2: Tag Dictionaries

### 2.1 EMVCo Tags Dictionary
**File**: `src/dictionaries/emvco_tags.json`
- Include all required tags: 6F, 84, A5, BF0C, 50, 87, 70, 61, 4F, 57, 5A, 5F24, 5F20, 5F28, 5F2D, 5F30, 5F34, 77, 80, 82, 83, 8C, 8D, 8E, 8F, 90, 92, 93, 94, 95, 9A, 9B, 9C, 9F02, 9F03, 9F06, 9F07, 9F08, 9F09, 9F0D, 9F0E, 9F0F, 9F10, 9F11, 9F12, 9F1A, 9F1E, 9F22, 9F26, 9F27, 9F2D, 9F32, 9F34, 9F35, 9F36, 9F37, 9F38, 9F4D, 9F4E, 9F53, 9F6D, 9F6E
- Each entry: `{ name, description, source, format, minLength, maxLength, constructed }`

### 2.2 ZKA Tags Dictionary
**File**: `src/dictionaries/zka_tags.json`
- Include all required tags: E0, E1, E2, E6, E7, F1, F2, F8, F9, FB, DF01-DF0D, DF11-DF15, DF17-DF19, DF1B-DF1C, DF22-DF23, DF25-DF2A, DF2C, DF2F-DF35, DF38-DF39, DF42, DF46-DF47, DF49, DF4B-DF4C, DF60, DF71, DF7F, DF7A, DF850D, DF8118-DF811D
- Same entry structure as EMVCo

### 2.3 Dictionary Index
**File**: `src/dictionaries/index.js`
- Merge and export both dictionaries
- Provide lookup by tag hex
- Provide lookup by name

---

## Phase 3: Adapters

### 3.1 ZVT Adapter
**File**: `src/adapters/zvt_adapter.js`
- Parse ZVT message structure:
  - 2-byte CTRL code
  - 1-byte or 3-byte length (0xFF prefix = extended)
  - BMP fields
- Parse BMP fields (1-byte tag, 1-byte length, variable value)
- Extract EMV TLV from BMP tags: 0x9A, 0xAA, 0x3B
- Support CTRL codes:
  - 0601: Authorisation
  - 060F: Authorisation Response
  - 061E: End of Day
  - 060B: Status Enquiry
  - 068A: Print Line
  - 8000: ACK
  - 8400: Abort
- Export `parseZVT(buffer)` returning TLV trees
- Export `serializeZVT(nodes)` returning ZVT message buffer

### 3.2 Config Adapter
**File**: `src/adapters/config_adapter.js`
- Parse Poseidon config blobs directly (pure TLV)
- Implement `getApplicationConfigs(tree)`:
  - Find all E2 nodes
  - Extract: AID, label, TAC Online, TAC Default, TAC Denial, floor limit, terminal capabilities
- Implement `getCAKeys(tree)`:
  - Find all E1 nodes
  - Extract: RID, key index, modulus, exponent, checksum
- Handle E0 (terminal config) template

---

## Phase 4: Decoders

### 4.1 Value Decoder
**File**: `src/decoders/value_decoder.js`
- Decode specific tag values:
  - 5A: PAN masked with spaces
  - 5F24: Expiry date YYMM → YYYY-MM
  - 5F20: ASCII cardholder name
  - 9F02/9F03: BCD amount → decimal string
  - 9A: BCD date → YYYY-MM-DD
  - 9F27: Cryptogram type (00=AAC, 01=TC, 10=ARQC)
  - 9F34: CVM results (3 bytes decoded)
  - 9F1A/5F28: ISO country code → name
  - 49: Currency code → ISO name
- Fallback: uppercase hex string for unknown tags
- Export `decodeValue(tag, buffer)` returning string

### 4.2 Bitmask Decoder
**File**: `src/decoders/bitmask_decoder.js`
- Bit-level decoding for:
  - TVR (95)
  - Terminal Capabilities (9F33)
  - Additional Terminal Capabilities (9F40)
  - TAC tags (DF11, DF12, DF13)
- Full EMV bitmask definitions
- Return array of `{ byte, mask, name, set }` objects
- Export `decodeBitmask(tag, buffer)` returning array

---

## Phase 5: Public API

### 5.1 Main Entry Point
**File**: `index.js`
- Export `parse(input, type)`:
  - type: "zvt", "config", or "raw"
  - Returns decoded tree with tag names and human-readable values
- Export `serialize(nodes)`:
  - Returns hex string
- Export `findTag(tree, tagHex)`:
  - DFS search, returns first match
- Export `findAllTags(tree, tagHex)`:
  - DFS search, returns all matches

---

## Phase 6: Tests

### 6.1 Parser Tests
**File**: `tests/parser.test.js`
- Single primitive parse
- Single constructed parse
- 3-level nested parse
- Two-byte tag parse
- Long-form length parse (0x81, 0x82)
- Padding skip (0x00, 0xFF)
- Buffer overrun error handling
- Malformed input error handling

### 6.2 Serializer Tests
**File**: `tests/serializer.test.js`
- Serialize primitive node
- Serialize constructed node with children
- Serialize nested tree
- Length encoding validation
- Round-trip: parse → serialize → parse = byte-identical

### 6.3 ZVT Tests
**File**: `tests/zvt.test.js`
- ZVT message parsing (each CTRL code)
- BMP extraction (tags 9A, AA, 3B)
- Extended length handling
- Round-trip ZVT serialization

### 6.4 Config Tests
**File**: `tests/config.test.js`
- E0/E1/E2 template extraction
- `getApplicationConfigs()` validation
- `getCAKeys()` validation
- Real Poseidon config blob parsing

### 6.5 Decoder Tests
**File**: `tests/decoder.test.js`
- TAC bitmask decoding accuracy
- PAN masking
- Amount BCD decoding
- Date decoding
- Cryptogram type decoding
- Country/currency code lookup

---

## File Structure

```
stage/
├── src/
│   ├── core/
│   │   ├── tlv_node.js
│   │   ├── tlv_parser.js
│   │   ├── tlv_serializer.js
│   │   └── tlv_utils.js
│   ├── dictionaries/
│   │   ├── emvco_tags.json
│   │   ├── zka_tags.json
│   │   └── index.js
│   ├── adapters/
│   │   ├── zvt_adapter.js
│   │   └── config_adapter.js
│   └── decoders/
│       ├── value_decoder.js
│       └── bitmask_decoder.js
├── tests/
│   ├── parser.test.js
│   ├── serializer.test.js
│   ├── zvt.test.js
│   └── config.test.js
├── index.js
├── package.json
└── jest.config.js
```

---

## Acceptance Criteria

- [ ] Parse and serialize are mutual inverses for any valid input
- [ ] All ZKA tags in a real Poseidon config blob parse with correct names
- [ ] TAC bitmask output matches EMV spec definitions
- [ ] All tests pass
- [ ] ZVT messages parse correctly for all supported CTRL codes
- [ ] Config adapter extracts E0/E1/E2 templates correctly
- [ ] Value decoder produces human-readable output for all specified tags
- [ ] Bitmask decoder returns accurate EMV spec bit definitions

---

## Implementation Order

1. Core TLV engine (parser, serializer, node, utils)
2. Tag dictionaries (EMVCo, ZKA)
3. Value and bitmask decoders
4. ZVT adapter
5. Config adapter
6. Public API (index.js)
7. Tests (incrementally with each phase)

---

## Dependencies

- Node.js (LTS version)
- Jest (testing framework)
- No external parsing libraries (implement from scratch per spec)

---

## Notes

- Always encode children before computing parent length during serialization
- Skip 0x00 and 0xFF padding bytes during parsing
- Support both 1-byte and 2-byte tag formats
- Support 1-byte, 2-byte (0x81), and 3-byte (0x82) length encodings
- Use DFS for all tree traversal operations
