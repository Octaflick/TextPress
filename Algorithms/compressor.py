"""
compressor.py — File-level compression/decompression engine for zipcompress.

Supported algorithms:
    - Huffman coding  (extension: .huff, algo id: 0x01)
    - LZ78            (extension: .lz78, algo id: 0x02)

Binary file format (.huff / .lz78):
    [4 bytes]  magic: b"ZPCM"
    [1 byte]   algorithm id
    [4 bytes]  original file size (big-endian)
    [...]      algorithm-specific payload
"""

from __future__ import annotations

import json
import struct
import sys
import os

# Add parent directory so we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from huffman import HuffmanEncoder, HuffmanDecoder, HuffmanTreeBuilder
from LZ78 import compress as lz78_compress, decompress as lz78_decompress, LZ78Token

# ── Constants ──────────────────────────────────────────────────────────────────

MAGIC = b"ZPCM"
ALGO_HUFFMAN = 0x01
ALGO_LZ78 = 0x02

EXTENSION_TO_ALGO = {
    ".huff": ALGO_HUFFMAN,
    ".lz78": ALGO_LZ78,
}

ALGO_NAMES = {
    ALGO_HUFFMAN: "Huffman",
    ALGO_LZ78: "LZ78",
}


# ── Huffman file helpers ───────────────────────────────────────────────────────

def _huffman_compress_payload(data: bytes) -> bytes:
    """Compress raw bytes using Huffman coding. Returns the payload bytes."""
    encoder = HuffmanEncoder()
    encoder.build_from_bytes(data)

    # Encode data to bit string
    bit_string = encoder.encode_bytes(data)

    # Serialize the code table directly (char_ordinal -> bit_code)
    # This avoids tree reconstruction mismatches from heap ordering
    code_table = {str(ord(ch)): code for ch, code in encoder.code_table.items()}
    code_json = json.dumps(code_table, separators=(",", ":")).encode("utf-8")

    # Pack bit string into actual bytes
    padding = (8 - len(bit_string) % 8) % 8
    bit_string_padded = bit_string + "0" * padding
    encoded_bytes = int(bit_string_padded, 2).to_bytes(len(bit_string_padded) // 8, "big")

    # Payload layout:
    #   [1 byte]   padding count
    #   [4 bytes]  code table JSON length
    #   [...]      code table JSON
    #   [...]      encoded bytes
    payload = struct.pack(">BI", padding, len(code_json)) + code_json + encoded_bytes
    return payload


def _huffman_decompress_payload(payload: bytes) -> bytes:
    """Decompress Huffman payload back to original bytes."""
    offset = 0

    # Read padding and code table length
    padding, code_json_len = struct.unpack_from(">BI", payload, offset)
    offset += 5

    # Read and parse code table
    code_json = payload[offset:offset + code_json_len].decode("utf-8")
    offset += code_json_len
    code_table = json.loads(code_json)  # {char_ordinal_str: bit_code_str}

    # Build reverse lookup: bit_code -> byte_value
    reverse_table = {code: int(ordinal) for ordinal, code in code_table.items()}

    # Read encoded bytes and convert back to bit string
    encoded_bytes = payload[offset:]
    if len(encoded_bytes) == 0:
        return b""

    bit_string = bin(int.from_bytes(encoded_bytes, "big"))[2:]
    # Pad to full byte width
    bit_string = bit_string.zfill(len(encoded_bytes) * 8)
    # Remove trailing padding
    if padding > 0:
        bit_string = bit_string[:-padding]

    # Decode using reverse table (walk bit by bit, match codes)
    decoded_bytes = []
    current_code = ""
    for bit in bit_string:
        current_code += bit
        if current_code in reverse_table:
            decoded_bytes.append(reverse_table[current_code])
            current_code = ""

    if current_code:
        raise ValueError("Invalid encoded data: trailing bits don't form a valid code")

    return bytes(decoded_bytes)


# ── LZ78 file helpers ─────────────────────────────────────────────────────────

def _lz78_compress_payload(data: bytes) -> bytes:
    """Compress raw bytes using LZ78. Returns the payload bytes."""
    text = data.decode("utf-8", errors="replace")
    tokens = lz78_compress(text)

    # Serialize tokens as JSON array of [index, char] pairs
    token_list = [[t.index, t.char] for t in tokens]
    token_json = json.dumps(token_list, separators=(",", ":")).encode("utf-8")
    return token_json


def _lz78_decompress_payload(payload: bytes) -> bytes:
    """Decompress LZ78 payload back to original bytes."""
    token_list = json.loads(payload.decode("utf-8"))
    tokens = [LZ78Token(index=t[0], char=t[1]) for t in token_list]
    text = lz78_decompress(tokens)
    return text.encode("utf-8")


# ── Public API ─────────────────────────────────────────────────────────────────

def detect_algorithm(filepath: str) -> int:
    """Detect algorithm from file extension."""
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext not in EXTENSION_TO_ALGO:
        raise ValueError(
            f"Unknown extension '{ext}'. Supported: {', '.join(EXTENSION_TO_ALGO.keys())}"
        )
    return EXTENSION_TO_ALGO[ext]


def compress_file(input_path: str, output_path: str) -> dict:
    """
    Compress a file and write the result to output_path.
    Algorithm is inferred from the output file extension.

    Returns a dict with compression stats.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    algo_id = detect_algorithm(output_path)

    # Read input file
    with open(input_path, "rb") as f:
        data = f.read()

    original_size = len(data)

    # Compress based on algorithm
    if algo_id == ALGO_HUFFMAN:
        payload = _huffman_compress_payload(data)
    elif algo_id == ALGO_LZ78:
        payload = _lz78_compress_payload(data)
    else:
        raise ValueError(f"Unsupported algorithm id: {algo_id}")

    # Write output: magic + algo_id + original_size + payload
    with open(output_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">BI", algo_id, original_size))
        f.write(payload)

    compressed_size = os.path.getsize(output_path)
    ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

    return {
        "algorithm": ALGO_NAMES[algo_id],
        "original_size": original_size,
        "compressed_size": compressed_size,
        "ratio": ratio,
    }


def decompress_file(input_path: str, output_path: str) -> dict:
    """
    Decompress a .huff or .lz78 file and write the result to output_path.
    Algorithm is auto-detected from the file header.

    Returns a dict with decompression stats.
    """
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Compressed file not found: {input_path}")

    with open(input_path, "rb") as f:
        # Read and validate magic
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(
                f"Invalid file format: missing ZPCM magic header. "
                f"Is this a file compressed by zipcompress?"
            )

        # Read algorithm id and original size
        algo_id, original_size = struct.unpack(">BI", f.read(5))

        if algo_id not in ALGO_NAMES:
            raise ValueError(f"Unknown algorithm id in file header: {algo_id}")

        # Read payload
        payload = f.read()

    # Decompress
    if algo_id == ALGO_HUFFMAN:
        data = _huffman_decompress_payload(payload)
    elif algo_id == ALGO_LZ78:
        data = _lz78_decompress_payload(payload)
    else:
        raise ValueError(f"Unsupported algorithm id: {algo_id}")

    # Write output
    with open(output_path, "wb") as f:
        f.write(data)

    return {
        "algorithm": ALGO_NAMES[algo_id],
        "original_size": original_size,
        "restored_size": len(data),
    }
