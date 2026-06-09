// Value Decoder - PASTE YOUR CODE HERE
/**
 * ValueDecoder - Decodes EMV tag values to human-readable formats
 * 
 * Each EMV tag has specific encoding rules:
 * - BCD (Binary Coded Decimal) for numeric values
 * - ASCII for text values
 * - Bitmask for flags and options
 * 
 * This module provides tag-specific decoding for common EMV values.
 */

// ISO 3166-1 numeric country codes
const COUNTRY_CODES = {
  '040': 'Austria',
  '056': 'Belgium',
  '250': 'France',
  '276': 'Germany',
  '280': 'Germany',  // Alternative code
  '380': 'Italy',
  '528': 'Netherlands',
  '724': 'Spain',
  '826': 'United Kingdom',
  '840': 'United States',
  '756': 'Switzerland',
  '036': 'Australia',
  '124': 'Canada',
  '392': 'Japan',
  '410': 'South Korea',
  '156': 'China',
  '356': 'India',
  '076': 'Brazil',
  '643': 'Russia',
  '554': 'New Zealand',
  '012': 'Algeria',
  '484': 'Mexico',
  '702': 'Singapore',
  '158': 'Taiwan',
  '360': 'Indonesia',
  '458': 'Malaysia',
  '608': 'Philippines',
  '764': 'Thailand',
  '414': 'Kuwait',
  '784': 'United Arab Emirates',
  '682': 'Saudi Arabia',
  '422': 'Lebanon',
  '504': 'Morocco',
  '818': 'Egypt',
  '710': 'South Africa',
  '011': 'Benin',
  '204': 'Cameroon',
  '388': 'Jamaica',
  '591': 'Panama',
  '340': 'Honduras',
  '188': 'Costa Rica',
  '320': 'Guatemala',
  '484': 'Mexico',
};

// ISO 4217 currency codes
const CURRENCY_CODES = {
  '978': 'EUR',
  '840': 'USD',
  '826': 'GBP',
  '756': 'CHF',
  '124': 'CAD',
  '036': 'AUD',
  '392': 'JPY',
  '410': 'KRW',
  '156': 'CNY',
  '356': 'INR',
  '076': 'BRL',
  '643': 'RUB',
  '554': 'NZD',
  '578': 'NOK',
  '752': 'SEK',
  '208': 'DKK',
  '348': 'HUF',
  '203': 'CZK',
  '616': 'PLN',
  '946': 'RON',
  '710': 'ZAR',
  '818': 'EGP',
  '352': 'ISK',
  '578': 'NOK',
  '752': 'SEK',
  '032': 'ARS',
  '152': 'CLP',
  '484': 'MXN',
  '604': 'PEN',
  '170': 'COP',
  '986': 'BRL',
};

// CVM (Cardholder Verification Method) types
const CVM_TYPES = {
  0x00: 'No CVM',
  0x01: 'Plaintext PIN (ICC verification)',
  0x02: 'Enciphered PIN (online)',
  0x1E: 'Signature (paper)',
  0x1F: 'No CVM required',
  0x41: 'Plaintext PIN and signature',
  0x42: 'Enciphered PIN and signature',
};

class ValueDecoder {
  /**
   * Decode a tag value to human-readable string
   * 
   * @param {string} tag - Tag identifier in uppercase hex
   * @param {Buffer} value - Raw value bytes
   * @returns {string} Human-readable representation
   */
  static decodeValue(tag, value) {
    if (!value || value.length === 0) {
      return '';
    }

    switch (tag) {
      case '5A':
        return this.decodePAN(value);
      case '5F24':
        return this.decodeExpiryDate(value);
      case '5F20':
        return this.decodeASCII(value);
      case '9F02':
      case '9F03':
        return this.decodeAmount(value);
      case '9A':
        return this.decodeDate(value);
      case '9F27':
        return this.decodeCryptogramType(value);
      case '9F34':
        return this.decodeCVMResults(value);
      case '9F1A':
      case '5F28':
        return this.decodeCountryCode(value);
      case '49':
        return this.decodeCurrencyCode(value);
      default:
        return this.toHex(value);
    }
  }

  /**
   * Decode PAN (Primary Account Number)
   * 
   * BCD format, right-padded with F, masked with spaces every 4 digits.
   * 
   * @param {Buffer} value - PAN bytes
   * @returns {string} Formatted PAN
   */
  static decodePAN(value) {
    let pan = '';
    for (const byte of value) {
      const high = (byte >> 4) & 0x0F;
      const low = byte & 0x0F;
      if (high <= 9) pan += high.toString();
      if (low <= 9) pan += low.toString();
    }
    
    // Format with spaces every 4 digits
    return pan.replace(/(.{4})(?=.)/g, '$1 ').trim();
  }

  /**
   * Decode expiry date (YYMM → YYYY-MM)
   * 
   * @param {Buffer} value - Date bytes (2 bytes, BCD)
   * @returns {string} Formatted date
   */
  static decodeExpiryDate(value) {
    const year = this.bcdToNumber(value[0]);
    const month = this.bcdToNumber(value[1]);
    
    // EMV uses 2-digit year, assume 2000-2099
    const fullYear = 2000 + year;
    
    return `${fullYear}-${month.toString().padStart(2, '0')}`;
  }

