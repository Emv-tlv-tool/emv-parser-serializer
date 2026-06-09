/**
 * TLV Serializer Tests
 * 
 * Tests the serialization of TLVNode structures back to raw bytes.
 * Serialization must produce byte-identical output to the original parsed data.
 */
const TLVParser = require('../src/core/tlv_parser');

const TLVNode = require('../src/core/tlv_node');
const TLVSerializer = require('../src/core/tlv_serializer');

describe('TLVSerializer', () => {
  describe('serialize - primitive tags', () => {
    /**
     * Test: Serialize single primitive tag with 1-byte tag
     * 
     * Converts a primitive TLVNode back to raw bytes.
     * Output should match the original TLV encoding.
     */
    test('should serialize single primitive tag', () => {
      const node = new TLVNode('9A', Buffer.from([0x21, 0x03, 0x15]), false);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('9A03210315');
    });

    /**
     * Test: Serialize primitive with zero length
     * 
     * Zero-length values are valid in EMV (optional indicators).
     */
    test('should serialize primitive with zero length', () => {
      const node = new TLVNode('9A', Buffer.alloc(0), false);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('9A00');
    });

    /**
     * Test: Serialize 2-byte primitive tag
     * 
     * Tags like 9F02 require 2 bytes in the output.
     */
    test('should serialize 2-byte primitive tag', () => {
      const node = new TLVNode('9F02', Buffer.from([0x00, 0x10, 0x00, 0x00]), false);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('9F020400100000');
    });

    /**
     * Test: Serialize with short-form length (< 128)
     * 
     * Lengths 0-127 use single-byte encoding.
     */
    test('should use short-form length for values under 128', () => {
      const value = Buffer.alloc(50, 0xAB);
      const node = new TLVNode('9A', value, false);
      const result = TLVSerializer.serialize(node);
      
      // Length byte should be 0x32 (50 decimal)
      expect(result.substring(2, 4)).toBe('32');
      expect(result.length).toBe(2 + 2 + 100); // Tag(2) + Len(2) + Value(100 hex chars)
    });

    /**
     * Test: Serialize with 2-byte length (0x81 prefix)
     * 
     * Lengths 128-255 use 0x81 XX encoding.
     */
    test('should use 0x81 prefix for length 128', () => {
      const value = Buffer.alloc(128, 0xCD);
      const node = new TLVNode('9A', value, false);
      const result = TLVSerializer.serialize(node);
      
      // Should start with 9A 81 80
      expect(result.substring(0, 6)).toBe('9A8180');
    });

    /**
     * Test: Serialize with 2-byte length at maximum (255)
     * 
     * Maximum value for 0x81 prefix is 255 (0xFF).
     */
    test('should use 0x81 prefix for length 255', () => {
      const value = Buffer.alloc(255, 0xEF);
      const node = new TLVNode('9A', value, false);
      const result = TLVSerializer.serialize(node);
      
      expect(result.substring(0, 6)).toBe('9A81FF');
    });

    /**
     * Test: Serialize with 3-byte length (0x82 prefix)
     * 
     * Lengths 256-65535 use 0x82 XX YY encoding.
     */
    test('should use 0x82 prefix for length 256', () => {
      const value = Buffer.alloc(256, 0x12);
      const node = new TLVNode('9A', value, false);
      const result = TLVSerializer.serialize(node);
      
      // Should start with 9A 82 01 00
      expect(result.substring(0, 8)).toBe('9A820100');
    });

    /**
     * Test: Serialize with 3-byte length for larger values
     * 
     * Test 512 bytes (0x0200).
     */
    test('should use 0x82 prefix for length 512', () => {
      const value = Buffer.alloc(512, 0x34);
      const node = new TLVNode('9A', value, false);
      const result = TLVSerializer.serialize(node);
      
      expect(result.substring(0, 8)).toBe('9A820200');
    });

    /**
     * Test: Length encoding boundaries
     * 
     * Verify correct encoding at boundary values:
     * - 127: 0x7F (short form)
     * - 128: 0x81 0x80 (long form)
     * - 255: 0x81 0xFF
     * - 256: 0x82 0x01 0x00
     */
    test('should encode length boundaries correctly', () => {
      // 127 bytes - short form
      const node127 = new TLVNode('9A', Buffer.alloc(127), false);
      expect(TLVSerializer.serialize(node127).substring(0, 4)).toBe('9A7F');

      // 128 bytes - 0x81 form
      const node128 = new TLVNode('9A', Buffer.alloc(128), false);
      expect(TLVSerializer.serialize(node128).substring(0, 6)).toBe('9A8180');

      // 255 bytes - 0x81 max
      const node255 = new TLVNode('9A', Buffer.alloc(255), false);
      expect(TLVSerializer.serialize(node255).substring(0, 6)).toBe('9A81FF');

      // 256 bytes - 0x82 min
      const node256 = new TLVNode('9A', Buffer.alloc(256), false);
      expect(TLVSerializer.serialize(node256).substring(0, 8)).toBe('9A820100');
    });

    /**
     * Test: Serialize ZKA DFxx tags
     * 
     * German ZKA specifications use DFxx tags.
     */
    test('should serialize ZKA DFxx tags', () => {
      const node = new TLVNode('DF11', Buffer.from([0xF8, 0x00, 0x00, 0x00, 0x00]), false);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('DF1105F800000000');
    });

    /**
     * Test: Output is uppercase hex string
     * 
     * All hex output should be uppercase for consistency.
     */
    test('should output uppercase hex string', () => {
      const node = new TLVNode('9A', Buffer.from([0xab, 0xcd, 0xef]), false);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('9A03ABCDEF');
      expect(result).toBe(result.toUpperCase());
    });
  });

  describe('serialize - constructed tags', () => {
    /**
     * Test: Serialize single constructed tag with children
     * 
     * Children are serialized first, then parent length is computed.
     * 
     * Hierarchy:
     * 6F (FCI Template)
     *   ├── 84 (AID)
     *   └── A5 (FCI Proprietary)
     */
    test('should serialize constructed tag with children', () => {
      const parent = new TLVNode('6F', Buffer.alloc(0), true);
      parent.addChild(new TLVNode('84', Buffer.from([0xA0, 0x00]), false));
      parent.addChild(new TLVNode('A5', Buffer.from([0x50, 0x00]), false));
      
      const result = TLVSerializer.serialize(parent);
      
      // Expected: 6F 08 84 02 A0 00 A5 02 50 00
      expect(result).toBe('6F088402A000A5025000');
    });

    /**
     * Test: Serialize nested constructed tags (3 levels)
     * 
     * Deeply nested structures require recursive child serialization.
     * 
     * Hierarchy:
     * 6F
     *   └── A5
     *         └── BF0C
     *               └── 50
     */
    test('should serialize 3-level nested constructed tags', () => {
      const level3 = new TLVNode('50', Buffer.from([0xAB, 0xCD]), false);
      
      const level2 = new TLVNode('BF0C', Buffer.alloc(0), true);
      level2.addChild(level3);
      
      const level1 = new TLVNode('A5', Buffer.alloc(0), true);
      level1.addChild(level2);
      
      const root = new TLVNode('6F', Buffer.alloc(0), true);
      root.addChild(level1);
      
      const result = TLVSerializer.serialize(root);
      
      // Expected: 6F 09 A5 07 BF0C 04 50 02 AB CD
      expect(result).toBe('6F09A507BF0C045002ABCD');
    });

    /**
     * Test: Serialize constructed with 2-byte tag
     * 
     * BF0C is a 2-byte constructed tag.
     */
    test('should serialize 2-byte constructed tag', () => {
      const parent = new TLVNode('BF0C', Buffer.alloc(0), true);
      parent.addChild(new TLVNode('50', Buffer.from([0x54, 0x45, 0x53, 0x54]), false));
      
      const result = TLVSerializer.serialize(parent);
      
      expect(result).toBe('BF0C06500454455354');
    });

    /**
     * Test: Serialize empty constructed tag
     * 
     * Constructed tags can have zero children.
     */
    test('should serialize empty constructed tag', () => {
      const node = new TLVNode('6F', Buffer.alloc(0), true);
      const result = TLVSerializer.serialize(node);
      
      expect(result).toBe('6F00');
    });

    /**
     * Test: Serialize multiple nodes
     * 
     * Multiple top-level nodes can be serialized together.
     */
    test('should serialize multiple nodes', () => {
      const node1 = new TLVNode('9A', Buffer.from([0x21, 0x03, 0x15]), false);
      const node2 = new TLVNode('82', Buffer.from([0x39, 0x00]), false);
      
      const result = TLVSerializer.serializeMultiple([node1, node2]);
      
      expect(result).toBe('9A0321031582023900');
    });
  });

  describe('round-trip parse → serialize → parse', () => {
    /**
     * Test: Round-trip for primitive tag
     * 
     * Parse → Serialize → Parse should produce identical results.
     */
    test('should produce identical output for primitive tag', () => {
      const original = '9A03210315';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip for constructed tag
     * 
     * Complex nested structures must survive round-trip unchanged.
     */
    test('should produce identical output for constructed tag', () => {
      const original = '6F088402A000A5025000';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip for 3-level nested structure
     */
    test('should produce identical output for nested structure', () => {
      const original = '6F09A507BF0C045002ABCD';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip for 2-byte tag
     */
    test('should produce identical output for 2-byte tag', () => {
      const original = '9F0206000010000000';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip for ZKA tag
     */
    test('should produce identical output for ZKA tag', () => {
      const original = 'DF1105F800000000';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip with long-form length (0x81)
     */
    test('should produce identical output with 0x81 length', () => {
      // Create 150-byte value
      const value = Buffer.alloc(150, 0xAB);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x81, 150]),
        value
      ]);
      const original = buffer.toString('hex').toUpperCase();
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip with long-form length (0x82)
     */
    test('should produce identical output with 0x82 length', () => {
      // Create 300-byte value
      const value = Buffer.alloc(300, 0xCD);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x82, 0x01, 0x2C]),
        value
      ]);
      const original = buffer.toString('hex').toUpperCase();
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Round-trip preserves tree structure
     * 
     * After round-trip, the tree structure (parent-child relationships)
     * must be identical.
     */
    test('should preserve tree structure after round-trip', () => {
      const original = '6F0DA507BF0C045002ABCD8402A000';
      const buffer = Buffer.from(original, 'hex');
      
      // Parse
      const nodes1 = TLVParser.parse(buffer);
      
      // Serialize
      const serialized = TLVSerializer.serialize(nodes1[0]);
      
      // Parse again
      const nodes2 = TLVParser.parse(Buffer.from(serialized, 'hex'));
      
      // Compare structure
      expect(nodes2[0].tag).toBe(nodes1[0].tag);
      expect(nodes2[0].children.length).toBe(nodes1[0].children.length);
      expect(nodes2[0].children[0].tag).toBe(nodes1[0].children[0].tag);
    });

    /**
     * Test: Round-trip for complex real-world EMV data
     * 
     * Simulates a realistic FCI template structure.
     */
    test('should handle complex real-world EMV structure', () => {
      // FCI Template with AID, Label, and Priority
      const original = '6F1B8407A0000000041010A510500B5649534120435245444954870101';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
      
      // Verify children parsed correctly
      expect(nodes[0].children.length).toBe(2);
      expect(nodes[0].children[0].tag).toBe('84');  // AID
      expect(nodes[0].children[1].tag).toBe('A5');  // FCI Proprietary
    });

    /**
     * Test: Round-trip for multiple top-level nodes
     */
    test('should handle multiple top-level nodes', () => {
      const original = '9A03210315820239009F0206000010000000';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serializeMultiple(nodes);
      
      expect(serialized).toBe(original);
    });

    /**
     * Test: Verify all parser tests survive round-trip
     * 
     * Any valid parsed data should serialize back to the same bytes.
     */
    test('should handle edge case: empty value', () => {
      const original = '9A00';
      const buffer = Buffer.from(original, 'hex');
      
      const nodes = TLVParser.parse(buffer);
      const serialized = TLVSerializer.serialize(nodes[0]);
      
      expect(serialized).toBe(original);
    });
  });
});
