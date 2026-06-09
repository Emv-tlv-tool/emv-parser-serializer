/**
 * TLV Node Tests
 * 
 * Tests the basic structure and behavior of TLVNode class.
 * TLVNode represents a single Tag-Length-Value element in the EMV hierarchy.
 */

const TLVNode = require('../src/core/tlv_node');
const TLVParser = require('../src/core/tlv_parser');

describe('TLVNode', () => {
  describe('constructor', () => {
    /**
     * Test: Primitive node creation
     * 
     * Primitive nodes contain actual data values (not nested TLV structures).
     * Example: Tag 9A (Transaction Date) with value 0x210315 = March 21, 2015
     */
    test('should create a primitive node', () => {
      const node = new TLVNode('9A', Buffer.from([0x21, 0x03, 0x15]), false);
      
      expect(node.tag).toBe('9A');
      expect(node.length).toBe(3);
      expect(node.value).toEqual(Buffer.from([0x21, 0x03, 0x15]));
      expect(node.isConstructed).toBe(false);
      expect(node.children).toEqual([]);
    });

    /**
     * Test: Constructed node creation
     * 
     * Constructed nodes contain nested TLV structures (children).
     * Example: Tag 6F (FCI Template) contains child elements like 84 (AID) and A5 (FCI Proprietary).
     */
    test('should create a constructed node', () => {
      const node = new TLVNode('6F', Buffer.alloc(0), true);
      
      expect(node.tag).toBe('6F');
      expect(node.isConstructed).toBe(true);
      expect(node.children).toEqual([]);
    });
  });

  describe('addChild', () => {
    /**
     * Test: Adding child to constructed node
     * 
     * Constructed nodes maintain a list of child TLVNode elements.
     * This is essential for representing the tree structure of EMV data.
     */
    test('should add child to constructed node', () => {
      const parent = new TLVNode('6F', Buffer.alloc(0), true);
      const child = new TLVNode('84', Buffer.from([0x01, 0x02]), false);
      
      parent.addChild(child);
      
      expect(parent.children.length).toBe(1);
      expect(parent.children[0]).toBe(child);
    });

    /**
     * Test: Preventing child addition to primitive node
     * 
     * Primitive nodes cannot have children by definition.
     * Attempting to add a child throws an error to enforce EMV spec compliance.
     */
    test('should not add child to primitive node', () => {
      const parent = new TLVNode('9A', Buffer.from([0x21]), false);
      const child = new TLVNode('84', Buffer.from([0x01]), false);
      
      expect(() => parent.addChild(child)).toThrow('Cannot add child to primitive node');
    });
  });

  describe('getChildren', () => {
    /**
     * Test: Retrieve all children
     * 
     * Returns the array of child nodes for tree traversal operations.
     */
    test('should return children array', () => {
      const parent = new TLVNode('6F', Buffer.alloc(0), true);
      const child1 = new TLVNode('84', Buffer.from([0x01]), false);
      const child2 = new TLVNode('A5', Buffer.alloc(0), true);
      
      parent.addChild(child1);
      parent.addChild(child2);
      
      expect(parent.getChildren()).toEqual([child1, child2]);
    });
  });

  describe('isPrimitive', () => {
    /**
     * Test: Check if node is primitive
     * 
     * Helper method to determine if node contains raw data (true) or nested structures (false).
     */
    test('should return true for primitive node', () => {
      const node = new TLVNode('9A', Buffer.from([0x21]), false);
      expect(node.isPrimitive()).toBe(true);
    });

    test('should return false for constructed node', () => {
      const node = new TLVNode('6F', Buffer.alloc(0), true);
      expect(node.isPrimitive()).toBe(false);
    });
  });

  describe('toJSON', () => {
    /**
     * Test: Serialize node to JSON format
     * 
     * Converts the TLVNode to a plain object for output/debugging.
     * Value is converted to uppercase hex string for readability.
     * Children are recursively included if present.
     */
    test('should serialize node to JSON', () => {
      const node = new TLVNode('9A', Buffer.from([0x21, 0x03, 0x15]), false);
      const json = node.toJSON();
      
      expect(json.tag).toBe('9A');
      expect(json.length).toBe(3);
      expect(json.value).toBe('210315');
      expect(json.isConstructed).toBe(false);
    });
  });
});

