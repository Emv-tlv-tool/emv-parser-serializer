/**
 * EMV TLV Parser & Serializer
 * 
 * A JavaScript library for parsing and serializing EMV TLV data
 * for German payment terminals (ZVT and Poseidon).
 * 
 * @module emv-tlv
 * @example
 * const EMVTLV = require('emv-tlv');
 * 
 * // Parse raw TLV
 * const tree = EMVTLV.parse('9A03210315', 'raw');
 * 
 * // Parse ZVT message
 * const zvt = EMVTLV.parse(buffer, 'zvt');
 * 
 * // Parse config blob
 * const config = EMVTLV.parse(buffer, 'config');
 */

const TLVParser = require('./src/core/tlv_parser');
const TLVSerializer = require('./src/core/tlv_serializer');
const TLVNode = require('./src/core/tlv_node');
const ValueDecoder = require('./src/decoders/value_decoder');
const BitmaskDecoder = require('./src/decoders/bitmask_decoder');
const ZVTAdapter = require('./src/adapters/zvt_adapter');
const ConfigAdapter = require('./src/adapters/config_adapter');
const Dictionary = require('./src/dictionaries');

/**
 * Parse input data based on type
 * 
 * @param {Buffer|string} input - Raw bytes or hex string
 * @param {string} type - Parser type: 'raw', 'zvt', or 'config'
 * @returns {Object|Object[]} Parsed data structure
 * 
 * @example
 * // Raw TLV
 * const tree = parse('9A03210315', 'raw');
 * // Returns: [{ tag: '9A', name: 'Transaction Date', value: '210315', decoded: '2021-03-15' }]
 * 
 * @example
 * // ZVT message
 * const zvt = parse(buffer, 'zvt');
 * // Returns: { ctrl: '0601', ctrlName: 'Authorisation', tlv: [...] }
 * 
 * @example
 * // Config blob
 * const config = parse(buffer, 'config');
 * // Returns: { ..., applicationConfigs: [...], caKeys: [...] }
 */
function parse(input, type = 'raw') {
  // Convert hex string to buffer if needed
  let buffer;
  if (typeof input === 'string') {
    buffer = Buffer.from(input, 'hex');
  } else if (Buffer.isBuffer(input)) {
    buffer = input;
  } else {
    throw new Error('Input must be Buffer or hex string');
  }

  switch (type) {
    case 'raw':
      return parseRaw(buffer);
    case 'zvt':
      return parseZVT(buffer);
    case 'config':
      return parseConfig(buffer);
    default:
      throw new Error(`Unknown type: ${type}. Use 'raw', 'zvt', or 'config'`);
  }
}

/**
 * Parse raw TLV data
 * 
 * @param {Buffer} buffer - Raw TLV bytes
 * @returns {Object[]} Array of enhanced TLV nodes
 */
function parseRaw(buffer) {
  const nodes = TLVParser.parse(buffer);
  return nodes.map(node => enhanceNode(node));
}

/**
 * Parse ZVT message
 * 
 * @param {Buffer} buffer - ZVT message bytes
 * @returns {Object} Parsed ZVT message with TLV tree
 */
function parseZVT(buffer) {
  const message = ZVTAdapter.parse(buffer);
  const tlvNodes = ZVTAdapter.extractEMVTLV(message);
  
  return {
    ctrl: message.ctrl,
    ctrlName: message.ctrlName,
    length: message.length,
    bmpFields: message.bmpFields,
    tlv: tlvNodes.map(node => enhanceNode(node)),
  };
}

/**
 * Parse Poseidon config blob
 * 
 * @param {Buffer} buffer - Config blob bytes
 * @returns {Object} Parsed config with application configs and CA keys
 */
function parseConfig(buffer) {
  const nodes = ConfigAdapter.parse(buffer);
  const enhancedNodes = nodes.map(node => enhanceNode(node));
  
  // Extract structured data
  const applicationConfigs = ConfigAdapter.getApplicationConfigs(nodes);
  const caKeys = ConfigAdapter.getCAKeys(nodes);
  
  return Object.assign(enhancedNodes, { applicationConfigs, caKeys });
}

/**
 * Enhance a TLV node with metadata and decoded values
 * 
 * @param {TLVNode} node - Raw TLV node
 * @returns {Object} Enhanced node with name, description, and decoded value
 */
function enhanceNode(node) {
  const metadata = Dictionary.lookupByTag(node.tag);
  const enhanced = {
    tag: node.tag,
    length: node.length,
    value: node.value.toString('hex').toUpperCase(),
    isConstructed: node.isConstructed,
  };

  // Add metadata
  if (metadata) {
    enhanced.name = metadata.name;
    enhanced.description = metadata.description;
    enhanced.format = metadata.format;
    enhanced.source = metadata.source;
  }

  // Decode value
  if (!node.isConstructed && node.value.length > 0) {
    enhanced.decoded = ValueDecoder.decodeValue(node.tag, node.value);
    
    // Add bitmask for applicable tags
    if (metadata && metadata.format === 'bitmask') {
      enhanced.bitmask = BitmaskDecoder.decodeBitmask(node.tag, node.value);
    }
  }

  // Recursively enhance children
  if (node.isConstructed && node.children.length > 0) {
    enhanced.children = node.children.map(child => enhanceNode(child));
  }

  return enhanced;
}

