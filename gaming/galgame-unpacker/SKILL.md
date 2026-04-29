---
name: galgame-unpacker
description: Unpack visual novel game archives and decode proprietary image formats. Supports Softpal/Amuse Craft engine PAC archives and PGD images (GE/PGD3). Use when extracting images, audio, or scripts from visual novel games.
license: MIT
compatibility: Requires Python 3.8+ and Pillow (pip install Pillow)
metadata:
  author: huanxherta
  version: "1.0"
  category: gaming
---

# GalGame Unpacker

Extract and decode resources from Softpal/Amuse Craft visual novel games.

## Supported Formats

### PAC Archives (.pac)

Bundle format used to package game resources.

**Structure:**
```
Header (0x800 bytes):
  [0:4]   Magic "PAC " (0x50414320)
  [4:8]   Padding
  [8:10]  File count (uint16 LE)

Entries (file_count × 40 bytes, at offset 0x800):
  [0:4]   Offset to data (absolute, 0 = after entries)
  [4:36]  Filename (32 bytes, null-padded)
  [36:40] File size (uint32 LE)

Data: starts at 0x800 + file_count × 40
```

**Common PAC files:**
- `ev.pac` — Event CG images
- `bk.pac` — Backgrounds
- `face.pac` — Character expressions
- `st.pac` — Character sprites
- `system.pac` — UI elements
- `bgm.pac`, `se.pac`, `voice.pac` — Audio

### PGD Images (.pgd)

Compressed image format with LZSS-like compression.

**Variants:**

1. **GE format** (magic `GE \x00`)
   - Header: 0x20 bytes
   - Width at 0x0C, Height at 0x10, Method at 0x1C
   - Payload: `[unpacked_size:u32][packed_size:u32][compressed_data]`
   - Post-processing:
     - Method 1: Planar BGRA (4 planes → BGRA32)
     - Method 2: YCbCr → BGR24
     - Method 3: TGA with delta decoding

2. **PGD3/PGD2 format** (magic `PGD3`/`PGD2`)
   - Incremental overlay format
   - References a base GE image by filename
   - Overlay applied via XOR

**Note:** Some PAC files add a 4-byte size prefix before PGD data. The extractor handles this automatically.

## Quick Start

### Extract PAC archives

```bash
# Single PAC file
python3 scripts/unpack_pac.py game/ev.pac output/ev/

# All PAC files in a directory
python3 scripts/unpack_pac.py game/ output/
```

### Convert PGD to PNG

```bash
# Single file
python3 scripts/pgd_decoder.py input.PGD output.png

# Batch directory
python3 scripts/pgd_decoder.py output/ev/ output/ev_png/
```

### Full Pipeline

```bash
# 1. Extract all PAC files
python3 scripts/unpack_pac.py /path/to/game/ /tmp/extracted/

# 2. Convert PGD images to PNG
for dir in /tmp/extracted/*/; do
    if ls "$dir"/*.PGD 2>/dev/null | head -1 > /dev/null; then
        python3 scripts/pgd_decoder.py "$dir" "${dir%_png}"
    fi
done
```

## Pitfalls

1. **Engine detection**: This tool handles Softpal/Amuse Craft PAC/PGD only. CatSystem2 uses different formats (HG2/HG3).

2. **4-byte prefix**: Some PAC files add a size prefix before PGD data. The extractor strips it automatically.

3. **PGD3 dependencies**: PGD3 files reference a base GE image. Standalone conversion produces only the overlay layer.

4. **Method 2 (YCbCr)**: Uses subsampled chroma. Output dimensions may differ from header values.

5. **Large batches**: Converting 4000+ PGD files takes ~30 minutes. Use batch mode.

## Verification

After extraction:
```bash
# Count extracted files
find output/ -name "*.png" | wc -l

# Verify image validity
python3 -c "from PIL import Image; Image.open('output/ev/EV001A01.png').verify()"

# Check dimensions
python3 -c "from PIL import Image; print(Image.open('output/ev/EV001A01.png').size)"
```

## Reference

Format reverse-engineered from GARbro source: `ArcFormats/Softpal/ImagePGD.cs`
