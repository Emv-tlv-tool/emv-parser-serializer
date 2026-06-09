// TLV Parser - PASTE YOUR CODE HERE
/**
 * TLVParser - Parses BER-TLV encoded data into TLVNode tree structure
 * 
 * BER-TLV (Basic Encoding Rules - Tag Length Value) is the encoding format
 * used in EMV smart card transactions.
 * 
 * Structure:
 * - Tag: 1 or 2 bytes (lower 5 bits = 0x1F means 2-byte tag)
 * - Length: 1-3 bytes (0x81/0x82 prefix for multi-byte)
 * - Value: Raw data bytes or nested TLV (for constructed tags)
 * 
 * Primitive vs Constructed:
 * - Bit 6 of first tag byte = 1 → Constructed (has children)
 * - Bit 6 of first tag byte = 0 → Primitive (raw data)
 */

const TLVNode = require('./tlv_node');

class TLVParser {
  /**
   * Parse a buffer containing TLV-encoded data
   * 
   * @param {Buffer} buffer - Raw TLV data bytes
   * @returns {TLVNode[]} Array of parsed TLVNode objects
   * @throws {Error} If buffer is malformed or truncated
   */
  static parse(buffer) {
    const nodes = [];
    let offset = 0;

    while (offset < buffer.length) {
      // Skip padding bytes (0x00 and 0xFF)
      if (buffer[offset] === 0x00 || buffer[offset] === 0xFF) {
        offset++;
        continue;
      }

      const node = this.parseNode(buffer, offset);
      nodes.push(node.node);
      offset = node.nextOffset;
    }

    return nodes;
  }

  /**
   * Parse a single TLV node from buffer starting at offset
   * 
   * @param {Buffer} buffer - Source buffer
   * @param {number} offset - Starting position
   * @returns {Object} { node: TLVNode, nextOffset: number }
   * @throws {Error} If insufficient bytes available
   */
  static parseNode(buffer, offset) {
    // Save first byte for constructed detection before offset is modified
    const firstTagByte = buffer[offset];

    // Parse tag (1 or 2 bytes)
    const { tag, tagLength } = this.parseTag(buffer, offset);
    offset += tagLength;

    // Parse length (1-3 bytes)
    const { length, lengthBytes } = this.parseLength(buffer, offset);
    offset += lengthBytes;

    // Check buffer bounds
    if (offset + length > buffer.length) {
      throw new Error('Buffer overrun: insufficient bytes for value');
    }

    // Extract value
    const value = buffer.slice(offset, offset + length);
    offset += length;

    // Determine if constructed (bit 6 of first tag byte)
    const isConstructed = (firstTagByte & 0x20) !== 0;

    // Create node
    const node = new TLVNode(tag, value, isConstructed);

    // Recursively parse children for constructed nodes
    if (isConstructed && length > 0) {
      const children = this.parse(value);
      children.forEach(child => node.addChild(child));
    }

    return { node, nextOffset: offset };
  }

  /**
   * Parse tag bytes from buffer
   * 
   * Tag encoding rules:
   * - If lower 5 bits of first byte are 0x1F, tag is multi-byte
   * - For multi-byte tags, continue reading while bit 8 is set (0x80)
   * - Otherwise, tag is single byte
   * 
   * @param {Buffer} buffer - Source buffer
   * @param {number} offset - Starting position
   * @returns {Object} { tag: string, tagLength: number }
   */
  static parseTag(buffer, offset) {
    if (offset >= buffer.length) {
      throw new Error('Buffer overrun: cannot read tag');
    }

    const firstByte = buffer[offset];
    let tagLength = 1;

    // Check if lower 5 bits are all 1s (0x1F) - indicates multi-byte tag
    if ((firstByte & 0x1F) === 0x1F) {
      // Multi-byte tag: continue reading while bit 8 is set
      while (offset + tagLength < buffer.length) {
        const nextByte = buffer[offset + tagLength];
        tagLength++;
        // If bit 8 is NOT set, this is the last byte
        if ((nextByte & 0x80) === 0) {
          break;
        }
      }
      
      // Check if we have all bytes
      if (offset + tagLength > buffer.length) {
        throw new Error('Buffer overrun: incomplete multi-byte tag');
      }
    }

    const tag = buffer.slice(offset, offset + tagLength).toString('hex').toUpperCase();
    return { tag, tagLength };
  }

  /**
   * Parse length bytes from buffer
   * 
   * Length encoding rules:
   * - 0x00-0x7F: Direct length value (1 byte)
   * - 0x81: Next byte contains length (2 bytes total)
   * - 0x82: Next 2 bytes contain length (3 bytes total)
   * - 0x83-0xFE: ZKA/Poseidon extended forms (lenient mode)
   *   - 0x83: Next 3 bytes contain length (4 bytes total)
   *   - 0x84: Next 4 bytes contain length (5 bytes total)
   *   - etc. (firstByte - 0x80 = number of subsequent length bytes)
   * - 0xFF: Reserved/invalid in standard BER-TLV
   * 
   * @param {Buffer} buffer - Source buffer
   * @param {number} offset - Starting position
   * @param {boolean} lenient - Accept ZKA extended-length forms (default: true)
   * @returns {Object} { length: number, lengthBytes: number }
   */
  static parseLength(buffer, offset, lenient = true) {
    if (offset >= buffer.length) {
      throw new Error('Buffer overrun: cannot read length');
    }

    const firstByte = buffer[offset];
    let length;
    let lengthBytes;

    if (firstByte <= 0x7F) {
      // Short form: length is in first byte
      length = firstByte;
      lengthBytes = 1;
    } else if (firstByte === 0x81) {
      // 2-byte form: next byte is length
      if (offset + 1 >= buffer.length) {
        throw new Error('Buffer overrun: cannot read extended length');
      }
      length = buffer[offset + 1];
      lengthBytes = 2;
    } else if (firstByte === 0x82) {
      // 3-byte form: next 2 bytes are length (big-endian)
      if (offset + 2 >= buffer.length) {
        throw new Error('Buffer overrun: cannot read extended length');
      }
      length = (buffer[offset + 1] << 8) | buffer[offset + 2];
      lengthBytes = 3;
    } else if (lenient && firstByte >= 0x83 && firstByte <= 0xFE) {
      // ZKA/Poseidon extended-length forms
      // Number of subsequent bytes = firstByte - 0x80
      const numBytes = firstByte - 0x80;
      
      if (offset + numBytes + 1 > buffer.length) {
        throw new Error(`Buffer overrun: cannot read ZKA extended length (${numBytes} bytes)`);
      }
      
      // Read length as big-endian
      length = 0;
      for (let i = 0; i < numBytes; i++) {
        length = (length << 8) | buffer[offset + 1 + i];
      }
      lengthBytes = 1 + numBytes;
    } else {
      throw new Error(`Invalid length encoding: 0x${firstByte.toString(16)}`);
    }

    return { length, lengthBytes };
  }
}

module.exports = TLVParser;
