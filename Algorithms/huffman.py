from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from typing import Optional


@dataclass
class HuffmanNode:
    ch: Optional[str]
    freq: int
    left: Optional["HuffmanNode"] = None
    right: Optional["HuffmanNode"] = None

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


class HuffmanTreeBuilder:
    def build(self, frequencies: dict[str, int]) -> Optional[HuffmanNode]:
        heap: list[tuple[int, int, HuffmanNode]] = []
        unique = count()

        for ch, freq in frequencies.items():
            heappush(heap, (freq, next(unique), HuffmanNode(ch, freq)))

        if not heap:
            return None

        while len(heap) > 1:
            left_freq, _, left_node = heappop(heap)
            right_freq, _, right_node = heappop(heap)
            merged = HuffmanNode(None, left_freq + right_freq, left_node, right_node)
            heappush(heap, (merged.freq, next(unique), merged))

        return heappop(heap)[2]


class HuffmanDecoder:
    def __init__(self, root: Optional[HuffmanNode] = None) -> None:
        self.root = root

    def set_tree(self, root: Optional[HuffmanNode]) -> None:
        self.root = root

    def decode(self, encoded_bits: str) -> str:
        if self.root is None:
            raise ValueError("Huffman tree is empty")

        decoded: list[str] = []
        current = self.root

        for bit in encoded_bits:
            if bit not in "01":
                continue

            current = current.left if bit == "0" else current.right

            if current is None:
                raise ValueError("Invalid encoded string: walked into a missing branch")

            if current.is_leaf():
                if current.ch is None:
                    raise ValueError("Invalid Huffman tree: leaf without a character")
                decoded.append(current.ch)
                current = self.root

        if current is not self.root:
            raise ValueError("Invalid encoded string: trailing incomplete Huffman code")

        return "".join(decoded)


class HuffmanEncoder:
    """Encodes data using Huffman coding."""

    def __init__(self) -> None:
        self.code_table: dict[str, str] = {}
        self.root: Optional[HuffmanNode] = None

    def _build_codes(self, node: Optional[HuffmanNode], prefix: str = "") -> None:
        """Recursively traverse the tree to build the code table."""
        if node is None:
            return
        if node.is_leaf():
            # Edge case: single unique character gets code "0"
            self.code_table[node.ch] = prefix if prefix else "0"
            return
        self._build_codes(node.left, prefix + "0")
        self._build_codes(node.right, prefix + "1")

    def build_from_data(self, data: str) -> None:
        """Build frequency table and Huffman tree from raw string data."""
        frequencies: dict[str, int] = {}
        for ch in data:
            frequencies[ch] = frequencies.get(ch, 0) + 1

        builder = HuffmanTreeBuilder()
        self.root = builder.build(frequencies)
        self.code_table = {}
        self._build_codes(self.root)

    def build_from_bytes(self, data: bytes) -> None:
        """Build frequency table and Huffman tree from raw bytes."""
        frequencies: dict[str, int] = {}
        for byte in data:
            ch = chr(byte)
            frequencies[ch] = frequencies.get(ch, 0) + 1

        builder = HuffmanTreeBuilder()
        self.root = builder.build(frequencies)
        self.code_table = {}
        self._build_codes(self.root)

    def encode(self, data: str) -> str:
        """Encode a string into a Huffman-coded bit string."""
        if not self.code_table:
            raise ValueError("Encoder not initialized. Call build_from_data first.")
        return "".join(self.code_table[ch] for ch in data)

    def encode_bytes(self, data: bytes) -> str:
        """Encode bytes into a Huffman-coded bit string."""
        if not self.code_table:
            raise ValueError("Encoder not initialized. Call build_from_bytes first.")
        return "".join(self.code_table[chr(byte)] for byte in data)

    def get_frequency_table(self) -> dict[str, int]:
        """Return the frequency table used for encoding."""
        if self.root is None:
            return {}
        freqs: dict[str, int] = {}
        self._collect_frequencies(self.root, freqs)
        return freqs

    def _collect_frequencies(self, node: Optional[HuffmanNode], freqs: dict[str, int]) -> None:
        if node is None:
            return
        if node.is_leaf() and node.ch is not None:
            freqs[node.ch] = node.freq
            return
        self._collect_frequencies(node.left, freqs)
        self._collect_frequencies(node.right, freqs)


if __name__ == "__main__":
    # Demo: encode and decode
    sample = "ABAABABAAB"
    encoder = HuffmanEncoder()
    encoder.build_from_data(sample)

    print("Code table:", encoder.code_table)
    encoded_bits = encoder.encode(sample)
    print("Encoded:", encoded_bits)

    decoder = HuffmanDecoder(encoder.root)
    decoded = decoder.decode(encoded_bits)
    print("Decoded:", decoded)
    print("Match:", sample == decoded)
