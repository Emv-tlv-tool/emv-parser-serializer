/**
 * Config Adapter Tests
 * 
 * Tests parsing of Poseidon terminal configuration blobs.
 * Poseidon configs are pure TLV with no envelope - parse directly.
 * 
 * Key templates:
 * - E0: Terminal configuration
 * - E1: CA keys per RID
 * - E2: Application configuration per AID
 */

const ConfigAdapter = require('../src/adapters/config_adapter');
const TLVParser = require('../src/core/tlv_parser');

describe('ConfigAdapter', () => {
  describe('parse', () => {
    /**
     * Test: Parse E0 (Terminal Configuration) template
     */
    test('should parse E0 terminal configuration template', () => {
      const buffer = Buffer.from([
        0xE0, 0x09,                    // E0: Terminal Config, length 9
        0x9F, 0x1A, 0x02, 0x02, 0x80,  // Terminal Country Code (Germany)
        0x9F, 0x35, 0x01, 0x22         // Terminal Type
      ]);
      
      const tree = ConfigAdapter.parse(buffer);
      
      expect(tree.length).toBe(1);
      expect(tree[0].tag).toBe('E0');
      expect(tree[0].isConstructed).toBe(true);
    });

    /**
     * Test: Parse E1 (CA Keys) template
     */
    test('should parse E1 CA keys template', () => {
      const buffer = Buffer.from([
        0xE1, 0x0C,                    // E1: CA Keys, length 12
        0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,  // RID (8 bytes)
        0xDF, 0x02, 0x01, 0x01        // CAPK Index (4 bytes)
      ]);
      
      const tree = ConfigAdapter.parse(buffer);
      
      expect(tree.length).toBe(1);
      expect(tree[0].tag).toBe('E1');
      expect(tree[0].children.length).toBe(2);
    });

    /**
     * Test: Parse E2 (Application Configuration) template
     */
    test('should parse E2 application configuration template', () => {
      const buffer = Buffer.from([
        0xE2, 0x13,                    // E2: App Config, length 19
        0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,  // AID
        0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,  // Label "VISA"
        0xDF, 0x11, 0x02, 0xF8, 0x00   // TAC Default
      ]);
      
      const tree = ConfigAdapter.parse(buffer);
      
      expect(tree.length).toBe(1);
      expect(tree[0].tag).toBe('E2');
      expect(tree[0].children.length).toBe(3);
    });

    /**
     * Test: Parse multiple templates
     */
    test('should parse multiple templates in same blob', () => {
      const buffer = Buffer.from([
        0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80,  // E0 template
        0xE1, 0x04, 0xDF, 0x02, 0x01, 0x01,        // E1 template
        0xE2, 0x04, 0x4F, 0x02, 0xA0, 0x00         // E2 template
      ]);
      
      const tree = ConfigAdapter.parse(buffer);
      
      expect(tree.length).toBe(3);
      expect(tree[0].tag).toBe('E0');
      expect(tree[1].tag).toBe('E1');
      expect(tree[2].tag).toBe('E2');
    });
  });

  describe('getApplicationConfigs', () => {
    /**
     * Test: Extract single application configuration
     */
    test('should extract single application config', () => {
      const buffer = Buffer.from([
        0xE2, 0x16,                    // E2: App Config, length 22
        0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,  // AID: A000000004
        0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,  // Label: VISA
        0xDF, 0x11, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00  // TAC Default
      ]);
      
      const tree = TLVParser.parse(buffer);
      const configs = ConfigAdapter.getApplicationConfigs(tree);
      
      expect(configs.length).toBe(1);
      expect(configs[0].aid).toBe('A000000004');
      expect(configs[0].label).toBe('VISA');
    });

    /**
     * Test: Extract multiple application configurations
     */
    test('should extract multiple application configs', () => {
      const buffer = Buffer.concat([
        // App 1: VISA
        Buffer.from([
        0xE2, 0x11,                   // length 17
        0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
        0xDF, 0x04, 0x02, 0x56, 0x49,
        0xDF, 0x11, 0x02, 0xF8, 0x00
        ]),
        // App 2: Mastercard
        Buffer.from([
          0xE2, 0x11,                   // length 17
          0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
          0xDF, 0x04, 0x02, 0x4D, 0x43,
          0xDF, 0x11, 0x02, 0xF8, 0x00
        ])
      ]);
      
      const tree = TLVParser.parse(buffer);
      const configs = ConfigAdapter.getApplicationConfigs(tree);
      
      expect(configs.length).toBe(2);
      expect(configs[0].aid).toBe('A000000004');
      expect(configs[1].aid).toBe('A000000005');
    });

    /**
     * Test: Extract all application config fields
     */
    test('should extract all application config fields', () => {
      const buffer = Buffer.from([
        0xE2, 0x33,                    // E2: App Config, length 51
        0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,  // AID
        0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,  // Label: VISA
        0xDF, 0x11, 0x05, 0xF8, 0x00, 0x00, 0x00, 0x00,  // TAC Default
        0xDF, 0x12, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00,  // TAC Denial
        0xDF, 0x13, 0x05, 0xDC, 0x00, 0x00, 0x00, 0x00,  // TAC Online
        0xDF, 0x05, 0x04, 0x00, 0x10, 0x00, 0x00,  // Floor Limit
        0x9F, 0x33, 0x03, 0xE0, 0xE8, 0xC8       // Terminal Capabilities
      ]);
      
      const tree = TLVParser.parse(buffer);
      const configs = ConfigAdapter.getApplicationConfigs(tree);
      
      expect(configs.length).toBe(1);
      expect(configs[0].aid).toBe('A000000004');
      expect(configs[0].label).toBe('VISA');
      expect(configs[0].tacDefault).toBe('F800000000');
      expect(configs[0].tacDenial).toBe('0000000000');
      expect(configs[0].tacOnline).toBe('DC00000000');
      expect(configs[0].floorLimit).toBeDefined();
      expect(configs[0].terminalCapabilities).toBe('E0E8C8');
    });

    /**
     * Test: Handle missing optional fields
     */
    test('should handle missing optional fields', () => {
      const buffer = Buffer.from([
        0xE2, 0x07,
        0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04  // Only AID
      ]);
      
      const tree = TLVParser.parse(buffer);
      const configs = ConfigAdapter.getApplicationConfigs(tree);
      
      expect(configs.length).toBe(1);
      expect(configs[0].aid).toBe('A000000004');
      expect(configs[0].label).toBeUndefined();
      expect(configs[0].tacDefault).toBeUndefined();
    });
  });

  describe('getCAKeys', () => {
    /**
     * Test: Extract single CA key
     */
    test('should extract single CA key', () => {
      const TLVNode = require('../src/core/tlv_node');
      const tree = [
        (() => {
          const e1 = new TLVNode('E1', Buffer.alloc(0), true);
          e1.addChild(new TLVNode('DF01', Buffer.from([0xA0, 0x00, 0x00, 0x00, 0x04]), false));  // RID
          e1.addChild(new TLVNode('DF02', Buffer.from([0x08]), false));  // Key Index: 8
          e1.addChild(new TLVNode('E6', Buffer.from([0x01, 0x02, 0x03, 0x04, 0x05]), false));  // Modulus
          e1.addChild(new TLVNode('E7', Buffer.from([0x03]), false));  // Exponent
          return e1;
        })()
      ];
      const keys = ConfigAdapter.getCAKeys(tree);
      
      expect(keys.length).toBe(1);
      expect(keys[0].rid).toBe('A000000004');
      expect(keys[0].keyIndex).toBe(8);
      expect(keys[0].modulus).toBe('0102030405');
      expect(keys[0].exponent).toBe('03');
    });

    /**
     * Test: Extract multiple CA keys
     */
    test('should extract multiple CA keys', () => {
      const buffer = Buffer.concat([
        // Key 1: VISA
        Buffer.from([
          0xE1, 0x0C,                   // length 12
          0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
          0xDF, 0x02, 0x01, 0x08
        ]),
        // Key 2: Mastercard
        Buffer.from([
          0xE1, 0x0C,                   // length 12
          0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
          0xDF, 0x02, 0x01, 0x07
        ])
      ]);
      
      const tree = TLVParser.parse(buffer);
      const keys = ConfigAdapter.getCAKeys(tree);
      
      expect(keys.length).toBe(2);
      expect(keys[0].rid).toBe('A000000004');
      expect(keys[1].rid).toBe('A000000005');
    });

    /**
     * Test: Extract CA key with checksum
     */
    test('should extract CA key with checksum', () => {
      const TLVNode = require('../src/core/tlv_node');
      const tree = [
        (() => {
          const e1 = new TLVNode('E1', Buffer.alloc(0), true);
          e1.addChild(new TLVNode('DF01', Buffer.from([0xA0, 0x00, 0x00, 0x00, 0x04]), false));  // RID
          e1.addChild(new TLVNode('DF02', Buffer.from([0x08]), false));  // Key Index
          e1.addChild(new TLVNode('E6', Buffer.from([0xAB]), false));  // Modulus
          e1.addChild(new TLVNode('E7', Buffer.from([0x03]), false));  // Exponent
          e1.addChild(new TLVNode('DF03', Buffer.from([0xCD]), false));  // Checksum
          return e1;
        })()
      ];
      const keys = ConfigAdapter.getCAKeys(tree);
      
      expect(keys[0].checksum).toBe('CD');
    });

    /**
     * Test: Handle missing optional fields
     */
    test('should handle missing CA key optional fields', () => {
      const buffer = Buffer.from([
        0xE1, 0x08,
        0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04  // Only RID (8 bytes)
      ]);
      
      const tree = TLVParser.parse(buffer);
      const keys = ConfigAdapter.getCAKeys(tree);
      
      expect(keys.length).toBe(1);
      expect(keys[0].rid).toBe('A000000004');
      expect(keys[0].keyIndex).toBeUndefined();
      expect(keys[0].modulus).toBeUndefined();
    });
  });

  describe('findTemplate', () => {
    /**
     * Test: Find E0 template
     */
    test('should find E0 terminal configuration template', () => {
      const buffer = Buffer.from([
        0xE1, 0x04, 0xDF, 0x02, 0x01, 0x01,  // E1
        0xE0, 0x05, 0x9F, 0x1A, 0x02, 0x02, 0x80,  // E0
        0xE2, 0x04, 0x4F, 0x02, 0xA0, 0x00   // E2
      ]);
      
      const tree = TLVParser.parse(buffer);
      const e0 = ConfigAdapter.findTemplate(tree, 'E0');
      
      expect(e0).toBeDefined();
      expect(e0.tag).toBe('E0');
    });

    /**
     * Test: Find all E2 templates
     */
    test('should find all E2 templates', () => {
      const buffer = Buffer.concat([
        Buffer.from([0xE2, 0x02, 0x4F, 0x00]),
        Buffer.from([0xE2, 0x02, 0x4F, 0x00]),
        Buffer.from([0xE2, 0x02, 0x4F, 0x00])
      ]);
      
      const tree = TLVParser.parse(buffer);
      const e2s = ConfigAdapter.findAllTemplates(tree, 'E2');
      
      expect(e2s.length).toBe(3);
    });
  });

  describe('Real-world scenario', () => {
    /**
     * Test: Parse complete Poseidon config blob
     */
    test('should parse complete Poseidon configuration', () => {
      // Simplified real-world config structure
      const buffer = Buffer.concat([
        // E0: Terminal Configuration
        Buffer.from([
          0xE0, 0x09,                    // length 9
          0x9F, 0x1A, 0x02, 0x02, 0x80,  // Germany
          0x9F, 0x35, 0x01, 0x22         // Terminal Type
        ]),
        // E1: CA Keys
        Buffer.from([
          0xE1, 0x0C,                    // length 12
          0xDF, 0x01, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
          0xDF, 0x02, 0x01, 0x08
        ]),
        // E2: App Config 1
        Buffer.from([
          0xE2, 0x13,                    // length 19
          0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x04,
          0xDF, 0x04, 0x04, 0x56, 0x49, 0x53, 0x41,
          0xDF, 0x11, 0x02, 0xF8, 0x00
        ]),
        // E2: App Config 2
        Buffer.from([
          0xE2, 0x13,                    // length 19
          0x4F, 0x05, 0xA0, 0x00, 0x00, 0x00, 0x05,
          0xDF, 0x04, 0x04, 0x4D, 0x41, 0x53, 0x54,
          0xDF, 0x11, 0x02, 0xF8, 0x00
        ])
      ]);
      
      const tree = ConfigAdapter.parse(buffer);
      const appConfigs = ConfigAdapter.getApplicationConfigs(tree);
      const caKeys = ConfigAdapter.getCAKeys(tree);
      
      expect(tree.length).toBe(4);
      expect(appConfigs.length).toBe(2);
      expect(caKeys.length).toBe(1);
      
      expect(appConfigs[0].aid).toBe('A000000004');
      expect(appConfigs[0].label).toBe('VISA');
      expect(appConfigs[1].aid).toBe('A000000005');
      expect(appConfigs[1].label).toBe('MAST');
    });
  });
});
