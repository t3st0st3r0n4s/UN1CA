#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only exact-delta verifier for UN1CA's existing PROCA kernel patch."""
import gzip
import hashlib
from pathlib import Path
import sys

ARM64_MAGIC = b'ARM\x64'
PROCA_FROM = bytes.fromhex('70726f63615f636f6e66696700')
PROCA_TO = bytes.fromhex('6675636b5f755f73616d6d7900')
HEADER_PATCH = bytes.fromhex('efece fec'.replace(' ', ''))


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def unpack_kernel(data):
    if data.startswith(b'\x1f\x8b'):
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as exc:
            raise Blocked(f'cannot decompress gzip kernel: {exc}') from exc
    require(len(data) >= 64 and data[56:60] == ARM64_MAGIC,
            'missing ARM64 Image header magic after optional gzip decompression')
    return data


def expected_proca_kernel(stock):
    """Replicate only the two exact mutations in unica/patches/proca/customize.sh."""
    expected = bytearray(stock)
    changes = []
    original_header = stock[40:44]
    if original_header not in (b'\0' * 4, HEADER_PATCH):
        expected[40:44] = HEADER_PATCH
        changes.append('header_offset_40')
    count = stock.count(PROCA_FROM)
    require(count <= 1, f'ambiguous PROCA literal: {count} occurrences')
    if count == 1:
        at = stock.find(PROCA_FROM)
        expected[at:at + len(PROCA_FROM)] = PROCA_TO
        changes.append(f'proca_literal_offset_{at}')
    return bytes(expected), changes


def check(stock_bytes, work_bytes):
    stock = unpack_kernel(stock_bytes)
    work = unpack_kernel(work_bytes)
    expected, changes = expected_proca_kernel(stock)
    require(len(work) == len(stock),
            f'kernel expanded length differs: stock={len(stock)}, work={len(work)}')
    if work != expected:
        at = next((i for i, (a, b) in enumerate(zip(expected, work)) if a != b), None)
        require(False, f'unexpected kernel byte at offset {at}: '
                f'expected={expected[at:at+8].hex()}, actual={work[at:at+8].hex()}')
    require(PROCA_FROM not in work, 'unpatched PROCA literal remains')
    return {
        'stock_uncompressed_sha256': hashlib.sha256(stock).hexdigest(),
        'work_uncompressed_sha256': hashlib.sha256(work).hexdigest(),
        'allowed_changes': ','.join(changes) if changes else 'NONE_EXPECTED',
        'bytes': len(work),
    }


def main():
    if len(sys.argv) != 3:
        print('Usage: check_proca_kernel_delta.py <stock-unpacked-kernel> '
              '<work-unpacked-kernel>', file=sys.stderr)
        return 2
    try:
        stock = Path(sys.argv[1]).read_bytes()
        work = Path(sys.argv[2]).read_bytes()
        results = check(stock, work)
    except (Blocked, OSError) as exc:
        print(f'r0s PROCA DELTA BLOCKED: {exc}', file=sys.stderr)
        return 2
    for name, value in results.items():
        print(f'{name}={value}')
    print('EXACT PROCA KERNEL DELTA PASS (binary comparison only; ABI/BOARD unverified)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
