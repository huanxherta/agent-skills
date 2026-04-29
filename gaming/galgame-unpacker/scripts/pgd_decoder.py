#!/usr/bin/env python3
"""
PGD (Softpal/Amuse Craft) image decoder
Supports: GE format (methods 1,2,3), PGD3/PGD2 incremental format
Based on GARbro's ArcFormats/Softpal/ImagePGD.cs
"""

import struct
import os
import sys
from PIL import Image
import io


class ByteReader:
    """Simple byte stream reader"""
    def __init__(self, data):
        self.data = data
        self.pos = 0
    
    def read_byte(self):
        if self.pos >= len(self.data):
            return -1
        b = self.data[self.pos]
        self.pos += 1
        return b
    
    def read_uint16(self):
        lo = self.read_byte()
        hi = self.read_byte()
        if lo < 0 or hi < 0:
            return -1
        return lo | (hi << 8)
    
    def read_bytes(self, count):
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result
    
    def read_int32(self):
        return struct.unpack_from('<I', self.data, self.pos - 4)[0] if self.pos >= 4 else 0


def copy_overlapped(output, src, dst, count):
    """Copy with overlap support (like memmove)"""
    for i in range(count):
        if src + i >= 0 and src + i < len(output) and dst + i < len(output):
            output[dst + i] = output[src + i]


def unpack_ge_pre(reader, output_length):
    """LZSS-like decompression used in GE format"""
    output = bytearray(output_length)
    dst = 0
    ctl = 2
    
    while dst < output_length:
        ctl >>= 1
        if ctl == 1:
            b = reader.read_byte()
            if b < 0:
                break
            ctl = b | 0x100
        
        if (ctl & 1) != 0:
            # Back-reference
            offset = reader.read_uint16()
            if offset < 0:
                break
            count = offset & 7
            if (offset & 8) == 0:
                b = reader.read_byte()
                if b < 0:
                    break
                count = (count << 8) | b
            count += 4
            offset >>= 4
            copy_overlapped(output, dst - offset, dst, count)
            dst += count
        else:
            # Literal
            count = reader.read_byte()
            if count < 0:
                break
            data = reader.read_bytes(count)
            output[dst:dst + len(data)] = data
            dst += len(data)
    
    return output


def unpack_standard(reader, output_length, look_behind):
    """Standard LZSS decompression (for 00_C and 11_C variants)"""
    output = bytearray(output_length)
    dst = 0
    ctl = 2
    
    while dst < output_length:
        ctl >>= 1
        if ctl == 1:
            b = reader.read_byte()
            if b < 0:
                break
            ctl = b | 0x100
        
        if (ctl & 1) != 0:
            src_offset = reader.read_uint16()
            count = reader.read_byte()
            if src_offset < 0 or count < 0:
                break
            if dst > look_behind:
                src_offset += dst - look_behind
            copy_overlapped(output, src_offset, dst, count)
            dst += count
        else:
            count = reader.read_byte()
            if count < 0:
                break
            data = reader.read_bytes(count)
            output[dst:dst + len(data)] = data
            dst += len(data)
    
    return output


def post_process_1(input_data, width, height):
    """Method 1: Planar BGRA (4 planes: A, R, G, B → BGRA32)"""
    plane_size = width * height
    output = bytearray(plane_size * 4)
    a_src = 0
    r_src = plane_size
    g_src = 2 * plane_size
    b_src = 3 * plane_size
    dst = 0
    for i in range(plane_size):
        output[dst] = input_data[b_src + i]      # B
        output[dst + 1] = input_data[g_src + i]  # G
        output[dst + 2] = input_data[r_src + i]  # R
        output[dst + 3] = input_data[a_src + i]  # A
        dst += 4
    return output, 'BGRA'


def clamp(val):
    if val > 255:
        return 255
    if val < 0:
        return 0
    return val


