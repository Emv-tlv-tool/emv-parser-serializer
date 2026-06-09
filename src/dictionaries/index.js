/**
 * Tag Dictionaries Index
 * 
 * Merges EMVCo and ZKA tag dictionaries for unified lookup.
 * Provides functions to lookup tag metadata by tag hex or name.
 */

const emvcoTags = require('./emvco_tags.json');
const zkaTags = require('./zka_tags.json');

/**
 * Combined dictionary of all tags
 * ZKA tags take precedence over EMVCo tags for overlapping entries
 */
const allTags = { ...emvcoTags, ...zkaTags };

/**
 * Lookup tag information by tag hex value
 * 
 * @param {string} tag - Tag identifier in uppercase hex (e.g., '9A', 'DF11')
 * @returns {Object|null} Tag metadata or null if not found
 * 
 * @example
 * lookupByTag('9A')
 * // Returns: { name: 'Transaction Date', description: '...', source: 'EMVCo', ... }
 */
function lookupByTag(tag) {
  return allTags[tag] || null;
}

/**
 * Lookup tag information by tag name
 * 
 * @param {string} name - Tag name (e.g., 'PAN', 'TAC Default')
 * @returns {Object|null} Tag metadata with tag hex or null if not found
 * 
 * @example
 * lookupByName('PAN')
 * // Returns: { tag: '5A', name: 'PAN', description: '...', ... }
 */
function lookupByName(name) {
  for (const [tagHex, metadata] of Object.entries(allTags)) {
    if (metadata.name.toLowerCase() === name.toLowerCase()) {
      return { tag: tagHex, ...metadata };
    }
  }
  return null;
}

/**
 * Get all tags from a specific source
 * 
 * @param {string} source - Source identifier ('EMVCo' or 'ZKA')
 * @returns {Object} Dictionary of tags from that source
 */
function getTagsBySource(source) {
  const result = {};
  for (const [tagHex, metadata] of Object.entries(allTags)) {
    if (metadata.source === source) {
      result[tagHex] = metadata;
    }
  }
  return result;
}

/**
 * Get all EMVCo tags
 * 
 * @returns {Object} Dictionary of EMVCo tags
 */
function getEMVCoTags() {
  return { ...emvcoTags };
}

/**
 * Get all ZKA tags
 * 
 * @returns {Object} Dictionary of ZKA tags
 */
function getZKATags() {
  return { ...zkaTags };
}

/**
 * Check if a tag exists in the dictionary
 * 
 * @param {string} tag - Tag identifier in uppercase hex
 * @returns {boolean} True if tag exists
 */
function hasTag(tag) {
  return tag in allTags;
}

/**
 * Get all tag hex values
 * 
 * @returns {string[]} Array of all tag hex values
 */
function getAllTags() {
  return Object.keys(allTags);
}

/**
 * Enhance a TLV node with tag metadata
 * 
 * @param {Object} node - TLV node object with tag property
 * @returns {Object} Node with added name, description, and format
 */
function enhanceNode(node) {
  const metadata = lookupByTag(node.tag);
  if (metadata) {
    return {
      ...node,
      name: metadata.name,
      description: metadata.description,
      format: metadata.format,
      source: metadata.source,
    };
  }
  return node;
}

module.exports = {
  lookupByTag,
  lookupByName,
  getTagsBySource,
  getEMVCoTags,
  getZKATags,
  hasTag,
  getAllTags,
  enhanceNode,
  emvcoTags,
  zkaTags,
  allTags,
};
