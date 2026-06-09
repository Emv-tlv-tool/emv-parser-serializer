/**
 * Config Adapter - Parses Poseidon terminal configuration blobs
 * 
 * Poseidon configs are pure TLV with no envelope - parse directly.
 * 
 * Key templates:
 * - E0: Terminal configuration (terminal-wide settings)
 * - E1: CA public keys per RID (certificate authority keys)
 * - E2: Application configuration per AID (payment app settings)
 * 
 * Application Configuration (E2) contains:
 * - AID (4F): Application Identifier
 * - Label (DF04): Application display name
 * - TAC Default (DF11): Terminal Action Code - Default
 * - TAC Denial (DF12): Terminal Action Code - Denial
 * - TAC Online (DF13): Terminal Action Code - Online
 * - Floor Limit (DF05): Offline transaction limit
 * - Terminal Capabilities (9F33): Terminal feature flags
 * 
 * CA Keys (E1) contains:
 * - RID (DF01): Registered Application Provider Identifier
 * - Key Index (DF02): CA Public Key Index
 * - Modulus (E6): CA Public Key Modulus
 * - Exponent (E7): CA Public Key Exponent
 * - Checksum (DF03): Key checksum
 */

const TLVParser = require('../core/tlv_parser');

class ConfigAdapter {
  /**
   * Parse a Poseidon configuration blob
   * 
   * @param {Buffer} buffer - Raw config blob bytes
   * @returns {TLVNode[]} Parsed TLV tree
   */
  static parse(buffer) {
    return TLVParser.parse(buffer);
  }

  /**
   * Extract all application configurations from E2 templates
   * 
   * @param {TLVNode[]} tree - Parsed TLV tree
   * @returns {Object[]} Array of application config objects
   */
  static getApplicationConfigs(tree) {
    const configs = [];
    const e2Nodes = this.findAllTemplates(tree, 'E2');

    for (const e2 of e2Nodes) {
      const config = this.extractAppConfig(e2);
      configs.push(config);
    }

    return configs;
  }

  /**
   * Extract application configuration from a single E2 node
   * 
   * @param {TLVNode} e2Node - E2 template node
   * @returns {Object} Application configuration object
   */
  static extractAppConfig(e2Node) {
    const config = {};

    // Find each field using DFS
    const aid = this.findChild(e2Node, '4F');
    const label = this.findChild(e2Node, 'DF04');
    const tacDefault = this.findChild(e2Node, 'DF11');
    const tacDenial = this.findChild(e2Node, 'DF12');
    const tacOnline = this.findChild(e2Node, 'DF13');
    const floorLimit = this.findChild(e2Node, 'DF05');
    const terminalCapabilities = this.findChild(e2Node, '9F33');

    if (aid) config.aid = aid.value.toString('hex').toUpperCase();
    if (label) config.label = label.value.toString('ascii');
    if (tacDefault) config.tacDefault = tacDefault.value.toString('hex').toUpperCase();
    if (tacDenial) config.tacDenial = tacDenial.value.toString('hex').toUpperCase();
    if (tacOnline) config.tacOnline = tacOnline.value.toString('hex').toUpperCase();
    if (floorLimit) config.floorLimit = this.parseAmount(floorLimit.value);
    if (terminalCapabilities) config.terminalCapabilities = terminalCapabilities.value.toString('hex').toUpperCase();

    return config;
  }

  /**
   * Extract all CA keys from E1 templates
   * 
   * @param {TLVNode[]} tree - Parsed TLV tree
   * @returns {Object[]} Array of CA key objects
   */
  static getCAKeys(tree) {
    const keys = [];
    const e1Nodes = this.findAllTemplates(tree, 'E1');

    for (const e1 of e1Nodes) {
      const key = this.extractCAKey(e1);
      keys.push(key);
    }

    return keys;
  }

  /**
   * Extract CA key from a single E1 node
   * 
   * @param {TLVNode} e1Node - E1 template node
   * @returns {Object} CA key object
   */
  static extractCAKey(e1Node) {
    const key = {};

    const rid = this.findChild(e1Node, 'DF01');
    const keyIndex = this.findChild(e1Node, 'DF02');
    const modulus = this.findChild(e1Node, 'E6');
    const exponent = this.findChild(e1Node, 'E7');
    const checksum = this.findChild(e1Node, 'DF03');

    if (rid) key.rid = rid.value.toString('hex').toUpperCase();
    if (keyIndex) key.keyIndex = keyIndex.value[0];
    if (modulus) key.modulus = modulus.value.toString('hex').toUpperCase();
    if (exponent) key.exponent = exponent.value.toString('hex').toUpperCase();
    if (checksum) key.checksum = checksum.value.toString('hex').toUpperCase();

    return key;
  }

  /**
   * Find a template by tag in the tree (DFS)
   * 
   * @param {TLVNode[]} tree - TLV tree
   * @param {string} tag - Tag to find
   * @returns {TLVNode|undefined} Found node or undefined
   */
  static findTemplate(tree, tag) {
    for (const node of tree) {
      if (node.tag === tag) {
        return node;
      }
      // Search children
      if (node.isConstructed) {
        const found = this.findTemplate(node.children, tag);
        if (found) return found;
      }
    }
    return undefined;
  }

  /**
   * Find all templates by tag in the tree (DFS)
   * 
   * @param {TLVNode[]} tree - TLV tree
   * @param {string} tag - Tag to find
   * @returns {TLVNode[]} Array of found nodes
   */
  static findAllTemplates(tree, tag) {
    const results = [];

    for (const node of tree) {
      if (node.tag === tag) {
        results.push(node);
      }
      // Search children
      if (node.isConstructed) {
        const childResults = this.findAllTemplates(node.children, tag);
        results.push(...childResults);
      }
    }

    return results;
  }

  /**
   * Find a child node by tag (direct children only)
   * 
   * @param {TLVNode} parent - Parent node
   * @param {string} tag - Tag to find
   * @returns {TLVNode|undefined} Found child or undefined
   */
  static findChild(parent, tag) {
    return parent.children.find(child => child.tag === tag);
  }

  /**
   * Parse amount from BCD buffer
   * 
   * @param {Buffer} value - BCD encoded amount
   * @returns {number} Amount in cents
   */
  static parseAmount(value) {
    let amount = 0;
    for (const byte of value) {
      const high = (byte >> 4) & 0x0F;
      const low = byte & 0x0F;
      amount = amount * 100 + high * 10 + low;
    }
    return amount;
  }
}

module.exports = ConfigAdapter;
