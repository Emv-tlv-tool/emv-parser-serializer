/**
 * TLVNode - Represents a single Tag-Length-Value element in EMV data structure
 * 
 * EMV uses a hierarchical TLV (Tag-Length-Value) encoding:
 * - Tag: 1 or 2 bytes identifying the data element
 * - Length: 1-3 bytes specifying the value length
 * - Value: The actual data (primitive) or nested TLV structures (constructed)
 * 
 * Primitive nodes: Contain raw data values (e.g., transaction date, amount)
 * Constructed nodes: Contain nested TLV structures forming a tree
 * 
 * Example hierarchy:
 * 6F (FCI Template - constructed)
 *   ├── 84 (AID - primitive)
 *   └── A5 (FCI Proprietary - constructed)
 *         └── 50 (Label - primitive)
 */
class TLVNode {
  /**
   * Create a new TLVNode
   * 
   * @param {string} tag - Tag identifier in uppercase hex (e.g., '9A', '6F')
   * @param {Buffer} value - Raw value bytes (empty buffer for constructed nodes initially)
   * @param {boolean} isConstructed - True if node contains nested TLV structures
   */
  constructor(tag, value, isConstructed = false) {
    this.tag = tag;
    this.value = value;
    this.length = value ? value.length : 0;
    this.isConstructed = isConstructed;
    this.children = [];
  }

  /**
   * Add a child node to this constructed node
   * 
   * Used during parsing to build the TLV tree hierarchy.
   * Only constructed nodes can have children.
   * 
   * @param {TLVNode} node - Child TLVNode to add
   * @throws {Error} If attempting to add child to primitive node
   */
  addChild(node) {
    if (this.isConstructed) {
      this.children.push(node);
    } else {
      throw new Error('Cannot add child to primitive node');
    }
  }

  /**
   * Get all child nodes
   * 
   * @returns {TLVNode[]} Array of child nodes (empty for primitive nodes)
   */
  getChildren() {
    return this.children;
  }

  /**
   * Check if this node is primitive (contains raw data)
   * 
   * @returns {boolean} True if primitive, false if constructed
   */
  isPrimitive() {
    return !this.isConstructed;
  }

  /**
   * Convert node to JSON object for serialization/output
   * 
   * Recursively includes children for constructed nodes.
   * Value is converted to uppercase hex string for readability.
   * 
   * @returns {Object} Plain object representation of the node
   * 
   * Example output:
   * {
   *   tag: '9A',
   *   length: 3,
   *   value: '210315',
   *   isConstructed: false,
   *   children: undefined
   * }
   */
  toJSON() {
    return {
      tag: this.tag,
      length: this.length,
      value: this.value ? this.value.toString('hex').toUpperCase() : '',
      isConstructed: this.isConstructed,
      children: this.children.length > 0 ? this.children.map(c => c.toJSON()) : undefined
    };
  }
}

module.exports = TLVNode;
