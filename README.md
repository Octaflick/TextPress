# Compression-WIP- (zipcompress)

A **CLI-based file compression tool** built with Python, supporting Huffman coding and LZ78 dictionary compression.

---

## 🚀 Quick Start

```bash
# Compress a file using Huffman coding
python zipcompress.py compress input.txt output.huff

# Compress a file using LZ78
python zipcompress.py compress input.txt output.lz78

# Decompress
python zipcompress.py decompress output.huff restored.txt

# Show help
python zipcompress.py help
```

---

## 📖 Commands

| Command | Usage | Description |
|---|---|---|
| `compress` | `zipcompress compress <input> <output>` | Compress a file |
| `decompress` | `zipcompress decompress <input> <output>` | Decompress a file |
| `help` | `zipcompress help` | Show all available commands |

The **algorithm is auto-detected** from the output file extension:

| Extension | Algorithm |
|---|---|
| `.huff` | Huffman coding |
| `.lz78` | LZ78 dictionary compression |

---

## 📁 Project Structure

```
zipcompression/
├── zipcompress.py              # CLI entry point
├── Algorithms/
│   ├── huffman.py              # Huffman coding (encoder + decoder)
│   ├── LZ78.py                 # LZ78 dictionary compression
│   ├── compressor.py           # File-level compress/decompress engine
│   └── huffman.cpp             # C++ Huffman (WIP)
└── README.md
```

---

## 🔧 How It Works

### Huffman Coding
Assigns shorter binary codes to more frequent bytes. Best for files with uneven character distributions.

### LZ78
Builds a dictionary of repeated phrases on the fly. Best for files with lots of repeated text patterns.

### Compressed File Format
All compressed files use a binary format with:
- `ZPCM` magic header (4 bytes)
- Algorithm identifier (1 byte)
- Original file size (4 bytes)
- Algorithm-specific payload

---

## 👥 Contributors

- Team of 2 — collaborative CLI compression project
