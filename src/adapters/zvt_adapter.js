/**
 * ZVT Adapter - Parses ZVT (ZahlVerkehrsTerminal) messages
 * 
 * ZVT is the protocol used in German payment terminals.
 * 
 * Message Structure:
 * - CTRL (2 bytes): Message type/command code
 * - Length (1-3 bytes): Payload length
 *   - 0x00-0xFE: Direct length value
 *   - 0xFF: Extended length (next 2 bytes)
 * - BMP Fields: Tag-Length-Value encoded data
 *   - Each BMP field: 1-byte tag, 1-byte length, variable value
 * 
 * EMV TLV data is embedded in BMP tags:
 * - 0x9A: Transaction-related EMV data
 * - 0xAA: Additional EMV data
 * - 0x3B: Card-related EMV data
 */

const TLVParser = require('../core/tlv_parser');

// ZVT CTRL codes
const CTRL_CODES = {
  '0601': 'Authorisation',
  '060F': 'Authorisation Response',
  '061E': 'End of Day',
  '060B': 'Status Enquiry',
  '068A': 'Print Line',
  '8000': 'ACK',
  '8400': 'Abort',
};

// BMP tags that contain EMV TLV data
const EMV_BMP_TAGS = [0x9A, 0xAA, 0x3B];

class ZVTAdapter {
  /**
   * Parse a ZVT message buffer
   * 
   * @param {Buffer} buffer - Raw ZVT message bytes
   * @returns {Object} Parsed message with ctrl, length, and bmpFields
   */
  static parse(buffer) {
    let offset = 0;

    // Parse CTRL (2 bytes)
    const ctrl = buffer.slice(0, 2).toString('hex').toUpperCase();
    offset += 2;

    // Parse Length (1-3 bytes)
    let length;
    let lengthBytes;
    
    if (buffer[offset] === 0xFF) {
      // Extended length: 0xFF + 2 bytes
      length = (buffer[offset + 1] << 8) | buffer[offset + 2];
      lengthBytes = 3;
    } else {
      // Direct length
      length = buffer[offset];
      lengthBytes = 1;
    }
    offset += lengthBytes;

    // Parse BMP fields
    const bmpFields = [];
    const payloadEnd = offset + length;

    while (offset < payloadEnd) {
      const bmpTag = buffer[offset];
      const bmpLength = buffer[offset + 1];
      offset += 2;

      const bmpValue = buffer.slice(offset, offset + bmpLength);
      offset += bmpLength;

      bmpFields.push({
        tag: bmpTag.toString(16).toUpperCase().padStart(2, '0'),
        length: bmpLength,
        value: bmpValue,
      });
    }

    return {
      ctrl,
      ctrlName: CTRL_CODES[ctrl] || 'Unknown',
      length,
      bmpFields,
    };
  }

  /**
   * Extract EMV TLV data from BMP fields
   * 
   * BMP tags 0x9A, 0xAA, and 0x3B contain EMV TLV data.
   * 
   * @param {Object} message - Parsed ZVT message
   * @returns {TLVNode[]} Array of parsed TLV trees
   */
  static extractEMVTLV(message) {
    const tlvTrees = [];

    for (const bmp of message.bmpFields) {
      const tagValue = parseInt(bmp.tag, 16);
      
      if (EMV_BMP_TAGS.includes(tagValue)) {
        // Parse the BMP value as EMV TLV
        const nodes = TLVParser.parse(bmp.value);
        tlvTrees.push(...nodes);
      }
    }

    return tlvTrees;
  }

  /**
   * Serialize a ZVT message
   * 
   * @param {Object} message - Message object with ctrl and bmpFields
   * @returns {Buffer} Serialized ZVT message
   */
  static serialize(message) {
    const parts = [];

    // CTRL (2 bytes)
    const ctrlBuffer = Buffer.from(message.ctrl, 'hex');
    parts.push(ctrlBuffer);

    // Calculate payload length
    let payloadLength = 0;
    for (const bmp of message.bmpFields) {
      payloadLength += 2 + bmp.value.length; // Tag(1) + Length(1) + Value
    }

    // Length encoding
    let lengthBuffer;
    if (payloadLength <= 0xFE) {
      lengthBuffer = Buffer.from([payloadLength]);
    } else {
      // Extended length
      lengthBuffer = Buffer.from([
        0xFF,
        (payloadLength >> 8) & 0xFF,
        payloadLength & 0xFF,
      ]);
    }
    parts.push(lengthBuffer);

    // BMP fields
    for (const bmp of message.bmpFields) {
      const tagBuffer = Buffer.from([parseInt(bmp.tag, 16)]);
      const lengthBuffer = Buffer.from([bmp.value.length]);
      parts.push(tagBuffer);
      parts.push(lengthBuffer);
      parts.push(bmp.value);
    }

    return Buffer.concat(parts);
  }

  /**
   * Get CTRL code name
   * 
   * @param {string} ctrl - CTRL code in hex
   * @returns {string} CTRL code name
   */
  static getCtrlName(ctrl) {
    return CTRL_CODES[ctrl] || 'Unknown';
  }

  /**
   * Check if BMP tag contains EMV data
   * 
   * @param {string} bmpTag - BMP tag in hex
   * @returns {boolean} True if tag contains EMV data
   */
  static isEMVBmpTag(bmpTag) {
    const tagValue = parseInt(bmpTag, 16);
    return EMV_BMP_TAGS.includes(tagValue);
  }
}

module.exports = ZVTAdapter;
