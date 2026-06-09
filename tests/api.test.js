/**
 * Public API Tests
 * 
 * Tests the main entry point for the EMV TLV parser library.
 * Provides unified interface for parsing ZVT, config, and raw TLV data.
 */

const EMVTLV = require('../index');

describe('EMVTLV Public API', () => {
  describe('parse - raw TLV', () => {
    /**
     * Test: Parse raw TLV data
     */
    test('should parse raw TLV data', () => {
      const input = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);
      const result = EMVTLV.parse(input, 'raw');
      
      expect(result.length).toBe(1);
      expect(result[0].tag).toBe('9A');
      expect(result[0].name).toBe('Transaction Date');
    });

    /**
     * Test: Parse hex string input
     */
    test('should parse hex string input', () => {
      const result = EMVTLV.parse('9A03210315', 'raw');
      
      expect(result.length).toBe(1);
      expect(result[0].tag).toBe('9A');
    });

    /**
     * Test: Parse with decoded values
     */
    test('should decode values by default', () => {
      const result = EMVTLV.parse('9A03210315', 'raw');
      
      expect(result[0].decoded).toBe('2021-03-15');
    });

    /**
     * Test: Parse constructed tag
     */
    test('should parse constructed tag with children', () => {
      const result = EMVTLV.parse('6F088402A000A5025000', 'raw');
      
      expect(result[0].tag).toBe('6F');
      expect(result[0].name).toBe('FCI Template');
      expect(result[0].children.length).toBe(2);
      expect(result[0].children[0].name).toBe('DF Name');
    });
  });

  describe('parse - ZVT', () => {
    /**
     * Test: Parse ZVT message
     */
    test('should parse ZVT message', () => {
      const input = Buffer.from([
        0x06, 0x01, 0x07,               // CTRL: 0601, length: 7
        0x9A, 0x05, 0x9A, 0x03, 0x21, 0x03, 0x15  // BMP: tag 0x9A, length 5, value = TLV 9A03210315
      ]);
      const result = EMVTLV.parse(input, 'zvt');
      
      expect(result.ctrl).toBe('0601');
      expect(result.ctrlName).toBe('Authorisation');
      expect(result.tlv.length).toBe(1);
      expect(result.tlv[0].tag).toBe('9A');
    });

    /**
     * Test: Parse ZVT with EMV extraction
     */
    test('should extract EMV TLV from ZVT', () => {
      const emvData = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);
      const bmpValue = emvData;  // BMP value IS the TLV (tag + length + value = 5 bytes)
      const input = Buffer.concat([
        Buffer.from([0x06, 0x01, bmpValue.length + 2]),  // CTRL + length (BMP tag(1) + BMP length(1) + value)
        Buffer.from([0x9A, bmpValue.length]),  // BMP tag(0x9A), BMP length
        bmpValue
      ]);
      
      const result = EMVTLV.parse(input, 'zvt');
      
      expect(result.tlv.length).toBe(1);
      expect(result.tlv[0].decoded).toBe('2021-03-15');
    });
  });

  describe('parse - config', () => {
    /**
     * Test: Parse Poseidon config blob
     */
    test('should parse config blob', () => {
      const input = Buffer.from([
        0xE0, 0x09,
        0x9F, 0x1A, 0x02, 0x02, 0x80,
        0x9F, 0x35, 0x01, 0x22
      ]);
      const result = EMVTLV.parse(input, 'config');
      
      expect(result.length).toBe(1);
      expect(result[0].tag).toBe('E0');
      expect(result[0].name).toBe('Terminal Configuration');
    });

    /**
     * Test: Get application configs from parsed config
     */
    test('should provide application configs', () => {
      const input = Buffer.concat([
        Buffer.from([
          0xE2, 0x0C,
          0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
          0xDF, 0x04, 0x02, 0x56, 0x49
        ])
      ]);
      
      const result = EMVTLV.parse(input, 'config');
      
      expect(result.applicationConfigs).toBeDefined();
      expect(result.applicationConfigs.length).toBe(1);
      expect(result.applicationConfigs[0].aid).toBe('A000000004');
    });

    /**
     * Test: Get CA keys from parsed config
     */
    test('should provide CA keys', () => {
      const input = Buffer.concat([
        Buffer.from([
          0xE1, 0x08,
          0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04
        ])
      ]);
      
      const result = EMVTLV.parse(input, 'config');
      
      expect(result.caKeys).toBeDefined();
      expect(result.caKeys.length).toBe(1);
      expect(result.caKeys[0].rid).toBe('A000000004');
    });
  });

  describe('serialize', () => {
    /**
     * Test: Serialize TLV nodes
     */
    test('should serialize TLV nodes', () => {
      const input = '9A03210315';
      const parsed = EMVTLV.parse(input, 'raw');
      const serialized = EMVTLV.serialize(parsed);
      
      expect(serialized).toBe(input.toUpperCase());
    });

    /**
     * Test: Serialize constructed nodes
     */
    test('should serialize constructed nodes', () => {
      const input = '6F088402A000A5025000';
      const parsed = EMVTLV.parse(input, 'raw');
      const serialized = EMVTLV.serialize(parsed);
      
      expect(serialized).toBe(input.toUpperCase());
    });

    /**
     * Test: Round-trip consistency
     */
    test('should maintain round-trip consistency', () => {
      const inputs = [
        '9A03210315',
        '6F088402A000A5025000',
        '9F0206000010000000',
        'DF1105F800000000'
      ];
      
      for (const input of inputs) {
        const parsed = EMVTLV.parse(input, 'raw');
        const serialized = EMVTLV.serialize(parsed);
        expect(serialized).toBe(input.toUpperCase());
      }
    });
  });

  describe('findTag', () => {
    /**
     * Test: Find tag in tree
     */
    test('should find tag in tree', () => {
      const input = '6F088402A000A5025000';
      const tree = EMVTLV.parse(input, 'raw');
      const found = EMVTLV.findTag(tree, '84');
      
      expect(found).toBeDefined();
      expect(found.tag).toBe('84');
      expect(found.value).toBe('A000');
    });

    /**
     * Test: Find nested tag
     */
    test('should find nested tag', () => {
      const input = '6F09A507BF0C045002ABCD';
      const tree = EMVTLV.parse(input, 'raw');
      const found = EMVTLV.findTag(tree, '50');
      
      expect(found).toBeDefined();
      expect(found.tag).toBe('50');
    });

    /**
     * Test: Return undefined for missing tag
     */
    test('should return undefined for missing tag', () => {
      const input = '6F088402A000A5025000';
      const tree = EMVTLV.parse(input, 'raw');
      const found = EMVTLV.findTag(tree, '9A');
      
      expect(found).toBeUndefined();
    });
  });

  describe('findAllTags', () => {
    /**
     * Test: Find all occurrences of tag
     */
    test('should find all occurrences of tag', () => {
      const input = Buffer.concat([
        Buffer.from([0x9A, 0x01, 0x01]),
        Buffer.from([0x82, 0x01, 0x02]),
        Buffer.from([0x9A, 0x01, 0x03])
      ]);
      const tree = EMVTLV.parse(input, 'raw');
      const found = EMVTLV.findAllTags(tree, '9A');
      
      expect(found.length).toBe(2);
      expect(found[0].value).toBe('01');
      expect(found[1].value).toBe('03');
    });

    /**
     * Test: Find tags in nested structure
     */
    test('should find tags in nested structure', () => {
      // Nested: 6F contains 84 and A5, A5 contains 50
      const input = Buffer.from([
        0x6F, 0x0A,                    // 6F: length 10
        0x84, 0x02, 0xA0, 0x00,        // 84: AID
        0xA5, 0x04,                    // A5: length 4
        0x50, 0x02, 0x56, 0x49         // 50: Label "VI"
      ]);
      const tree = EMVTLV.parse(input, 'raw');
      
      const allNodes = EMVTLV.findAllTags(tree, '50');
      expect(allNodes.length).toBe(1);
      expect(allNodes[0].tag).toBe('50');
    });

    /**
     * Test: Return empty array for missing tag
     */
    test('should return empty array for missing tag', () => {
      const input = '9A03210315';
      const tree = EMVTLV.parse(input, 'raw');
      const found = EMVTLV.findAllTags(tree, '82');
      
      expect(found).toEqual([]);
    });
  });

  describe('decodeNode', () => {
    /**
     * Test: Decode node value
     */
    test('should decode node value', () => {
      const tree = EMVTLV.parse('9A03210315', 'raw');
      const decoded = EMVTLV.decodeNode(tree[0]);
      
      expect(decoded.decoded).toBe('2021-03-15');
    });

    /**
     * Test: Decode PAN
     */
    test('should decode PAN', () => {
      const tree = EMVTLV.parse('5A084276123456789012FFFF', 'raw');
      const decoded = EMVTLV.decodeNode(tree[0]);
      
      expect(decoded.decoded).toBe('4276 1234 5678 9012');
    });

    /**
     * Test: Decode bitmask
     */
    test('should decode TVR bitmask', () => {
      const tree = EMVTLV.parse('95050000000000', 'raw');
      const decoded = EMVTLV.decodeNode(tree[0]);
      
      expect(decoded.bitmask).toBeDefined();
      expect(decoded.bitmask.length).toBeGreaterThan(0);
      expect(decoded.bitmask.every(b => b.set === false)).toBe(true);
    });

    /**
     * Test: Decode TAC bitmask
     */
    test('should decode TAC bitmask', () => {
      const tree = EMVTLV.parse('DF1105F800000000', 'raw');
      const decoded = EMVTLV.decodeNode(tree[0]);
      
      expect(decoded.bitmask).toBeDefined();
      expect(decoded.bitmask.length).toBeGreaterThan(0);
    });
  });

  describe('toJSON', () => {
    /**
     * Test: Convert tree to JSON
     */
    test('should convert tree to JSON', () => {
      const tree = EMVTLV.parse('6F088402A000A5025000', 'raw');
      const json = EMVTLV.toJSON(tree);
      
      expect(Array.isArray(json)).toBe(true);
      expect(json[0].tag).toBe('6F');
      expect(json[0].name).toBe('FCI Template');
      expect(json[0].children).toBeDefined();
    });

    /**
     * Test: JSON includes decoded values
     */
    test('should include decoded values in JSON', () => {
      const tree = EMVTLV.parse('9A03210315', 'raw');
      const json = EMVTLV.toJSON(tree);
      
      expect(json[0].decoded).toBe('2021-03-15');
    });
  });

  describe('error handling', () => {
    /**
     * Test: Handle invalid input type
     */
    test('should throw on invalid input type', () => {
      expect(() => EMVTLV.parse('test', 'invalid')).toThrow('Unknown type');
    });

    /**
     * Test: Handle malformed TLV
     */
    test('should throw on malformed TLV', () => {
      expect(() => EMVTLV.parse('9A05AB', 'raw')).toThrow();
    });

    /**
     * Test: Handle empty input
     */
    test('should handle empty input', () => {
      const result = EMVTLV.parse('', 'raw');
      expect(result).toEqual([]);
    });
  });

  describe('integration', () => {
    /**
     * Test: Full workflow - parse, modify, serialize
     */
    test('should support full workflow', () => {
      // Parse
      const tree = EMVTLV.parse('6F088402A000A5025000', 'raw');
      
      // Find
      const aid = EMVTLV.findTag(tree, '84');
      expect(aid).toBeDefined();
      
      // Serialize
      const serialized = EMVTLV.serialize(tree);
      expect(serialized).toBe('6F088402A000A5025000');
      
      // Re-parse
      const reparsed = EMVTLV.parse(serialized, 'raw');
      expect(reparsed[0].tag).toBe('6F');
    });

    /**
     * Test: Real-world ZVT message
     */
    test('should handle real-world ZVT message', () => {
      // Authorization request with EMV data embedded in BMP fields
      // BMP field 0x9A contains EMV TLV: 82 02 39 00 (AIP) + 50 00 (Label)
      // BMP field 0xAA contains EMV TLV: 9A 03 21 03 15 (Date)
      const tlv1 = Buffer.from([0x82, 0x02, 0x39, 0x00, 0x50, 0x00]);  // 2 TLV nodes
      const tlv2 = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);  // 1 TLV node
      
      const zvtMessage = Buffer.concat([
        Buffer.from([0x06, 0x01]),  // CTRL: Authorisation
        Buffer.from([tlv1.length + 2 + tlv2.length + 2]),  // total payload length
        Buffer.from([0x9A, tlv1.length]),  // BMP tag 0x9A, length = tlv1 bytes
        tlv1,
        Buffer.from([0xAA, tlv2.length]),  // BMP tag 0xAA, length = tlv2 bytes
        tlv2,
      ]);
      
      const result = EMVTLV.parse(zvtMessage, 'zvt');
      
      expect(result.ctrl).toBe('0601');
      expect(result.ctrlName).toBe('Authorisation');
      expect(result.tlv.length).toBe(3);  // 2 + 1 = 3 EMV TLV nodes
    });

    /**
     * Test: Real-world config blob
     */
    test('should handle real-world config blob', () => {
      // Simplified Poseidon config
      const config = Buffer.concat([
        Buffer.from([0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80]),  // Terminal config
        Buffer.from([0xE2, 0x0B, 0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04, 0xDF, 0x04, 0x01, 0x56])  // App config
      ]);
      
      const result = EMVTLV.parse(config, 'config');
      
      expect(result.length).toBe(2);
      expect(result.applicationConfigs.length).toBe(1);
      expect(result.applicationConfigs[0].label).toBe('V');
    });
  });
});