def post_process_2(input_data, width, height):
    """Method 2: YCbCr-like (3 segments → BGR24)"""
    stride = width * 3
    segment_size = width * height // 4
    src0 = 0
    src1 = segment_size
    src2 = segment_size * 2
    
    output = bytearray(stride * height)
    dst = 0
    points = [0, 1, width, width + 1]
    
    for y in range(height // 2):
        for x in range(width // 2):
            i0 = input_data[src0]
            if i0 >= 128:
                i0 -= 256  # signed
            i1 = input_data[src1]
            if i1 >= 128:
                i1 -= 256  # signed
            
            b_val = 226 * i0
            g_val = -43 * i0 - 89 * i1
            r_val = 179 * i1
            src0 += 1
            src1 += 1
            
            for pt in points:
                base_value = input_data[src2 + pt] << 7
                offset = dst + 3 * pt
                if offset + 2 < len(output):
                    output[offset] = clamp((base_value + b_val) >> 7)
                    output[offset + 1] = clamp((base_value + g_val) >> 7)
                    output[offset + 2] = clamp((base_value + r_val) >> 7)
            
            src2 += 2
            dst += 6
        src2 += width
        dst += stride
    
    return output, 'BGR'


def post_process_pal(input_data, src, width, height, pixel_size):
    """Delta decoding (PostProcessPal)"""
    stride = width * pixel_size
    output = bytearray(height * stride)
    ctl = src
    src += height
    dst = 0
    
    for row in range(height):
        c = input_data[ctl]
        ctl += 1
        
        if (c & 1) != 0:
            # Row with left-prediction
            prev = dst
            output[dst:dst + pixel_size] = input_data[src:src + pixel_size]
            src += pixel_size
            dst += pixel_size
            count = stride - pixel_size
            for i in range(count):
                output[dst] = (output[prev] - input_data[src]) & 0xFF
                dst += 1
                prev += 1
                src += 1
        elif (c & 2) != 0:
            # Row with up-prediction
            prev = dst - stride
            count = stride
            for i in range(count):
                output[dst] = (output[prev] - input_data[src]) & 0xFF
                dst += 1
                prev += 1
                src += 1
        else:
            # Row with average prediction
            output[dst:dst + pixel_size] = input_data[src:src + pixel_size]
            src += pixel_size
            dst += pixel_size
            prev = dst - stride
            count = stride - pixel_size
            for i in range(count):
                output[dst] = ((output[prev] + output[dst - pixel_size]) // 2 - input_data[src]) & 0xFF
                dst += 1
                prev += 1
                src += 1
    
    return output


def post_process_3(input_data, width, height):
    """Method 3: TGA-embedded with delta decoding"""
    bpp = struct.unpack_from('<H', input_data, 2)[0]
    w = struct.unpack_from('<H', input_data, 4)[0]
    h = struct.unpack_from('<H', input_data, 6)[0]
    
    if bpp == 32:
        pixel_size = 4
        mode = 'BGRA'
    elif bpp == 24:
        pixel_size = 3
        mode = 'BGR'
    else:
        raise ValueError(f"Unsupported BPP: {bpp}")
    
    output = post_process_pal(input_data, 8, w, h, pixel_size)
    return output, mode, w, h


def decode_pgd_ge(data):
    """Decode a GE format PGD file"""
    if len(data) < 0x28:
        raise ValueError("File too small for GE format")
    
    magic = data[0:3]
    if magic != b'GE ':
        raise ValueError(f"Not a GE format PGD (magic: {magic})")
    
    # Parse header
    offset_x = struct.unpack_from('<i', data, 4)[0]
    offset_y = struct.unpack_from('<i', data, 8)[0]
    width = struct.unpack_from('<I', data, 0x0C)[0]
    height = struct.unpack_from('<I', data, 0x10)[0]
    method = struct.unpack_from('<H', data, 0x1C)[0]
    
    # Parse payload
    unpacked_size = struct.unpack_from('<I', data, 0x20)[0]
    packed_size = struct.unpack_from('<I', data, 0x24)[0]
    
    reader = ByteReader(data)
    reader.pos = 0x28
    
    # Decompress
    decompressed = unpack_ge_pre(reader, unpacked_size)
    
    # Post-process based on method
    if method == 1:
        pixels, mode = post_process_1(decompressed, width, height)
        return pixels, mode, width, height
    elif method == 2:
        pixels, mode = post_process_2(decompressed, width, height)
        return pixels, mode, width, height
    elif method == 3:
        pixels, mode, w, h = post_process_3(decompressed, width, height)
        return pixels, mode, w, h
    else:
        raise ValueError(f"Unsupported PGD method: {method}")


def decode_pgd3(data, base_data=None):
    """Decode a PGD3/PGD2 incremental format PGD file"""
    if len(data) < 0x30:
        raise ValueError("File too small for PGD3 format")
    
    magic = data[0:4]
    if magic not in [b'PGD3', b'PGD2']:
        raise ValueError(f"Not a PGD3 format (magic: {magic})")
    
    # Parse header
    offset_x = struct.unpack_from('<H', data, 4)[0]
    offset_y = struct.unpack_from('<H', data, 6)[0]
    width = struct.unpack_from('<H', data, 8)[0]
    height = struct.unpack_from('<H', data, 0x0A)[0]
    bpp = struct.unpack_from('<H', data, 0x0C)[0]
    base_name = data[0x0E:0x30].split(b'\x00')[0].decode('ascii', errors='replace')
    
    pixel_size = bpp // 8
    
    # Parse payload
    unpacked_size = struct.unpack_from('<I', data, 0x30)[0]
    packed_size = struct.unpack_from('<I', data, 0x34)[0]
    
    reader = ByteReader(data)
    reader.pos = 0x38
    
    # Decompress overlay
    overlay = unpack_ge_pre(reader, unpacked_size)
    
    # Apply delta decoding to overlay
    overlay_decoded = post_process_pal(overlay, 0, width, height, pixel_size)
    
    if base_data is not None:
        # XOR overlay onto base image
        base_bpp = len(base_data) // (width * height) if width * height > 0 else 4
        # Actually need base image dimensions, not overlay dimensions
        # This is handled by the caller
        return overlay_decoded, base_name, offset_x, offset_y, width, height, pixel_size
    else:
        return overlay_decoded, base_name, offset_x, offset_y, width, height, pixel_size


def pgd_to_image(data, base_data=None, base_width=None, base_height=None, base_mode=None):
    """Convert PGD data to PIL Image"""
    # Handle 4-byte prefix (some PAC files add a size/type prefix)
    magic = data[0:4]
    if magic[:3] != b'GE ' and magic not in [b'PGD3', b'PGD2']:
        # Try skipping 4-byte prefix
        if len(data) > 4:
            magic = data[4:8]
            if magic[:3] == b'GE ' or magic in [b'PGD3', b'PGD2']:
                data = data[4:]
    
    magic = data[0:4]
    if magic[:3] == b'GE ':
        pixels, mode, width, height = decode_pgd_ge(data)
    elif magic in [b'PGD3', b'PGD2']:
        overlay, base_name, ox, oy, w, h, ps = decode_pgd3(data, base_data)
        if base_data is not None and base_width and base_height:
            # XOR overlay onto base
            base_bpp = len(base_mode.replace('A', '').replace('BGR', '3').replace('BGRA', '4'))
            # Simple approach: just return the overlay for now
            pixels = overlay
            width = w
            height = h
            mode = 'BGRA' if ps == 4 else 'BGR'
        else:
            pixels = overlay
            width = w
            height = h
            mode = 'BGRA' if ps == 4 else 'BGR'
    else:
        raise ValueError(f"Unknown PGD format: {magic}")
    
    # Convert to PIL Image
    if mode == 'BGRA':
        img = Image.frombytes('RGBA', (width, height), bytes(pixels), 'raw', 'BGRA')
    elif mode == 'BGR':
        img = Image.frombytes('RGB', (width, height), bytes(pixels), 'raw', 'BGR')
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    return img


def main():
    if len(sys.argv) < 3:
        print("Usage: pgd_decoder.py <input_dir> <output_dir>")
        print("       pgd_decoder.py <input.pgd> <output.png>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if os.path.isdir(input_path):
        # Batch mode
        os.makedirs(output_path, exist_ok=True)
        files = sorted([f for f in os.listdir(input_path) if f.upper().endswith('.PGD')])
        success = 0
        fail = 0
        
        for fname in files:
            fpath = os.path.join(input_path, fname)
            out_name = os.path.splitext(fname)[0] + '.png'
            out_path = os.path.join(output_path, out_name)
            
            try:
                with open(fpath, 'rb') as f:
                    data = f.read()
                img = pgd_to_image(data)
                img.save(out_path)
                success += 1
            except Exception as e:
                print(f"FAIL {fname}: {e}")
                fail += 1
        
        print(f"Done: {success} success, {fail} fail out of {len(files)} files")
    else:
        # Single file mode
        with open(input_path, 'rb') as f:
            data = f.read()
        img = pgd_to_image(data)
        img.save(output_path)
        print(f"Saved: {output_path}")


if __name__ == '__main__':
    main()