/**
 * Serialize TLV nodes to hex string
 * 
 * @param {Object[]} nodes - Array of TLV nodes (can be enhanced or raw)
 * @returns {string} Hex string
 * 
 * @example
 * const tree = parse('9A03210315', 'raw');
 * const hex = serialize(tree);
 * // Returns: '9A03210315'
 */
function serialize(nodes) {
  if (!Array.isArray(nodes)) {
    nodes = [nodes];
  }

  const serialized = nodes.map(node => {
    // If node has a raw TLVNode attached, use it
    if (node._rawNode) {
      return TLVSerializer.serialize(node._rawNode);
    }
    
    // Reconstruct TLVNode from enhanced node
    const tlvNode = new TLVNode(
      node.tag,
      Buffer.from(node.value, 'hex'),
      node.isConstructed
    );
    
    // Add children if present
    if (node.children) {
      node.children.forEach(child => {
        const childNode = reconstructNode(child);
        tlvNode.addChild(childNode);
      });
    }
    
    return TLVSerializer.serialize(tlvNode);
  });

  return serialized.join('');
}

/**
 * Reconstruct a TLVNode from an enhanced node object
 * 
 * @param {Object} enhancedNode - Enhanced node object
 * @returns {TLVNode} TLVNode instance
 */
function reconstructNode(enhancedNode) {
  const node = new TLVNode(
    enhancedNode.tag,
    Buffer.from(enhancedNode.value, 'hex'),
    enhancedNode.isConstructed
  );
  
  if (enhancedNode.children) {
    enhancedNode.children.forEach(child => {
      node.addChild(reconstructNode(child));
    });
  }
  
  return node;
}

/**
 * Find a tag in the TLV tree (depth-first search)
 * 
 * @param {Object[]} tree - TLV tree
 * @param {string} tagHex - Tag to find in hex format
 * @returns {Object|undefined} Found node or undefined
 * 
 * @example
 * const tree = parse('6F088402A000A5025000', 'raw');
 * const aid = findTag(tree, '84');
 * // Returns: { tag: '84', name: 'DF Name', value: 'A000', ... }
 */
function findTag(tree, tagHex) {
  for (const node of tree) {
    if (node.tag === tagHex) {
      return node;
    }
    if (node.children) {
      const found = findTag(node.children, tagHex);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * Find all occurrences of a tag in the TLV tree (depth-first search)
 * 
 * @param {Object[]} tree - TLV tree
 * @param {string} tagHex - Tag to find in hex format
 * @returns {Object[]} Array of found nodes
 * 
 * @example
 * const tree = parse('9A01018201029A0103', 'raw');
 * const dates = findAllTags(tree, '9A');
 * // Returns: [{ tag: '9A', ... }, { tag: '9A', ... }]
 */
function findAllTags(tree, tagHex) {
  const results = [];
  
  for (const node of tree) {
    if (node.tag === tagHex) {
      results.push(node);
    }
    if (node.children) {
      const childResults = findAllTags(node.children, tagHex);
      results.push(...childResults);
    }
  }
  
  return results;
}

/**
 * Decode a node's value
 * 
 * @param {Object} node - TLV node
 * @returns {Object} Node with decoded value and/or bitmask
 */
function decodeNode(node) {
  const result = { ...node };
  
  if (!node.isConstructed && node.value) {
    const valueBuffer = Buffer.from(node.value, 'hex');
    result.decoded = ValueDecoder.decodeValue(node.tag, valueBuffer);
    
    // Add bitmask for applicable tags
    const metadata = Dictionary.lookupByTag(node.tag);
    if (metadata && metadata.format === 'bitmask') {
      result.bitmask = BitmaskDecoder.decodeBitmask(node.tag, valueBuffer);
    }
  }
  
  return result;
}

/**
 * Convert TLV tree to JSON (for serialization/output)
 * 
 * @param {Object[]} tree - TLV tree
 * @returns {Object[]} JSON representation
 */
function toJSON(tree) {
  return tree.map(node => {
    const json = {
      tag: node.tag,
      name: node.name,
      length: node.length,
      value: node.value,
    };
    
    if (node.decoded) {
      json.decoded = node.decoded;
    }
    
    if (node.bitmask) {
      json.bitmask = node.bitmask;
    }
    
    if (node.children && node.children.length > 0) {
      json.children = toJSON(node.children);
    }
    
    return json;
  });
}

// Export public API
module.exports = {
  parse,
  serialize,
  findTag,
  findAllTags,
  decodeNode,
  toJSON,
  
  // Expose core components for advanced use
  TLVParser,
  TLVSerializer,
  TLVNode,
  ValueDecoder,
  BitmaskDecoder,
  ZVTAdapter,
  ConfigAdapter,
  Dictionary,
};
