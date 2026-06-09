/**
 * Value Decoder Tests
 * 
 * Tests the decoding of EMV tag values to human-readable formats.
 * Each tag type has specific formatting rules based on EMV specifications.
 */

const ValueDecoder = require('../src/decoders/value_decoder');
const BitmaskDecoder = require('../src/decoders/bitmask_decoder');

describe('ValueDecoder', () => {
  describe('decodeValue - PAN (5A)', () => {
    /**
     * Test: Decode PAN (Primary Account Number)
     * 
     * PAN is stored in BCD format, right-padded with F.
     * Output should be masked with spaces every 4 digits.
     */
    test('should decode PAN with F padding', () => {
      // PAN: 4276123456789012 (padded with FF)
      const value = Buffer.from([0x42, 0x76, 0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0xFF, 0xFF]);
      const result = ValueDecoder.decodeValue('5A', value);
      
      expect(result).toBe('4276 1234 5678 9012');
    });

    /**
     * Test: Decode 16-digit PAN
     */
    test('should decode 16-digit PAN', () => {
      // PAN: 1234567890123456
      const value = Buffer.from([0x12, 0x34, 0x56, 0x78, 0x90, 0x12, 0x34, 0x56]);
      const result = ValueDecoder.decodeValue('5A', value);
      
      expect(result).toBe('1234 5678 9012 3456');
    });

    /**
     * Test: Decode 15-digit PAN (Amex)
     */
    test('should decode 15-digit PAN (Amex)', () => {
      // PAN: 378282246310005 (Amex test card)
      const value = Buffer.from([0x37, 0x82, 0x82, 0x24, 0x63, 0x10, 0x00, 0x5F]);
      const result = ValueDecoder.decodeValue('5A', value);
      
      expect(result).toBe('3782 8224 6310 005');
    });
  });

  describe('decodeValue - Expiry Date (5F24)', () => {
    /**
     * Test: Decode expiry date
     * 
     * Format: YYMM in BCD
     * Output: YYYY-MM
     */
    test('should decode expiry date YYMM to YYYY-MM', () => {
      const value = Buffer.from([0x25, 0x12]);  // December 2025
      const result = ValueDecoder.decodeValue('5F24', value);
      
      expect(result).toBe('2025-12');
    });

    /**
     * Test: Decode expiry date in year 2000
     */
    test('should handle year 2000', () => {
      const value = Buffer.from([0x00, 0x01]);  // January 2000
      const result = ValueDecoder.decodeValue('5F24', value);
      
      expect(result).toBe('2000-01');
    });

    /**
     * Test: Decode expiry date in year 2099
     */
    test('should handle year 2099', () => {
      const value = Buffer.from([0x99, 0x12]);  // December 2099
      const result = ValueDecoder.decodeValue('5F24', value);
      
      expect(result).toBe('2099-12');
    });
  });

  describe('decodeValue - Cardholder Name (5F20)', () => {
    /**
     * Test: Decode cardholder name
     * 
     * Stored as ASCII characters.
     */
    test('should decode ASCII cardholder name', () => {
      const value = Buffer.from('JOHN DOE', 'ascii');
      const result = ValueDecoder.decodeValue('5F20', value);
      
      expect(result).toBe('JOHN DOE');
    });

    /**
     * Test: Decode name with special characters
     */
    test('should handle special characters', () => {
      const value = Buffer.from('MÜLLER/SUCCESS', 'utf8');
      const result = ValueDecoder.decodeValue('5F20', value);
      
      expect(result).toBe('MÜLLER/SUCCESS');
    });
  });

  describe('decodeValue - Amount (9F02, 9F03)', () => {
    /**
     * Test: Decode authorized amount
     * 
     * Format: n12 (12 digits) in BCD, representing cents.
     * Output: Decimal string with proper formatting.
     */
    test('should decode BCD amount to decimal string', () => {
      // Amount: 000000010000 = 100.00 EUR
      const value = Buffer.from([0x00, 0x00, 0x00, 0x01, 0x00, 0x00]);
      const result = ValueDecoder.decodeValue('9F02', value);
      
      expect(result).toBe('100.00');
    });

    /**
     * Test: Decode amount with cents
     */
    test('should decode amount with cents', () => {
      // Amount: 000000012345 = 123.45 EUR
      const value = Buffer.from([0x00, 0x00, 0x00, 0x01, 0x23, 0x45]);
      const result = ValueDecoder.decodeValue('9F02', value);
      
      expect(result).toBe('123.45');
    });

    /**
     * Test: Decode zero amount
     */
    test('should decode zero amount', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);
      const result = ValueDecoder.decodeValue('9F02', value);
      
      expect(result).toBe('0.00');
    });

    /**
     * Test: Decode large amount
     */
    test('should decode large amount', () => {
      // Amount: 999999999999 = 9999999999.99
      const value = Buffer.from([0x99, 0x99, 0x99, 0x99, 0x99, 0x99]);
      const result = ValueDecoder.decodeValue('9F02', value);
      
      expect(result).toBe('9999999999.99');
    });

    /**
     * Test: Decode 9F03 (Amount Other)
     */
    test('should decode 9F03 amount other', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x50, 0x00]);
      const result = ValueDecoder.decodeValue('9F03', value);
      
      expect(result).toBe('50.00');
    });
  });

  describe('decodeValue - Transaction Date (9A)', () => {
    /**
     * Test: Decode transaction date
     * 
     * Format: YYMMDD in BCD
     * Output: YYYY-MM-DD
     */
    test('should decode BCD date to YYYY-MM-DD', () => {
      const value = Buffer.from([0x21, 0x03, 0x15]);  // March 15, 2021
      const result = ValueDecoder.decodeValue('9A', value);
      
      expect(result).toBe('2021-03-15');
    });

    /**
     * Test: Decode date in year 2000
     */
    test('should handle year 2000', () => {
      const value = Buffer.from([0x00, 0x01, 0x01]);  // January 1, 2000
      const result = ValueDecoder.decodeValue('9A', value);
      
      expect(result).toBe('2000-01-01');
    });

    /**
     * Test: Decode date in 2099
     */
    test('should handle year 2099', () => {
      const value = Buffer.from([0x99, 0x12, 0x31]);  // December 31, 2099
      const result = ValueDecoder.decodeValue('9A', value);
      
      expect(result).toBe('2099-12-31');
    });
  });

  describe('decodeValue - Cryptogram Type (9F27)', () => {
    /**
     * Test: Decode cryptogram type
     * 
     * 00 = AAC (Transaction Declined)
     * 01 = TC (Transaction Approved)
     * 10 = ARQC (Authorization Request)
     */
    test('should decode AAC (00)', () => {
      const value = Buffer.from([0x00]);
      const result = ValueDecoder.decodeValue('9F27', value);
      
      expect(result).toBe('AAC (Transaction Declined)');
    });

    test('should decode TC (01)', () => {
      const value = Buffer.from([0x01]);
      const result = ValueDecoder.decodeValue('9F27', value);
      
      expect(result).toBe('TC (Transaction Approved)');
    });

    test('should decode ARQC (10)', () => {
      const value = Buffer.from([0x10]);
      const result = ValueDecoder.decodeValue('9F27', value);
      
      expect(result).toBe('ARQC (Authorization Request)');
    });

    test('should decode unknown value', () => {
      const value = Buffer.from([0xFF]);
      const result = ValueDecoder.decodeValue('9F27', value);
      
      expect(result).toBe('Unknown (FF)');
    });
  });

  describe('decodeValue - CVM Results (9F34)', () => {
    /**
     * Test: Decode CVM (Cardholder Verification Method) results
     * 
     * 3 bytes:
     * - Byte 1: CVM performed
     * - Byte 2: CVM condition
     * - Byte 3: CVM result
     */
    test('should decode CVM results - PIN verified', () => {
      const value = Buffer.from([0x41, 0x00, 0x00]);  // PIN verified successfully
      const result = ValueDecoder.decodeValue('9F34', value);
      
      expect(result).toContain('PIN');
      expect(result).toContain('successful');
    });

    test('should decode CVM results - Signature', () => {
      const value = Buffer.from([0x1E, 0x00, 0x00]);  // Signature required
      const result = ValueDecoder.decodeValue('9F34', value);
      
      expect(result).toContain('Signature');
    });

    test('should decode CVM results - No CVM', () => {
      const value = Buffer.from([0x1F, 0x00, 0x00]);  // No CVM performed
      const result = ValueDecoder.decodeValue('9F34', value);
      
      expect(result).toContain('No CVM');
    });
  });

  describe('decodeValue - Country Codes (9F1A, 5F28)', () => {
    /**
     * Test: Decode ISO country code
     * 
     * Format: 2-byte BCD numeric country code.
     * Output: Country name.
     */
    test('should decode country code 040 (Austria)', () => {
      const value = Buffer.from([0x04, 0x00]);
      const result = ValueDecoder.decodeValue('9F1A', value);
      
      expect(result).toBe('Austria (040)');
    });

    test('should decode country code 280 (Germany)', () => {
      const value = Buffer.from([0x28, 0x00]);
      const result = ValueDecoder.decodeValue('9F1A', value);
      
      expect(result).toBe('Germany (280)');
    });

    test('should decode country code 840 (USA)', () => {
      const value = Buffer.from([0x84, 0x00]);
      const result = ValueDecoder.decodeValue('9F1A', value);
      
      expect(result).toBe('United States (840)');
    });

    test('should decode issuer country code (5F28)', () => {
      const value = Buffer.from([0x28, 0x00]);
      const result = ValueDecoder.decodeValue('5F28', value);
      
      expect(result).toBe('Germany (280)');
    });
  });

  describe('decodeValue - Currency Code (49)', () => {
    /**
     * Test: Decode transaction currency code
     * 
     * Format: 2-byte BCD ISO 4217 currency code.
     * Output: Currency name and code.
     */
    test('should decode currency 978 (EUR)', () => {
      const value = Buffer.from([0x97, 0x80]);
      const result = ValueDecoder.decodeValue('49', value);
      
      expect(result).toBe('EUR (978)');
    });

    test('should decode currency 840 (USD)', () => {
      const value = Buffer.from([0x84, 0x00]);
      const result = ValueDecoder.decodeValue('49', value);
      
      expect(result).toBe('USD (840)');
    });

    test('should decode currency 826 (GBP)', () => {
      const value = Buffer.from([0x82, 0x60]);
      const result = ValueDecoder.decodeValue('49', value);
      
      expect(result).toBe('GBP (826)');
    });
  });

  describe('decodeValue - Fallback to hex', () => {
    /**
     * Test: Unknown tags return uppercase hex string
     */
    test('should return hex string for unknown tag', () => {
      const value = Buffer.from([0xAB, 0xCD, 0xEF]);
      const result = ValueDecoder.decodeValue('FFFF', value);
      
      expect(result).toBe('ABCDEF');
    });

    test('should return hex string for unrecognized tag', () => {
      const value = Buffer.from([0x12, 0x34]);
      const result = ValueDecoder.decodeValue('9999', value);
      
      expect(result).toBe('1234');
    });
  });
});


