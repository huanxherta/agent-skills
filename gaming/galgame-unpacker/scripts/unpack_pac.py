#!/usr/bin/env python3
"""
PAC archive extractor for Softpal/Amuse Craft visual novels.
Extracts PGD images from .pac archives.

Usage:
    python3 unpack_pac.py <input.pac> <output_dir>
    python3 unpack_pac.py <game_dir> <output_dir>  # Extract all .pac files
"""

import struct
import os
import sys


def extract_pac(pac_path, output_dir):
    """Extract all files from a PAC archive.
    
    PAC Format:
    - Header (0x800 bytes):
      - [0:4]   Magic "PAC " (0x50414320)
      - [4:8]   Padding (zeros)
      - [8:10]  File count (uint16 LE)
    - Entries (file_count × 40 bytes, starting at 0x800):
      - [0:4]   Offset to data (absolute, 0 = after entries)
      - [4:36]  Filename (32 bytes, null-padded)
      - [36:40] File size (uint32 LE)
    - Data: starts at 0x800 + file_count × 40
    
    Returns: (extracted_count, total_count)
    """
    with open(pac_path, 'rb') as f:
        data = f.read()
    
    # Verify magic
    if data[0:4] != b'PAC ':
        raise ValueError(f"Not a PAC file: {pac_path}")
    
    # Parse header
    file_count = struct.unpack_from('<H', data, 8)[0]
    
    # Calculate entries offset and data start
    entries_start = 0x800
    entries_end = entries_start + file_count * 40
    default_data_offset = entries_end  # For entries with offset=0
    
    os.makedirs(output_dir, exist_ok=True)
    extracted = 0
    
    for i in range(file_count):
        entry_offset = entries_start + i * 40
        
        # Parse entry
        data_offset = struct.unpack_from('<I', data, entry_offset)[0]
        name = data[entry_offset + 4:entry_offset + 36].split(b'\x00')[0].decode('ascii', errors='replace')
        size = struct.unpack_from('<I', data, entry_offset + 36)[0]
        
        # Handle offset=0 (first entry uses default offset)
        if data_offset == 0:
            data_offset = default_data_offset
        
        # Extract file
        if size > 0 and data_offset + size <= len(data):
            file_data = data[data_offset:data_offset + size]
            
            # Handle 4-byte prefix for PGD files
            # Some PAC files add a size prefix before the actual PGD magic
            if len(file_data) > 4:
                magic = file_data[0:4]
                # If first 4 bytes don't look like a valid magic, check if skipping 4 bytes helps
                if magic[:3] != b'GE ' and magic not in [b'PGD3', b'PGD2']:
                    potential_magic = file_data[4:8]
                    if potential_magic[:3] == b'GE ' or potential_magic in [b'PGD3', b'PGD2']:
                        file_data = file_data[4:]
            
            output_path = os.path.join(output_dir, name)
            with open(output_path, 'wb') as f:
                f.write(file_data)
            extracted += 1
    
    return extracted, file_count


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.pac|game_dir> <output_dir>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    
    if os.path.isdir(input_path):
        # Extract all .pac files in directory
        pac_files = sorted([f for f in os.listdir(input_path) if f.lower().endswith('.pac')])
        total_extracted = 0
        total_files = 0
        
        for pac_name in pac_files:
            pac_path = os.path.join(input_path, pac_name)
            pac_output = os.path.join(output_dir, os.path.splitext(pac_name)[0])
            
            try:
                extracted, count = extract_pac(pac_path, pac_output)
                print(f"{pac_name}: {extracted}/{count} files extracted")
                total_extracted += extracted
                total_files += count
            except Exception as e:
                print(f"{pac_name}: ERROR - {e}")
        
        print(f"\nTotal: {total_extracted}/{total_files} files extracted")
    else:
        # Extract single PAC file
        extracted, count = extract_pac(input_path, output_dir)
        print(f"Extracted {extracted}/{count} files to {output_dir}")


if __name__ == '__main__':
    main()