describe('TLVParser', () => {
  describe('parse - primitive tags', () => {
    /**
     * Test: Parse single-byte tag primitive
     * 
     * Simplest case: 1-byte tag, 1-byte length, value bytes.
     * Tag 9A = Transaction Date with value 210315 (March 21, 2015 in BCD).
     * 
     * Format: [Tag] [Length] [Value bytes...]
     * Bytes:  9A    03       21 03 15
     */
    test('should parse single primitive tag with 1-byte tag', () => {
      const buffer = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[0].length).toBe(3);
      expect(nodes[0].value).toEqual(Buffer.from([0x21, 0x03, 0x15]));
      expect(nodes[0].isConstructed).toBe(false);
    });

    /**
     * Test: Parse tag with minimum length (0)
     * 
     * Some EMV tags can have zero length (e.g., optional indicators).
     */
    test('should parse primitive with zero length', () => {
      const buffer = Buffer.from([0x9A, 0x00]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[0].length).toBe(0);
      expect(nodes[0].value).toEqual(Buffer.alloc(0));
    });

    /**
     * Test: Parse multiple primitive tags sequentially
     * 
     * TLV streams can contain multiple independent tags.
     * Each tag is parsed separately and added to the results array.
     */
    test('should parse multiple primitive tags', () => {
      const buffer = Buffer.from([
        0x9A, 0x03, 0x21, 0x03, 0x15,  // Tag 9A, length 3, date
        0x9F, 0x02, 0x04, 0x00, 0x00, 0x10, 0x00  // Tag 9F02, length 4, amount = 0.40
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(2);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[1].tag).toBe('9F02');
    });

    /**
     * Test: Parse empty buffer
     * 
     * Empty buffer should return empty array (no nodes).
     */
    test('should return empty array for empty buffer', () => {
      const nodes = TLVParser.parse(Buffer.alloc(0));
      expect(nodes).toEqual([]);
    });

    /**
     * Test: Handle insufficient buffer bytes
     * 
     * If buffer ends prematurely, throw error to prevent buffer overruns.
     */
    test('should throw error for truncated value', () => {
      const buffer = Buffer.from([0x9A, 0x05, 0x21, 0x03]);  // Length 5 but only 2 value bytes
      
      expect(() => TLVParser.parse(buffer)).toThrow('Buffer overrun');
    });
  });
});

  describe('parse - constructed tags', () => {
    /**
     * Test: Parse single constructed tag with children
     * 
     * Constructed tags contain nested TLV structures.
     * Tag 6F (FCI Template) is constructed - bit 6 of first byte (0x6F) is set.
     * 
     * Format: [Tag] [Length] [Child TLV structures...]
     * Bytes:  6F    08       84 02 A0 00  A5 02 50 00
     * 
     * Children:
     * - 84 02 A0 00 (AID, length 2)
     * - A5 02 50 00 (FCI Proprietary, length 2, containing 50)
     */
    test('should parse single constructed tag with children', () => {
      // 6F 08 84 02 A0 00 A5 02 50 00
      const buffer = Buffer.from([
        0x6F, 0x08,                    // Tag 6F, length 8
        0x84, 0x02, 0xA0, 0x00,        // Child: Tag 84, length 2, value A0 00
        0xA5, 0x02, 0x50, 0x00         // Child: Tag A5, length 2, containing 50 00
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('6F');
      expect(nodes[0].isConstructed).toBe(true);
      expect(nodes[0].children.length).toBe(2);
      expect(nodes[0].children[0].tag).toBe('84');
      expect(nodes[0].children[1].tag).toBe('A5');
    });

    /**
     * Test: Parse constructed tag with nested children (3 levels)
     * 
     * EMV data often has multiple nesting levels.
     * Example: 6F → A5 → BF0C → children
     * 
     * Hierarchy:
     * 6F (FCI Template)
     *   └── A5 (FCI Proprietary)
     *         └── BF0C (FCI Issuer Discretionary Data)
     *               └── 50 (Label)
     */
    test('should parse 3-level nested constructed tags', () => {
      // 6F 09 A5 07 BF0C 04 50 02 AB CD
      const buffer = Buffer.from([
        0x6F, 0x09,                          // Tag 6F, length 9
        0xA5, 0x07,                          // Tag A5, length 7
        0xBF, 0x0C, 0x04,                    // Tag BF0C (2-byte), length 4
        0x50, 0x02, 0xAB, 0xCD               // Tag 50, length 2, value AB CD
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      const root = nodes[0];
      expect(root.tag).toBe('6F');
      expect(root.children.length).toBe(1);
      
      const level1 = root.children[0];
      expect(level1.tag).toBe('A5');
      expect(level1.children.length).toBe(1);
      
      const level2 = level1.children[0];
      expect(level2.tag).toBe('BF0C');
      expect(level2.children.length).toBe(1);
      
      const level3 = level2.children[0];
      expect(level3.tag).toBe('50');
      expect(level3.isPrimitive()).toBe(true);
    });

    /**
     * Test: Parse constructed with empty children
     * 
     * A constructed tag can have zero-length value (no children).
     */
    test('should parse constructed tag with no children', () => {
      const buffer = Buffer.from([0x6F, 0x00]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('6F');
      expect(nodes[0].isConstructed).toBe(true);
      expect(nodes[0].children.length).toBe(0);
    });

    /**
     * Test: Parse mixed primitive and constructed tags
     * 
     * Real EMV data contains both primitive and constructed tags in sequence.
     */
    test('should parse mixed primitive and constructed tags', () => {
      const buffer = Buffer.from([
        0x9A, 0x03, 0x21, 0x03, 0x15,       // Primitive: Tag 9A, date
        0x6F, 0x05, 0x84, 0x03, 0xA0, 0x00, 0x01,  // Constructed: Tag 6F with child
        0x9F, 0x02, 0x06, 0x00, 0x00, 0x00, 0x10, 0x00, 0x00  // Primitive: Tag 9F02, amount
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(3);
      expect(nodes[0].isPrimitive()).toBe(true);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[1].isConstructed).toBe(true);
      expect(nodes[1].tag).toBe('6F');
      expect(nodes[2].isPrimitive()).toBe(true);
      expect(nodes[2].tag).toBe('9F02');
    });
  });


  describe('parse - 2-byte tags', () => {
    /**
     * Test: Parse 2-byte tag (primitive)
     * 
     * 2-byte tags are used when tag value > 255.
     * Lower 5 bits of first byte = 0x1F indicates second byte follows.
     * 
     * Example: Tag 9F02 (Amount, Authorized)
     * First byte: 0x9F (binary: 10011111, lower 5 bits = 11111 = 0x1F)
     * Second byte: 0x02
     * 
     * Value: 000000100000 (BCD) = 200.00 EUR
     */
    test('should parse 2-byte primitive tag', () => {
      const buffer = Buffer.from([
        0x9F, 0x02, 0x06,              // Tag 9F02 (2-byte), length 6
        0x00, 0x00, 0x00, 0x10, 0x00, 0x00  // Value: 100000 cents
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9F02');
      expect(nodes[0].length).toBe(6);
      expect(nodes[0].isPrimitive()).toBe(true);
    });

    /**
     * Test: Parse 2-byte constructed tag
     * 
     * 2-byte tags can also be constructed (bit 6 of first byte set).
     * Example: BF0C (FCI Issuer Discretionary Data)
     * First byte: 0xBF (binary: 10111111, bit 6 = 1 = constructed, lower 5 bits = 11111)
     * 
     * Hierarchy:
     * BF0C (constructed)
     *   └── 50 (Label)
     */
    test('should parse 2-byte constructed tag', () => {
      const buffer = Buffer.from([
        0xBF, 0x0C, 0x06,              // Tag BF0C (2-byte constructed), length 6
        0x50, 0x04, 0x54, 0x45, 0x53, 0x54  // Child: Tag 50, value "TEST"
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('BF0C');
      expect(nodes[0].isConstructed).toBe(true);
      expect(nodes[0].children.length).toBe(1);
      expect(nodes[0].children[0].tag).toBe('50');
    });

    /**
     * Test: Parse multiple 2-byte tags with different formats
     * 
     * Mix of primitive and constructed 2-byte tags.
     */
    test('should parse multiple 2-byte tags', () => {
      const buffer = Buffer.from([
        0x9F, 0x02, 0x04, 0x00, 0x10, 0x00, 0x00,  // 9F02: Amount
        0x9F, 0x03, 0x04, 0x00, 0x00, 0x00, 0x00,  // 9F03: Amount Other
        0x9F, 0x07, 0x01, 0x01                      // 9F07: Application Usage Control
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(3);
      expect(nodes[0].tag).toBe('9F02');
      expect(nodes[1].tag).toBe('9F03');
      expect(nodes[2].tag).toBe('9F07');
    });

    /**
     * Test: Parse mix of 1-byte and 2-byte tags
     * 
     * Real EMV data combines both tag formats.
     */
    test('should parse mixed 1-byte and 2-byte tags', () => {
      const buffer = Buffer.from([
        0x9A, 0x03, 0x21, 0x03, 0x15,              // 1-byte tag: 9A (date)
        0x9F, 0x02, 0x04, 0x00, 0x10, 0x00, 0x00,  // 2-byte tag: 9F02 (amount)
        0x82, 0x02, 0x39, 0x00                     // 1-byte tag: 82 (AIP)
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(3);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[1].tag).toBe('9F02');
      expect(nodes[2].tag).toBe('82');
    });

    /**
     * Test: Detect constructed flag for 2-byte tag
     * 
     * Bit 6 of first byte determines primitive (0) vs constructed (1).
     * 0x9F = 10011111 → bit 6 = 0 → primitive
     * 0xBF = 10111111 → bit 6 = 1 → constructed
     */
    test('should correctly detect constructed flag for 2-byte tags', () => {
      // Primitive 2-byte tag (9F02)
      const primitiveBuffer = Buffer.from([0x9F, 0x02, 0x01, 0x00]);
      const primitiveNodes = TLVParser.parse(primitiveBuffer);
      expect(primitiveNodes[0].isPrimitive()).toBe(true);

      // Constructed 2-byte tag (BF0C)
      const constructedBuffer = Buffer.from([0xBF, 0x0C, 0x02, 0x50, 0x00]);
      const constructedNodes = TLVParser.parse(constructedBuffer);
      expect(constructedNodes[0].isConstructed).toBe(true);
    });

    /**
     * Test: Parse ZKA-specific 2-byte tags (DFxx series)
     * 
     * German ZKA specifications use DFxx tags for terminal configuration.
     */
    test('should parse ZKA DFxx tags', () => {
      const buffer = Buffer.from([
        0xDF, 0x11, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00,  // DF11: TAC Default
        0xDF, 0x12, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00   // DF12: TAC Denial
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(2);
      expect(nodes[0].tag).toBe('DF11');
      expect(nodes[1].tag).toBe('DF12');
    });
  });


    describe('parse - long-form length', () => {
    /**
     * Test: Parse 2-byte length (0x81 prefix)
     * 
     * Length encoding rules:
     * - 0x00-0x7F: Direct length (1 byte, max 127 bytes)
     * - 0x81 XX: Next byte is length (max 255 bytes)
     * 
     * Example: 0x81 0x80 = 128 bytes length
     */
    test('should parse 2-byte length with 0x81 prefix', () => {
      const valueLength = 128;
      const value = Buffer.alloc(valueLength, 0xAB);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x81, valueLength]),  // Tag 9A, length 128 (2-byte form)
        value
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[0].length).toBe(valueLength);
      expect(nodes[0].value.length).toBe(valueLength);
    });

    /**
     * Test: Parse 2-byte length at boundary (255 bytes)
     * 
     * Maximum value for 0x81 prefix encoding is 255.
     */
    test('should parse 2-byte length at maximum (255)', () => {
      const valueLength = 255;
      const value = Buffer.alloc(valueLength, 0xCD);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x81, valueLength]),  // Tag 9A, length 255
        value
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].length).toBe(valueLength);
    });

    /**
     * Test: Parse 3-byte length (0x82 prefix)
     * 
     * - 0x82 XX YY: Next 2 bytes are length (big-endian, max 65535 bytes)
     * 
     * Example: 0x82 0x01 0x00 = 256 bytes length
     */
    test('should parse 3-byte length with 0x82 prefix', () => {
      const valueLength = 256;
      const value = Buffer.alloc(valueLength, 0xEF);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x82, 0x01, 0x00]),  // Tag 9A, length 256 (3-byte form)
        value
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[0].length).toBe(valueLength);
      expect(nodes[0].value.length).toBe(valueLength);
    });

    /**
     * Test: Parse 3-byte length with large value
     * 
     * Example: 0x82 0x02 0x00 = 512 bytes
     */
    test('should parse 3-byte length with 512 bytes', () => {
      const valueLength = 512;
      const value = Buffer.alloc(valueLength, 0x12);
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x82, 0x02, 0x00]),  // Tag 9A, length 512
        value
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].length).toBe(valueLength);
    });

    /**
     * Test: Parse constructed tag with long-form length
     * 
     * Large constructed tags (e.g., certificate data) use extended length.
     */
    test('should parse constructed tag with long-form length', () => {
      // Create a constructed tag with 128 bytes of children
      const childData = Buffer.concat([
        Buffer.from([0x84, 0x02, 0xA0, 0x00]),  // Child 1: AID
        Buffer.alloc(124, 0x00)                  // Padding to reach 128 bytes
      ]);
      
      const buffer = Buffer.concat([
        Buffer.from([0x6F, 0x81, childData.length]),  // Tag 6F, length 128
        childData
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('6F');
      expect(nodes[0].isConstructed).toBe(true);
      expect(nodes[0].length).toBe(childData.length);
    });

    /**
     * Test: Mix of short and long-form length in same buffer
     * 
     * Real EMV data can mix different length encodings.
     */
    test('should parse mix of short and long-form lengths', () => {
      const buffer = Buffer.concat([
        Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]),  // Short form: 3 bytes
        Buffer.from([0x9F, 0x02, 0x81, 0x80]),        // Long form: 128 bytes
        Buffer.alloc(128, 0x00),
        Buffer.from([0x82, 0x02, 0x39, 0x00])         // Short form: 2 bytes
      ]);
      
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(3);
      expect(nodes[0].length).toBe(3);
      expect(nodes[1].length).toBe(128);
      expect(nodes[2].length).toBe(2);
    });

    /**
     * Test: Verify short-form used for values <= 127
     * 
     * Short form is preferred for small lengths (more compact).
     */
    test('should handle short-form for values under 128', () => {
      const buffer = Buffer.from([0x9A, 0x7F]);  // Length 127 (short form)
      const value = Buffer.alloc(127, 0xAA);
      const fullBuffer = Buffer.concat([buffer, value]);
      
      const nodes = TLVParser.parse(fullBuffer);
      
      expect(nodes[0].length).toBe(127);
    });

    /**
     * Test: Handle length boundary values
     * 
     * Test edge cases: 127 (max short), 128 (min 0x81), 255 (max 0x81), 256 (min 0x82)
     */
    test('should handle length boundary values correctly', () => {
      // 127 bytes (short form)
      const buf127 = Buffer.concat([Buffer.from([0x9A, 0x7F]), Buffer.alloc(127)]);
      expect(TLVParser.parse(buf127)[0].length).toBe(127);

      // 128 bytes (0x81 form)
      const buf128 = Buffer.concat([Buffer.from([0x9A, 0x81, 0x80]), Buffer.alloc(128)]);
      expect(TLVParser.parse(buf128)[0].length).toBe(128);

      // 255 bytes (max 0x81)
      const buf255 = Buffer.concat([Buffer.from([0x9A, 0x81, 0xFF]), Buffer.alloc(255)]);
      expect(TLVParser.parse(buf255)[0].length).toBe(255);

      // 256 bytes (0x82 form)
      const buf256 = Buffer.concat([Buffer.from([0x9A, 0x82, 0x01, 0x00]), Buffer.alloc(256)]);
      expect(TLVParser.parse(buf256)[0].length).toBe(256);
    });
  });

    describe('parse - padding skip', () => {
    /**
     * Test: Skip leading 0x00 padding bytes
     * 
     * EMV data streams may contain 0x00 padding bytes between TLV elements.
     * The parser should ignore these and continue to the next valid tag.
     */
    test('should skip leading 0x00 padding bytes', () => {
      const buffer = Buffer.from([
        0x00, 0x00, 0x00,              // Padding bytes (ignored)
        0x9A, 0x03, 0x21, 0x03, 0x15   // Actual TLV data
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
    });

    /**
     * Test: Skip leading 0xFF padding bytes
     * 
     * 0xFF bytes are also used as padding in some EMV implementations.
     */
    test('should skip leading 0xFF padding bytes', () => {
      const buffer = Buffer.from([
        0xFF, 0xFF,                    // Padding bytes (ignored)
        0x9A, 0x03, 0x21, 0x03, 0x15   // Actual TLV data
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
    });

    /**
     * Test: Skip mixed 0x00 and 0xFF padding
     * 
     * Both padding types can appear in the same stream.
     */
    test('should skip mixed 0x00 and 0xFF padding', () => {
      const buffer = Buffer.from([
        0x00, 0xFF, 0x00, 0xFF,        // Mixed padding
        0x9A, 0x03, 0x21, 0x03, 0x15   // Actual TLV data
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
    });

    /**
     * Test: Skip trailing padding bytes
     * 
     * Padding can appear after the last TLV element.
     */
    test('should skip trailing padding bytes', () => {
      const buffer = Buffer.from([
        0x9A, 0x03, 0x21, 0x03, 0x15,  // TLV data
        0x00, 0x00, 0xFF, 0xFF         // Trailing padding (ignored)
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('9A');
    });

    /**
     * Test: Skip padding between TLV elements
     * 
     * Padding can appear between valid TLV elements.
     */
    test('should skip padding between TLV elements', () => {
      const buffer = Buffer.from([
        0x9A, 0x03, 0x21, 0x03, 0x15,  // First TLV
        0x00, 0xFF, 0x00,              // Padding between
        0x82, 0x02, 0x39, 0x00         // Second TLV
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(2);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[1].tag).toBe('82');
    });

    /**
     * Test: Handle buffer with only padding
     * 
     * A buffer containing only padding should return empty array.
     */
    test('should return empty array for buffer with only padding', () => {
      const buffer = Buffer.from([0x00, 0x00, 0xFF, 0xFF, 0x00]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes).toEqual([]);
    });

    /**
     * Test: Real-world EMV padding scenario
     * 
     * Some card responses include padding for alignment purposes.
     * This simulates a typical PSE response with padding.
     */
    test('should handle real-world padding scenario', () => {
      const buffer = Buffer.from([
        0x6F, 0x0A,                    // FCI Template, length 10
        0x84, 0x04, 0xA0, 0x00, 0x00, 0x01,  // AID child
        0xA5, 0x02, 0x50, 0x00,        // FCI Proprietary child
        0x00, 0x00,                    // Alignment padding
        0xFF, 0xFF,                    // Additional padding
        0x9A, 0x03, 0x21, 0x03, 0x15   // Another TLV after padding
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(2);
      expect(nodes[0].tag).toBe('6F');
      expect(nodes[0].children.length).toBe(2);
      expect(nodes[1].tag).toBe('9A');
    });

    /**
     * Test: Skip padding inside constructed tag value
     * 
     * Padding within a constructed tag's value should be handled
     * by the recursive parsing.
     */
    test('should skip padding inside constructed tag', () => {
      const buffer = Buffer.from([
        0x6F, 0x0C,                    // FCI Template, length 12
        0x84, 0x02, 0xA0, 0x00,        // AID child
        0x00, 0xFF,                    // Padding inside constructed
        0x50, 0x02, 0x54, 0x45,        // Label child "TE"
        0x00, 0x00                     // More padding inside
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(1);
      expect(nodes[0].tag).toBe('6F');
      // Should find 2 children, skipping the padding
      expect(nodes[0].children.length).toBe(2);
      expect(nodes[0].children[0].tag).toBe('84');
      expect(nodes[0].children[1].tag).toBe('50');
    });

    /**
     * Test: Multiple TLV elements with padding in various positions
     * 
     * Comprehensive test covering all padding scenarios.
     */
    test('should parse multiple TLVs with padding everywhere', () => {
      const buffer = Buffer.from([
        0x00,                          // Leading padding
        0x9A, 0x03, 0x21, 0x03, 0x15,  // TLV 1
        0xFF, 0x00,                    // Padding
        0x82, 0x02, 0x39, 0x00,        // TLV 2
        0xFF,                          // Padding
        0x9F, 0x02, 0x04, 0x00, 0x10, 0x00, 0x00,  // TLV 3
        0x00, 0xFF, 0x00               // Trailing padding
      ]);
      const nodes = TLVParser.parse(buffer);
      
      expect(nodes.length).toBe(3);
      expect(nodes[0].tag).toBe('9A');
      expect(nodes[1].tag).toBe('82');
      expect(nodes[2].tag).toBe('9F02');
    });
  });
