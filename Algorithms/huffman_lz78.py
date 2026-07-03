from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
import struct
from typing import Dict, Optional


MODE_RAW = 0
MODE_HUFFMAN = 1
MODE_LZ78 = 2
MODE_LZ78_THEN_HUFFMAN = 3
MODE_HUFFMAN_THEN_LZ78 = 4


@dataclass
class _HuffmanNode:
    symbol: Optional[int]
    freq: int
    left: Optional["_HuffmanNode"] = None
    right: Optional["_HuffmanNode"] = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def _write_varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("Varint cannot encode negative values")

    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0

    while True:
        if offset >= len(data):
            raise ValueError("Invalid varint: reached end of payload")

        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift

        if byte & 0x80 == 0:
            return result, offset

        shift += 7
        if shift > 63:
            raise ValueError("Invalid varint: value is too large")


def _build_huffman_tree(frequencies: Dict[int, int]) -> Optional[_HuffmanNode]:
    heap: list[tuple[int, int, _HuffmanNode]] = []
    unique = count()

    for symbol, freq in sorted(frequencies.items()):
        heappush(heap, (freq, next(unique), _HuffmanNode(symbol, freq)))

    if not heap:
        return None

    while len(heap) > 1:
        left_freq, _, left_node = heappop(heap)
        right_freq, _, right_node = heappop(heap)
        merged = _HuffmanNode(None, left_freq + right_freq, left_node, right_node)
        heappush(heap, (merged.freq, next(unique), merged))

    return heappop(heap)[2]


def _build_huffman_codes(
    node: Optional[_HuffmanNode],
    codes: Dict[int, str],
    prefix: str = "",
) -> None:
    if node is None:
        return

    if node.is_leaf():
        if node.symbol is None:
            raise ValueError("Invalid Huffman tree: leaf without a symbol")
        codes[node.symbol] = prefix if prefix else "0"
        return

    _build_huffman_codes(node.left, codes, prefix + "0")
    _build_huffman_codes(node.right, codes, prefix + "1")


def _huffman_encode(data: bytes) -> bytes:
    if not data:
        return struct.pack(">BH", 0, 0)

    frequencies = dict(Counter(data))
    root = _build_huffman_tree(frequencies)
    codes: Dict[int, str] = {}
    _build_huffman_codes(root, codes)

    encoded_bits = bytearray()
    current_byte = 0
    bit_count = 0

    for symbol in data:
        for bit in codes[symbol]:
            current_byte = (current_byte << 1) | (1 if bit == "1" else 0)
            bit_count += 1
            if bit_count == 8:
                encoded_bits.append(current_byte)
                current_byte = 0
                bit_count = 0

    padding = 0
    if bit_count:
        padding = 8 - bit_count
        encoded_bits.append(current_byte << padding)

    header = bytearray(struct.pack(">BH", padding, len(frequencies)))
    for symbol, freq in sorted(frequencies.items()):
        header.extend(struct.pack(">BI", symbol, freq))

    return bytes(header) + bytes(encoded_bits)


def _huffman_decode(payload: bytes) -> bytes:
    if len(payload) < 3:
        raise ValueError("Invalid Huffman payload: missing header")

    padding, symbol_count = struct.unpack_from(">BH", payload, 0)
    if padding > 7:
        raise ValueError("Invalid Huffman payload: padding must be 0-7 bits")

    offset = 3
    frequencies: Dict[int, int] = {}

    for _ in range(symbol_count):
        if offset + 5 > len(payload):
            raise ValueError("Invalid Huffman payload: truncated frequency table")
        symbol, freq = struct.unpack_from(">BI", payload, offset)
        offset += 5
        if freq <= 0:
            raise ValueError("Invalid Huffman payload: symbol frequency must be positive")
        frequencies[symbol] = freq

    expected_size = sum(frequencies.values())
    if expected_size == 0:
        return b""

    if symbol_count == 1:
        symbol = next(iter(frequencies))
        return bytes([symbol]) * expected_size

    root = _build_huffman_tree(frequencies)
    output = bytearray()
    current = root

    for packed_byte in payload[offset:]:
        for bit_index in range(7, -1, -1):
            bit = (packed_byte >> bit_index) & 1
            current = current.right if bit else current.left

            if current is None:
                raise ValueError("Invalid Huffman payload: walked into a missing branch")

            if current.is_leaf():
                if current.symbol is None:
                    raise ValueError("Invalid Huffman tree: leaf without a symbol")
                output.append(current.symbol)
                if len(output) == expected_size:
                    return bytes(output)
                current = root

    raise ValueError("Invalid Huffman payload: encoded data ended early")


def _lz78_encode(data: bytes) -> bytes:
    dictionary: Dict[bytes, int] = {}
    token_stream = bytearray()
    current = b""
    next_index = 1

    for byte in data:
        candidate = current + bytes([byte])
        if candidate in dictionary:
            current = candidate
            continue

        token_stream.extend(_write_varint(dictionary.get(current, 0)))
        token_stream.extend(_write_varint(byte + 1))
        dictionary[candidate] = next_index
        next_index += 1
        current = b""

    if current:
        token_stream.extend(_write_varint(dictionary[current]))
        token_stream.extend(_write_varint(0))

    return bytes(token_stream)


def _lz78_decode(payload: bytes) -> bytes:
    dictionary: Dict[int, bytes] = {0: b""}
    output = bytearray()
    offset = 0
    next_index = 1

    while offset < len(payload):
        index, offset = _read_varint(payload, offset)
        marker, offset = _read_varint(payload, offset)

        if index not in dictionary:
            raise ValueError(f"Invalid LZ78 payload: unknown dictionary index {index}")
        if marker > 256:
            raise ValueError("Invalid LZ78 payload: byte marker is out of range")

        next_byte = b"" if marker == 0 else bytes([marker - 1])
        phrase = dictionary[index] + next_byte
        output.extend(phrase)

        if marker != 0:
            dictionary[next_index] = phrase
            next_index += 1

    return bytes(output)


def compress(data: bytes) -> bytes:
    """
    Compress bytes with an adaptive Huffman-LZ78 hybrid.

    The payload stores the smallest strategy among raw, Huffman, LZ78,
    LZ78 followed by Huffman, and Huffman followed by LZ78.
    """
    huffman_payload = _huffman_encode(data)
    lz78_payload = _lz78_encode(data)

    candidates = [
        (MODE_RAW, data),
        (MODE_HUFFMAN, huffman_payload),
        (MODE_LZ78, lz78_payload),
        (MODE_LZ78_THEN_HUFFMAN, _huffman_encode(lz78_payload)),
        (MODE_HUFFMAN_THEN_LZ78, _lz78_encode(huffman_payload)),
    ]

    mode, payload = min(candidates, key=lambda candidate: len(candidate[1]) + 1)
    return bytes([mode]) + payload


def decompress(payload: bytes) -> bytes:
    if not payload:
        raise ValueError("Invalid hybrid payload: missing compression mode")

    mode = payload[0]
    data = payload[1:]

    if mode == MODE_RAW:
        return data
    if mode == MODE_HUFFMAN:
        return _huffman_decode(data)
    if mode == MODE_LZ78:
        return _lz78_decode(data)
    if mode == MODE_LZ78_THEN_HUFFMAN:
        return _lz78_decode(_huffman_decode(data))
    if mode == MODE_HUFFMAN_THEN_LZ78:
        return _huffman_decode(_lz78_decode(data))

    raise ValueError(f"Invalid hybrid payload: unknown compression mode {mode}")


__all__ = ["compress", "decompress"]
