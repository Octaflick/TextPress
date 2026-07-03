#!/usr/bin/env python3
"""
zipcompress — A CLI-based file compression tool.

Usage:
    python zipcompress.py compress  <input_file> <output_file>
    python zipcompress.py decompress <input_file> <output_file>
    python zipcompress.py help

Supported formats:
    .huff   — Huffman coding
    .lz78   — LZ78 dictionary compression
    .hlz    — adaptive Huffman-LZ78 hybrid
"""

from __future__ import annotations

import sys
import os
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add Algorithms directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "Algorithms"))

from compressor import compress_file, decompress_file, EXTENSION_TO_ALGO, ALGO_NAMES


# ── ANSI Colors ────────────────────────────────────────────────────────────────

class Colors:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"
    BLUE = "\033[94m"


# ── Formatters ─────────────────────────────────────────────────────────────────

def format_size(size_bytes: int) -> str:
    """Format bytes into a human-readable size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def print_banner():
    """Print the zipcompress banner."""
    print()
    print(f"  {Colors.CYAN}{Colors.BOLD}╔══════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"  {Colors.CYAN}{Colors.BOLD}║{Colors.RESET}          {Colors.MAGENTA}{Colors.BOLD}⚡ ZIPCOMPRESS{Colors.RESET}  {Colors.DIM}— File Compression Tool{Colors.RESET}        {Colors.CYAN}{Colors.BOLD}║{Colors.RESET}")
    print(f"  {Colors.CYAN}{Colors.BOLD}╚══════════════════════════════════════════════════════════╝{Colors.RESET}")
    print()


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_help():
    """Display help information with all available commands."""
    print_banner()

    print(f"  {Colors.BOLD}USAGE{Colors.RESET}")
    print(f"    {Colors.GREEN}zipcompress{Colors.RESET} <command> <input_file> <output_file>")
    print()

    print(f"  {Colors.BOLD}COMMANDS{Colors.RESET}")
    print(f"    {Colors.GREEN}compress{Colors.RESET}    <input> <output>    Compress a file")
    print(f"    {Colors.GREEN}decompress{Colors.RESET}  <input> <output>    Decompress a file")
    print(f"    {Colors.GREEN}help{Colors.RESET}                            Show this help message")
    print()

    print(f"  {Colors.BOLD}SUPPORTED FORMATS{Colors.RESET}")
    print(f"    {Colors.YELLOW}.huff{Colors.RESET}    Huffman coding")
    print(f"    {Colors.YELLOW}.lz78{Colors.RESET}    LZ78 dictionary compression")
    print(f"    {Colors.YELLOW}.hlz{Colors.RESET}     Adaptive Huffman-LZ78 hybrid")
    print()

    print(f"  {Colors.BOLD}EXAMPLES{Colors.RESET}")
    print(f"    {Colors.DIM}# Compress with Huffman{Colors.RESET}")
    print(f"    {Colors.CYAN}zipcompress compress input.txt output.huff{Colors.RESET}")
    print()
    print(f"    {Colors.DIM}# Compress with LZ78{Colors.RESET}")
    print(f"    {Colors.CYAN}zipcompress compress input.txt output.lz78{Colors.RESET}")
    print()
    print(f"    {Colors.DIM}# Compress with Huffman-LZ78 hybrid{Colors.RESET}")
    print(f"    {Colors.CYAN}zipcompress compress input.txt output.hlz{Colors.RESET}")
    print()
    print(f"    {Colors.DIM}# Decompress{Colors.RESET}")
    print(f"    {Colors.CYAN}zipcompress decompress output.hlz restored.txt{Colors.RESET}")
    print()


def cmd_compress(input_file: str, output_file: str):
    """Compress a file."""
    print_banner()

    print(f"  {Colors.BOLD}COMPRESSING{Colors.RESET}")
    print(f"    Input file:   {Colors.CYAN}{input_file}{Colors.RESET}")
    print(f"    Output file:  {Colors.CYAN}{output_file}{Colors.RESET}")
    print()

    start_time = time.time()

    try:
        stats = compress_file(input_file, output_file)
    except FileNotFoundError as e:
        print(f"  {Colors.RED}✗ Error:{Colors.RESET} {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"  {Colors.RED}✗ Error:{Colors.RESET} {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  {Colors.RED}✗ Unexpected error:{Colors.RESET} {e}")
        sys.exit(1)

    elapsed = time.time() - start_time

    ratio_color = Colors.GREEN if stats["ratio"] > 0 else Colors.YELLOW
    print(f"  {Colors.GREEN}✓ Compression successful!{Colors.RESET}")
    print()
    print(f"    Algorithm:       {Colors.MAGENTA}{stats['algorithm']}{Colors.RESET}")
    print(f"    Original size:   {format_size(stats['original_size'])}")
    print(f"    Compressed size: {format_size(stats['compressed_size'])}")
    print(f"    Compression:     {ratio_color}{stats['ratio']:.1f}%{Colors.RESET}")
    print(f"    Time:            {elapsed:.3f}s")
    print()


def cmd_decompress(input_file: str, output_file: str):
    """Decompress a file."""
    print_banner()

    print(f"  {Colors.BOLD}DECOMPRESSING{Colors.RESET}")
    print(f"    Input file:   {Colors.CYAN}{input_file}{Colors.RESET}")
    print(f"    Output file:  {Colors.CYAN}{output_file}{Colors.RESET}")
    print()

    start_time = time.time()

    try:
        stats = decompress_file(input_file, output_file)
    except FileNotFoundError as e:
        print(f"  {Colors.RED}✗ Error:{Colors.RESET} {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"  {Colors.RED}✗ Error:{Colors.RESET} {e}")
        sys.exit(1)
    except Exception as e:
        print(f"  {Colors.RED}✗ Unexpected error:{Colors.RESET} {e}")
        sys.exit(1)

    elapsed = time.time() - start_time

    print(f"  {Colors.GREEN}✓ Decompression successful!{Colors.RESET}")
    print()
    print(f"    Algorithm:       {Colors.MAGENTA}{stats['algorithm']}{Colors.RESET}")
    print(f"    Restored size:   {format_size(stats['restored_size'])}")
    print(f"    Time:            {elapsed:.3f}s")
    print()


# ── Main Entry Point ──────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        cmd_help()
        return

    command = args[0].lower()

    if command == "compress":
        if len(args) < 3:
            print(f"\n  {Colors.RED}✗ Error:{Colors.RESET} compress requires 2 arguments: <input_file> <output_file>")
            print(f"  {Colors.DIM}Usage: zipcompress compress input.txt output.huff{Colors.RESET}\n")
            sys.exit(1)
        cmd_compress(args[1], args[2])

    elif command == "decompress":
        if len(args) < 3:
            print(f"\n  {Colors.RED}✗ Error:{Colors.RESET} decompress requires 2 arguments: <input_file> <output_file>")
            print(f"  {Colors.DIM}Usage: zipcompress decompress output.huff restored.txt{Colors.RESET}\n")
            sys.exit(1)
        cmd_decompress(args[1], args[2])

    else:
        print(f"\n  {Colors.RED}✗ Unknown command:{Colors.RESET} '{command}'")
        print(f"  {Colors.DIM}Run 'zipcompress help' to see available commands.{Colors.RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
