#!/usr/bin/env python3
"""
Merge parent_tags and bytes (bitmask) data from tags(4).json
into emvco_tags.json and zka_tags.json.
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')

def main():
    tags4_path = os.path.join(BASE_DIR, 'src', 'emv_tlv', 'dictionaries', 'tags (4).json')
    emvco_path = os.path.join(BASE_DIR, 'src', 'emv_tlv', 'dictionaries', 'emvco_tags.json')
    zka_path = os.path.join(BASE_DIR, 'src', 'emv_tlv', 'dictionaries', 'zka_tags.json')

    # Load source data
    tags4 = load_json(tags4_path)
    emvco = load_json(emvco_path)
    zka = load_json(zka_path)

    # Build lookup: poseidon_tag -> {parent_tags, bytes}
    lookup = {}
    for entry in tags4:
        tag = entry.get('poseidon_tag', '').strip()
        if not tag:
            continue
        parent_tags = entry.get('parent_tags', [])
        bytes_data = entry.get('bytes', [])
        # Only store bytes if non-empty
        lookup[tag] = {
            'parent_tags': parent_tags,
            'bytes': bytes_data if bytes_data else None
        }

    emvco_updated = 0
    zka_updated = 0
    emvco_added = 0
    zka_added = 0

    # Update emvco_tags.json
    for tag, data in lookup.items():
        if tag in emvco:
            emvco[tag]['parent_tags'] = data['parent_tags']
            if data['bytes']:
                emvco[tag]['bytes'] = data['bytes']
            emvco_updated += 1

    # Update zka_tags.json
    for tag, data in lookup.items():
        if tag in zka:
            zka[tag]['parent_tags'] = data['parent_tags']
            if data['bytes']:
                zka[tag]['bytes'] = data['bytes']
            zka_updated += 1

    # Add new tags from tags(4).json that don't exist in either dictionary
    # We add them as new entries with format info from tags(4).json
    all_existing = set(emvco.keys()) | set(zka.keys())
    for entry in tags4:
        tag = entry.get('poseidon_tag', '').strip()
        if not tag or tag in all_existing or tag == '00':
            continue
        # Determine which dictionary to add to based on tag type
        # EMVCo tags are typically 2 bytes (9Fxx style)
        # ZKA tags are typically DFxx or custom
        new_entry = {
            'name': entry.get('name', ''),
            'description': entry.get('tech_name', ''),
            'format': entry.get('value_format', 'binary'),
            'constructed': False,
            'parent_tags': entry.get('parent_tags', []),
        }
        if entry.get('bytes'):
            new_entry['bytes'] = entry['bytes']
        
        if tag in ['9F01', '9F06', '9F09', '9F15', '9F16', '9F1A', '9F33', '9F35', '9F40', '9F4E', '9F53']:
            # EMVCo tag
            if tag not in emvco:
                emvco[tag] = new_entry
                emvco_added += 1
        else:
            # ZKA tag
            if tag not in zka:
                zka[tag] = new_entry
                zka_added += 1

    # Also check for tags in tags(4).json that are NOT in either dictionary
    all_tag_keys = set(emvco.keys()) | set(zka.keys())
    missing = [t for t in lookup if t not in all_tag_keys and t != '00']
    if missing:
        print(f"Tags from tags(4).json not found in either dictionary ({len(missing)}):")
        for t in missing[:20]:
            print(f"  - {t}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")

    # Save updated dictionaries
    save_json(emvco_path, emvco)
    save_json(zka_path, zka)

    print(f"\nemvco_tags.json: {emvco_updated} tags updated")
    print(f"zka_tags.json: {zka_updated} tags updated")
    print("Done!")

if __name__ == '__main__':
    main()