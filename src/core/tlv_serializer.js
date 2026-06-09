// TLV Serializer - PASTE YOUR CODE HERE
/**
 * TLVSerializer - Serializes TLVNode structures back to BER-TLV encoded bytes
 * 
 * Serialization Rules:
 * 1. Encode tag (1 or 2 bytes based on tag value)
 * 2. Encode length (short form for < 128, long form otherwise)
 * 3. For constructed nodes: serialize children first, then compute parent length
 * 
 * Output is uppercase hex string for readability and interoperability.
 */

const TLVNode = require('./tlv_node');

class TLVSerializer {
  /**
   * Serialize a TLVNode to hex string
   * 
   * @param {TLVNode} node - Node to serialize
   * @returns {string} Uppercase hex string
   */
  static serialize(node) {
    const tagBytes = this.encodeTag(node.tag);
    const valueBytes = this.serializeValue(node);
    const lengthBytes = this.encodeLength(valueBytes.length);
    
    return Buffer.concat([tagBytes, lengthBytes, valueBytes]).toString('hex').toUpperCase();
  }

  /**
   * Encode tag to bytes
   * 
   * Tags are encoded directly from their hex string representation.
   * Supports 1-byte (e.g., '9A'), 2-byte (e.g., '9F02'), and 3-byte (e.g., 'DF850D') tags.
   * 
   * @param {string} tag - Tag in hex string format (e.g., '9A', '9F02', 'DF850D')
   * @returns {Buffer} Tag bytes
   */
  static encodeTag(tag) {
    // Tag is already in hex string format - just convert to buffer
    // Length of hex string / 2 = number of bytes
    return Buffer.from(tag, 'hex');
  }

  /**
   * Encode length to bytes
   * 
   * Length encoding rules:
   * - 0-127: Single byte (0x00-0x7F)
   * - 128-255: Two bytes (0x81 XX)
   * - 256-65535: Three bytes (0x82 XX YY)
   * 
   * @param {number} length - Value length
   * @returns {Buffer} Length bytes
   */
  static encodeLength(length) {
    if (length <= 127) {
      // Short form: single byte
      return Buffer.from([length]);
    } else if (length <= 255) {
      // 2-byte form: 0x81 prefix
      return Buffer.from([0x81, length]);
    } else if (length <= 65535) {
      // 3-byte form: 0x82 prefix + 2-byte big-endian length
      return Buffer.from([0x82, (length >> 8) & 0xFF, length & 0xFF]);
    } else {
      throw new Error(`Length ${length} exceeds maximum supported value (65535)`);
    }
  }

  /**
   * Serialize node's value
   * 
   * For primitive nodes: return the value buffer.
   * For constructed nodes: serialize all children and concatenate.
   * 
   * @param {TLVNode} node - Node whose value to serialize
   * @returns {Buffer} Value bytes
   */
  static serializeValue(node) {
    if (node.isPrimitive()) {
      // Primitive: return value as-is
      return node.value || Buffer.alloc(0);
    } else {
      // Constructed: serialize all children
      const childBuffers = node.children.map(child => {
        const hex = this.serialize(child);
        return Buffer.from(hex, 'hex');
      });
      return Buffer.concat(childBuffers);
    }
  }

  /**
   * Serialize multiple nodes to hex string
   * 
   * Useful for serializing a list of top-level TLV elements.
   * 
   * @param {TLVNode[]} nodes - Array of nodes to serialize
   * @returns {string} Uppercase hex string
   */
  static serializeMultiple(nodes) {
    const buffers = nodes.map(node => {
      const hex = this.serialize(node);
      return Buffer.from(hex, 'hex');
    });
    return Buffer.concat(buffers).toString('hex').toUpperCase();
  }
}

module.exports = TLVSerializer;
