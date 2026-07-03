from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class LZ78Token:
    index: int
    char: str


def compress(text: str) -> List[LZ78Token]:
    """
    Compress text using the traditional LZ78 algorithm.

    Output is a list of (index, character) tokens, where:
    - index is the dictionary index of the longest previous phrase
    - character is the next unmatched character
    """
    dictionary: Dict[str, int] = {}
    tokens: List[LZ78Token] = []
    current = ""
    next_index = 1

    for ch in text:
        candidate = current + ch
        if candidate in dictionary:
            current = candidate
            continue

        index = dictionary.get(current, 0)
        tokens.append(LZ78Token(index, ch))
        dictionary[candidate] = next_index
        next_index += 1
        current = ""

    if current:
        # Traditional LZ78 emits the final phrase as (index, "") when the
        # input ends exactly on a dictionary entry.
        tokens.append(LZ78Token(dictionary[current], ""))

    return tokens


def decompress(tokens: List[LZ78Token]) -> str:
    """
    Rebuild the original text from LZ78 tokens.
    Dictionary indices are 1-based; 0 means the empty string.
    """
    dictionary: Dict[int, str] = {0: ""}
    next_index = 1
    output: List[str] = []

    for token in tokens:
        if token.index not in dictionary:
            raise ValueError(f"Invalid LZ78 token index: {token.index}")

        phrase = dictionary[token.index] + token.char
        output.append(phrase)
        dictionary[next_index] = phrase
        next_index += 1

    return "".join(output)


def tokens_to_pairs(tokens: List[LZ78Token]) -> List[Tuple[int, str]]:
    return [(token.index, token.char) for token in tokens]


if __name__ == "__main__":
    sample = "ABAABABAABBBBBBBBB"
    compressed = compress(sample)
    restored = decompress(compressed)

    print("Compressed:", tokens_to_pairs(compressed))
    print("Restored:", restored)

