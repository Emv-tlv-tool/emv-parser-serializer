/**
 * ZVT Adapter Tests
 * 
 * Tests parsing and serialization of ZVT (ZahlVerkehrsTerminal) messages
 * used in German payment terminals.
 * 
 * ZVT Message Structure:
 * - CTRL (2 bytes): Message type identifier
 * - Length (1-3 bytes): Total payload length
 * - BMP Fields: Tag-Length-Value data
 * 
 * EMV TLV data is embedded in BMP tags 0x9A, 0xAA, and 0x3B.
 */

const ZVTAdapter = require('../src/adapters/zvt_adapter');

describe('ZVTAdapter', () => {
  describe('parse - message structure', () => {
    /**
     * Test: Parse ZVT message with CTRL code
     * 
     * CTRL 0601 = Authorisation Request
     */
    test('should parse ZVT message header', () => {
      // CTRL: 0601, Length: 05, BMP: 9A 03 21 03 15
      const buffer = Buffer.from([
        0x06, 0x01,                    // CTRL: Authorisation
        0x05,                          // Length: 5 bytes
        0x9A, 0x03, 0x21, 0x03, 0x15   // BMP: Transaction Date
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('0601');
      expect(message.ctrlName).toBe('Authorisation');
      expect(message.length).toBe(5);
    });

    /**
     * Test: Parse extended length (0xFF prefix)
     * 
     * Length 0xFF indicates extended length follows (2 bytes)
     */
    test('should parse extended length with 0xFF prefix', () => {
      // CTRL: 0601, Extended Length: 0xFF 0x01 0x00 (256 bytes)
      const payload = Buffer.alloc(256, 0x00);
      const buffer = Buffer.concat([
        Buffer.from([0x06, 0x01]),     // CTRL
        Buffer.from([0xFF, 0x01, 0x00]), // Extended length: 256
        payload
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('0601');
      expect(message.length).toBe(256);
    });
  });

  describe('parse - BMP fields', () => {
    /**
     * Test: Parse single BMP field
     * 
     * BMP field: 1-byte tag, 1-byte length, value
     */
    test('should parse single BMP field', () => {
      const buffer = Buffer.from([
        0x06, 0x01,                    // CTRL: Authorisation
        0x05,                          // Length: 5
        0x9A, 0x03, 0x21, 0x03, 0x15   // BMP: Tag 9A, Len 3, Date
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.bmpFields.length).toBe(1);
      expect(message.bmpFields[0].tag).toBe('9A');
      expect(message.bmpFields[0].length).toBe(3);
    });

    /**
     * Test: Parse multiple BMP fields
     */
    test('should parse multiple BMP fields', () => {
      const buffer = Buffer.from([
        0x06, 0x01,                    // CTRL: Authorisation
        0x0B,                          // Length: 11
        0x9A, 0x03, 0x21, 0x03, 0x15,  // BMP 1: Date
        0x82, 0x02, 0x39, 0x00,        // BMP 2: AIP
        0x9F, 0x02, 0x06               // BMP 3: Amount (partial - just header)
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.bmpFields.length).toBe(3);
      expect(message.bmpFields[0].tag).toBe('9A');
      expect(message.bmpFields[1].tag).toBe('82');
      expect(message.bmpFields[2].tag).toBe('9F');
    });
  });

  describe('parse - EMV TLV extraction', () => {
    /**
     * Test: Extract EMV TLV from BMP tag 0x9A
     * 
     * BMP tag 0x9A contains EMV TLV data
     */
    test('should extract EMV TLV from BMP tag 0x9A', () => {
      // EMV TLV nested inside BMP 0x9A
      const emvData = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);
      const buffer = Buffer.from([
        0x06, 0x01,                    // CTRL
        emvData.length + 2,            // Length
        0x9A, emvData.length,          // BMP 0x9A
        ...emvData                     // EMV TLV inside
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      const tlvTrees = ZVTAdapter.extractEMVTLV(message);
      
      expect(tlvTrees.length).toBe(1);
      expect(tlvTrees[0].tag).toBe('9A');
    });

    /**
     * Test: Extract EMV TLV from BMP tag 0xAA
     */
    test('should extract EMV TLV from BMP tag 0xAA', () => {
      const emvData = Buffer.from([0x82, 0x02, 0x39, 0x00]);
      const buffer = Buffer.from([
        0x06, 0x01,
        emvData.length + 2,
        0xAA, emvData.length,
        ...emvData
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      const tlvTrees = ZVTAdapter.extractEMVTLV(message);
      
      expect(tlvTrees.length).toBe(1);
      expect(tlvTrees[0].tag).toBe('82');
    });

    /**
     * Test: Extract EMV TLV from BMP tag 0x3B
     */
    test('should extract EMV TLV from BMP tag 0x3B', () => {
      const emvData = Buffer.from([
        0x6F, 0x08, 0x84, 0x02, 0xA0, 0x00, 0xA5, 0x02, 0x50, 0x00
      ]);
      const buffer = Buffer.from([
        0x06, 0x01,
        emvData.length + 2,
        0x3B, emvData.length,
        ...emvData
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      const tlvTrees = ZVTAdapter.extractEMVTLV(message);
      
      expect(tlvTrees.length).toBe(1);
      expect(tlvTrees[0].tag).toBe('6F');
      expect(tlvTrees[0].children.length).toBe(2);
    });

    /**
     * Test: Extract multiple EMV TLV trees
     */
    test('should extract multiple EMV TLV from different BMP tags', () => {
      const emvData1 = Buffer.from([0x9A, 0x03, 0x21, 0x03, 0x15]);
      const emvData2 = Buffer.from([0x82, 0x02, 0x39, 0x00]);
      
      const buffer = Buffer.from([
        0x06, 0x01,
        emvData1.length + 2 + emvData2.length + 2,
        0x9A, emvData1.length, ...emvData1,
        0xAA, emvData2.length, ...emvData2
      ]);
      
      const message = ZVTAdapter.parse(buffer);
      const tlvTrees = ZVTAdapter.extractEMVTLV(message);
      
      expect(tlvTrees.length).toBe(2);
    });
  });

  describe('parse - CTRL codes', () => {
    /**
     * Test: CTRL 0601 - Authorisation
     */
    test('should identify CTRL 0601 as Authorisation', () => {
      const buffer = Buffer.from([0x06, 0x01, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('0601');
      expect(message.ctrlName).toBe('Authorisation');
    });

    /**
     * Test: CTRL 060F - Authorisation Response
     */
    test('should identify CTRL 060F as Authorisation Response', () => {
      const buffer = Buffer.from([0x06, 0x0F, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('060F');
      expect(message.ctrlName).toBe('Authorisation Response');
    });

    /**
     * Test: CTRL 061E - End of Day
     */
    test('should identify CTRL 061E as End of Day', () => {
      const buffer = Buffer.from([0x06, 0x1E, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('061E');
      expect(message.ctrlName).toBe('End of Day');
    });

    /**
     * Test: CTRL 060B - Status Enquiry
     */
    test('should identify CTRL 060B as Status Enquiry', () => {
      const buffer = Buffer.from([0x06, 0x0B, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('060B');
      expect(message.ctrlName).toBe('Status Enquiry');
    });

    /**
     * Test: CTRL 068A - Print Line
     */
    test('should identify CTRL 068A as Print Line', () => {
      const buffer = Buffer.from([0x06, 0x8A, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('068A');
      expect(message.ctrlName).toBe('Print Line');
    });

    /**
     * Test: CTRL 8000 - ACK
     */
    test('should identify CTRL 8000 as ACK', () => {
      const buffer = Buffer.from([0x80, 0x00, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('8000');
      expect(message.ctrlName).toBe('ACK');
    });

    /**
     * Test: CTRL 8400 - Abort
     */
    test('should identify CTRL 8400 as Abort', () => {
      const buffer = Buffer.from([0x84, 0x00, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('8400');
      expect(message.ctrlName).toBe('Abort');
    });

    /**
     * Test: Unknown CTRL code
     */
    test('should handle unknown CTRL code', () => {
      const buffer = Buffer.from([0xFF, 0xFF, 0x00]);
      const message = ZVTAdapter.parse(buffer);
      
      expect(message.ctrl).toBe('FFFF');
      expect(message.ctrlName).toBe('Unknown');
    });
  });

  describe('serialize', () => {
    /**
     * Test: Serialize ZVT message
     */
    test('should serialize ZVT message with BMP fields', () => {
      const message = {
        ctrl: '0601',
        bmpFields: [
          { tag: '9A', value: Buffer.from([0x21, 0x03, 0x15]) }
        ]
      };
      
      const buffer = ZVTAdapter.serialize(message);
      
      expect(buffer[0]).toBe(0x06);
      expect(buffer[1]).toBe(0x01);
      expect(buffer.length).toBe(5 + 3); // CTRL(2) + Len(1) + BMP(2+3)
    });

    /**
     * Test: Round-trip parse → serialize
     */
    test('should survive round-trip', () => {
      const original = Buffer.from([
        0x06, 0x01, 0x05,
        0x9A, 0x03, 0x21, 0x03, 0x15
      ]);
      
      const message = ZVTAdapter.parse(original);
      const serialized = ZVTAdapter.serialize(message);
      
      expect(serialized).toEqual(original);
    });
  });
});
