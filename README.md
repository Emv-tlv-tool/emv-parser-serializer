# EMV TLV Parser & Serializer

A JavaScript library for parsing, decoding, and serializing EMV TLV (Tag-Length-Value) data, with first-class support for German payment terminal protocols: **ZVT** transaction messages and **Poseidon** terminal configuration blobs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-LTS-green.svg)](https://nodejs.org)
[![Tests](https://img.shields.io/badge/Tests-Jest-blue.svg)](https://jestjs.io)

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
- [Examples](#examples)
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
git clone https://github.com/lumag/emv-tools.git
cd emv-tools/stage

# Install dev dependencies (Jest)
npm install
```

No runtime dependencies — the library is self-contained.

---

## Quick Start

```javascript
const EMVTLV = require('emv-tlv');

// 1. Parse raw EMV TLV from a hex string
const tree = EMVTLV.parse('9A03210315', 'raw');
console.log(tree[0]);
// {
//   tag: '9A',
//   name: 'Transaction Date',
//   length: 3,
//   value: '210315',
//   decoded: '2021-03-15',
//   isConstructed: false
// }

// 2. Parse a ZVT transaction message from a Buffer
const zvt = EMVTLV.parse(buffer, 'zvt');
console.log(zvt.ctrlName);  // e.g. 'Authorisation'
console.log(zvt.tlv);       // EMV TLV extracted from BMP fields

// 3. Parse a Poseidon terminal config blob
const config = EMVTLV.parse(buffer, 'config');
console.log(config.applicationConfigs);  // AID, label, TAC, floor limit, ...
console.log(config.caKeys);               // RID, index, modulus, exponent, ...

// 4. Serialize a TLV tree back to hex
const hex = EMVTLV.serialize(tree);
console.log(hex);  // '9A03210315'
```

---

## API Reference

### `parse(input, type)`

Parses input data based on the specified type.

| Parameter | Type | Description |
|-----------|------|-------------|
| `input` | `Buffer` \| `string` | Raw bytes or hex-encoded string |
| `type` | `string` | One of `'raw'`, `'zvt'`, or `'config'` (default: `'raw'`) |

**Returns:** `Object` \| `Object[]` — an enhanced TLV tree with metadata, decoded values, and (for bitmask tags) bit-level breakdown.

### `serialize(nodes)`

Serializes one or more TLV nodes back into a hex string.

| Parameter | Type | Description |
|-----------|------|-------------|
| `nodes` | `Object` \| `Object[]` | A single enhanced node or an array of nodes |

**Returns:** `string` — concatenated hex representation of the TLV tree(s).

### `findTag(tree, tagHex)`

Depth-first search returning the first node matching `tagHex`.

```javascript
const aid = EMVTLV.findTag(tree, '84');
```

### `findAllTags(tree, tagHex)`

Depth-first search returning all nodes matching `tagHex`.

```javascript
const allAmounts = EMVTLV.findAllTags(tree, '9F02');
```

### `decodeNode(node)`

Re-decodes a node's value (e.g. after manual modification).

### `toJSON(tree)`

Strips a TLV tree down to a clean JSON-friendly shape (tag, name, length, value, decoded, bitmask, children).

### Exposed Internals

For advanced use, the core components are also exported:

```javascript
const {
  TLVParser, TLVSerializer, TLVNode,
  ValueDecoder, BitmaskDecoder,
  ZVTAdapter, ConfigAdapter,
  Dictionary,
} = require('emv-tlv');
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
stage/
├── src/
│   ├── core/
│   │   ├── tlv_node.js          # TLV node class with tree traversal
│   │   ├── tlv_parser.js        # Recursive BER-TLV parser
│   │   ├── tlv_serializer.js    # Recursive serializer
│   │   └── tlv_utils.js         # Hex/buffer helpers, validation
│   ├── dictionaries/
│   │   ├── emvco_tags.json      # EMVCo tag reference data
│   │   ├── zka_tags.json        # ZKA (German) tag reference data
│   │   └── index.js             # Merged dictionary + lookup API
│   ├── adapters/
│   │   ├── zvt_adapter.js       # ZVT protocol parser
│   │   └── config_adapter.js    # Poseidon config blob parser
│   └── decoders/
│       ├── value_decoder.js     # Human-readable value decoding
│       └── bitmask_decoder.js   # EMV bitmask spec decoding
├── index.js                     # Public API entry point
├── package.json
└── jest.config.js
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

```javascript
const Dictionary = require('emv-tlv/src/dictionaries');

Dictionary.lookupByTag('9A');   // { name: 'Transaction Date', ... }
Dictionary.lookupByName('PAN');  // [{ tag: '5A', ... }]
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

The `BitmaskDecoder` provides EMV-spec-compliant decoding for tags whose `format` is `bitmask`, including:

- `95` — Terminal Verification Results (TVR)
- `9B` — Transaction Status Information (TSI)
- `9F33` — Terminal Capabilities
- `9F40` — Additional Terminal Capabilities
- `DF11`, `DF12`, `DF13` — TAC Online / Default / Denial

Each bit is returned as `{ byte, mask, name, set }`:

```javascript
{
  byte: 1,
  mask: 0x80,
  name: 'Offline data authentication was not performed',
  set: true
}
```

---

## Examples

### Round-trip parse/serialize

```javascript
const original = '6F258407A0000000031010A50F500C56495341204352454449548701015F2D02656E9F1101019F120C564953412052554442454E';
const tree = EMVTLV.parse(original, 'raw');
const hex = EMVTLV.serialize(tree);

console.assert(hex === original);  // byte-identical
```

### Inspect a Poseidon config blob

```javascript
const config = EMVTLV.parse(configBlob, 'config');

for (const app of config.applicationConfigs) {
  console.log(`AID: ${app.aid}, Label: ${app.label}`);
  console.log(`  TAC Online:   ${app.tacOnline}`);
  console.log(`  TAC Default:  ${app.tacDefault}`);
  console.log(`  TAC Denial:   ${app.tacDenial}`);
  console.log(`  Floor limit:  ${app.floorLimit}`);
}

for (const ca of config.caKeys) {
  console.log(`RID: ${ca.rid}, Index: ${ca.keyIndex}`);
  console.log(`  Modulus: ${ca.modulus.length} bytes`);
}
```

### Decode a ZVT authorisation request

```javascript
const zvt = EMVTLV.parse(zvtBuffer, 'zvt');
console.log(`${zvt.ctrlName} (${zvt.ctrl})`);
console.log(`Length: ${zvt.length}, BMP fields: ${zvt.bmpFields.length}`);

for (const node of zvt.tlv) {
  console.log(`  ${node.tag} ${node.name}: ${node.decoded || node.value}`);
}
```

---

## Running Tests

```bash
# Run all tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
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

[MIT](https://opensource.org/licenses/MIT) — see [`package.json`](./package.json).

Originally developed as part of [emv-tools](https://github.com/lumag/emv-tools).