  /**
   * Decode ASCII text
   * 
   * @param {Buffer} value - ASCII bytes
   * @returns {string} Decoded string
   */
  static decodeASCII(value) {
    return value.toString('utf8').trim();
  }

  /**
   * Decode amount (n12 BCD → decimal string)
   * 
   * Value represents cents, output in major currency unit.
   * 
   * @param {Buffer} value - Amount bytes (6 bytes, BCD)
   * @returns {string} Decimal amount string
   */
  static decodeAmount(value) {
    let amount = '';
    for (const byte of value) {
      amount += this.bcdToNumber(byte).toString().padStart(2, '0');
    }
    
    // Last 2 digits are cents
    const cents = parseInt(amount.slice(-2), 10);
    const units = parseInt(amount.slice(0, -2) || '0', 10);
    
    return `${units}.${cents.toString().padStart(2, '0')}`;
  }

  /**
   * Decode transaction date (YYMMDD → YYYY-MM-DD)
   * 
   * @param {Buffer} value - Date bytes (3 bytes, BCD)
   * @returns {string} Formatted date
   */
  static decodeDate(value) {
    const year = this.bcdToNumber(value[0]);
    const month = this.bcdToNumber(value[1]);
    const day = this.bcdToNumber(value[2]);
    
    const fullYear = 2000 + year;
    
    return `${fullYear}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
  }

  /**
   * Decode cryptogram type
   * 
   * @param {Buffer} value - Cryptogram type byte
   * @returns {string} Human-readable cryptogram type
   */
  static decodeCryptogramType(value) {
    const type = value[0];
    switch (type) {
      case 0x00:
        return 'AAC (Transaction Declined)';
      case 0x01:
        return 'TC (Transaction Approved)';
      case 0x10:
        return 'ARQC (Authorization Request)';
      default:
        return `Unknown (${type.toString(16).toUpperCase().padStart(2, '0')})`;
    }
  }

  /**
   * Decode CVM results
   * 
   * @param {Buffer} value - CVM result bytes (3 bytes)
   * @returns {string} Human-readable CVM result
   */
  static decodeCVMResults(value) {
    const cvmType = value[0];
    const cvmResult = value[2];
    
    const typeName = CVM_TYPES[cvmType] || `Unknown CVM (${cvmType.toString(16).toUpperCase()})`;
    
    let resultText = '';
    switch (cvmResult) {
      case 0x00:
        resultText = 'successful';
        break;
      case 0x01:
        resultText = 'failed';
        break;
      default:
        resultText = `unknown (${cvmResult.toString(16).toUpperCase()})`;
    }
    
    return `${typeName} - ${resultText}`;
  }

  /**
   * Decode country code
   * 
   * @param {Buffer} value - Country code bytes (2 bytes, BCD)
   * @returns {string} Country name with code
   */
  static decodeCountryCode(value) {
    // 2 bytes contain a 3-digit BCD code: digit1 in high nibble of byte0,
    // digit2 in low nibble of byte0, digit3 in high nibble of byte1
    // e.g., 0x04 0x00 → digits 0,4,0 → "040" (Austria)
    // e.g., 0x28 0x00 → digits 2,8,0 → "280" (Germany)
    const d0 = (value[0] >> 4) & 0x0F;
    const d1 = value[0] & 0x0F;
    const d2 = (value[1] >> 4) & 0x0F;
    const codeNum = d0 * 100 + d1 * 10 + d2;
    const code = codeNum.toString().padStart(3, '0');
    
    const name = COUNTRY_CODES[code] || 'Unknown';
    return `${name} (${code})`;
  }

  /**
   * Decode currency code
   * 
   * @param {Buffer} value - Currency code bytes (2 bytes, BCD)
   * @returns {string} Currency name with code
   */
  static decodeCurrencyCode(value) {
    // 2 bytes contain a 3-digit BCD code: digit1 in high nibble of byte0,
    // digit2 in low nibble of byte0, digit3 in high nibble of byte1
    // e.g., 0x97 0x80 → digits 9,7,8 → "978" (EUR)
    const d0 = (value[0] >> 4) & 0x0F;
    const d1 = value[0] & 0x0F;
    const d2 = (value[1] >> 4) & 0x0F;
    const codeNum = d0 * 100 + d1 * 10 + d2;
    const code = codeNum.toString().padStart(3, '0');
    
    const name = CURRENCY_CODES[code] || 'Unknown';
    return `${name} (${code})`;
  }

  /**
   * Convert BCD byte to number
   * 
   * @param {number} byte - BCD encoded byte
   * @returns {number} Decimal value
   */
  static bcdToNumber(byte) {
    return ((byte >> 4) & 0x0F) * 10 + (byte & 0x0F);
  }

  /**
   * Convert buffer to uppercase hex string
   * 
   * @param {Buffer} value - Value bytes
   * @returns {string} Hex string
   */
  static toHex(value) {
    return value.toString('hex').toUpperCase();
  }
}

module.exports = ValueDecoder;