describe('BitmaskDecoder', () => {
  describe('decodeBitmask - TVR (95)', () => {
    /**
     * Test: Decode TVR (Terminal Verification Results)
     * 
     * TVR is 5 bytes, each bit indicates a specific check result.
     * All bits set to 1 means the check failed/was not performed.
     */
    test('should decode TVR with all bits set', () => {
      const value = Buffer.from([0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      expect(result.length).toBeGreaterThan(0);
      expect(result.every(b => b.set === true)).toBe(true);
    });

    /**
     * Test: Decode TVR with no bits set
     */
    test('should decode TVR with no bits set', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      expect(result.length).toBeGreaterThan(0);
      expect(result.every(b => b.set === false)).toBe(true);
    });

    /**
     * Test: Decode TVR byte 1 - Offline data authentication not performed
     */
    test('should decode TVR byte 1 bit 8', () => {
      const value = Buffer.from([0x80, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      const bit = result.find(b => b.byte === 0 && b.mask === 0x80);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
      expect(bit.name).toContain('Offline data authentication');
    });

    /**
     * Test: Decode TVR byte 2 - Cardholder verification not successful
     */
    test('should decode TVR byte 2 bit 8', () => {
      const value = Buffer.from([0x00, 0x80, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      const bit = result.find(b => b.byte === 1 && b.mask === 0x80);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });

    /**
     * Test: Decode TVR byte 5 - Relay resistance threshold exceeded
     */
    test('should decode TVR byte 5 bit 8', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x80]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      const bit = result.find(b => b.byte === 4 && b.mask === 0x80);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
      expect(bit.name).toContain('Relay resistance');
    });

    /**
     * Test: Decode TVR return structure
     */
    test('should return correct structure', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      
      result.forEach(bit => {
        expect(bit).toHaveProperty('byte');
        expect(bit).toHaveProperty('mask');
        expect(bit).toHaveProperty('name');
        expect(bit).toHaveProperty('set');
        expect(typeof bit.byte).toBe('number');
        expect(typeof bit.mask).toBe('number');
        expect(typeof bit.name).toBe('string');
        expect(typeof bit.set).toBe('boolean');
      });
    });
  });

  describe('decodeBitmask - Terminal Capabilities (9F33)', () => {
    /**
     * Test: Decode Terminal Capabilities
     * 
     * 3 bytes defining terminal's capabilities.
     */
    test('should decode Terminal Capabilities', () => {
      const value = Buffer.from([0xE0, 0xE8, 0xC8]);
      const result = BitmaskDecoder.decodeBitmask('9F33', value);
      
      expect(result.length).toBeGreaterThan(0);
      const setBits = result.filter(b => b.set === true);
      expect(setBits.length).toBeGreaterThan(0);
    });

    /**
     * Test: Decode manual key entry capability
     */
    test('should decode Manual key entry', () => {
      const value = Buffer.from([0x40, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('9F33', value);
      
      const bit = result.find(b => b.byte === 0 && b.mask === 0x40);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });
  });

  describe('decodeBitmask - Additional Terminal Capabilities (9F40)', () => {
    /**
     * Test: Decode Additional Terminal Capabilities
     * 
     * 5 bytes defining extended terminal capabilities.
     */
    test('should decode Additional Terminal Capabilities', () => {
      const value = Buffer.from([0xF0, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('9F40', value);
      
      expect(result.length).toBeGreaterThan(0);
    });
  });

  describe('decodeBitmask - TAC Default (DF11)', () => {
    /**
     * Test: Decode TAC Default
     * 
     * TAC (Terminal Action Code) defines default actions.
     * 5 bytes, each bit corresponds to an action.
     */
    test('should decode TAC Default', () => {
      const value = Buffer.from([0xF8, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('DF11', value);
      
      expect(result.length).toBeGreaterThan(0);
      
      // Check byte 1 bit 8 (Offline PIN try limit exceeded)
      const bit = result.find(b => b.byte === 0 && b.mask === 0x80);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });

    /**
     * Test: Decode TAC Default with specific pattern
     */
    test('should decode TAC Default transaction not honored', () => {
      // Byte 4 bit 4: Transaction not permitted on card
      const value = Buffer.from([0x00, 0x00, 0x00, 0x08, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('DF11', value);
      
      const bit = result.find(b => b.byte === 3 && b.mask === 0x08);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });
  });

  describe('decodeBitmask - TAC Denial (DF12)', () => {
    /**
     * Test: Decode TAC Denial
     * 
     * Defines conditions that cause transaction denial.
     */
    test('should decode TAC Denial', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('DF12', value);
      
      expect(result.length).toBeGreaterThan(0);
      expect(result.every(b => b.set === false)).toBe(true);
    });

    test('should decode TAC Denial with bits set', () => {
      const value = Buffer.from([0x00, 0x00, 0x00, 0x00, 0x10]);
      const result = BitmaskDecoder.decodeBitmask('DF12', value);
      
      const bit = result.find(b => b.byte === 4 && b.mask === 0x10);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });
  });

  describe('decodeBitmask - TAC Online (DF13)', () => {
    /**
     * Test: Decode TAC Online
     * 
     * Defines conditions that require online authorization.
     */
    test('should decode TAC Online', () => {
      const value = Buffer.from([0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);
      const result = BitmaskDecoder.decodeBitmask('DF13', value);
      
      expect(result.length).toBeGreaterThan(0);
      expect(result.every(b => b.set === true)).toBe(true);
    });

    test('should decode TAC Online selective bits', () => {
      const value = Buffer.from([0x04, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('DF13', value);
      
      // Bit 3 of byte 1: Cardholder verification not successful
      const bit = result.find(b => b.byte === 0 && b.mask === 0x04);
      expect(bit).toBeDefined();
      expect(bit.set).toBe(true);
    });
  });

  describe('decodeBitmask - Unknown tag fallback', () => {
    /**
     * Test: Unknown tag returns empty array
     */
    test('should return empty array for unknown tag', () => {
      const value = Buffer.from([0xFF, 0xFF]);
      const result = BitmaskDecoder.decodeBitmask('9999', value);
      
      expect(result).toEqual([]);
    });
  });

  describe('decodeBitmask - Full TVR specification', () => {
    /**
     * Test: Verify all TVR bits have correct EMV names
     */
    test('should have correct EMV names for TVR byte 1', () => {
      const value = Buffer.from([0xFF, 0x00, 0x00, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      const byte1Bits = result.filter(b => b.byte === 0 && b.set);
      
      expect(byte1Bits.length).toBe(8);
      
      // Check specific bit names
      const bit8 = result.find(b => b.mask === 0x80);
      expect(bit8.name).toContain('Offline data authentication');
      
      const bit7 = result.find(b => b.mask === 0x40);
      expect(bit7.name).toContain('SDA');
      
      const bit1 = result.find(b => b.mask === 0x01);
      expect(bit1.name).toContain('CDA');
    });

    /**
     * Test: Verify TVR byte 3 (transaction risk)
     */
    test('should have correct names for TVR byte 3', () => {
      const value = Buffer.from([0x00, 0x00, 0xFF, 0x00, 0x00]);
      const result = BitmaskDecoder.decodeBitmask('95', value);
      const byte3Bits = result.filter(b => b.byte === 2 && b.set);
      
      expect(byte3Bits.length).toBe(8);
      
      // Lower 3 bits are reserved, should not be in output or marked reserved
      const reservedBits = byte3Bits.filter(b => b.mask < 0x08);
      expect(reservedBits.every(b => b.name.includes('Reserved'))).toBe(true);
    });
  });
});
