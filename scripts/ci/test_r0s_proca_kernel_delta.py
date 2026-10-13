#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Synthetic exact-delta tests; no firmware, kernel or ROM used."""
import gzip
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('proca_gate', ROOT / 'scripts/r0s/check_proca_kernel_delta.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fixture(header=b'\x01\x02\x03\x04', symbol=True):
    payload = bytearray(b'\0' * 192)
    payload[40:44] = header
    payload[56:60] = b'ARM\x64'
    if symbol:
        payload[128:128 + len(gate.PROCA_FROM)] = gate.PROCA_FROM
    return bytes(payload)


def main():
    count = 0

    def accepted(stock, work):
        nonlocal count
        gate.check(stock, work)
        count += 1

    def blocked(stock, work):
        nonlocal count
        try:
            gate.check(stock, work)
        except gate.Blocked:
            count += 1
            return
        raise AssertionError('unexpected kernel delta was accepted')

    stock = fixture()
    modified, changes = gate.expected_proca_kernel(stock)
    assert len(changes) == 2
    accepted(stock, modified)
    accepted(gzip.compress(stock, mtime=0), gzip.compress(modified, compresslevel=1, mtime=0))
    accepted(fixture(header=b'\0' * 4, symbol=False), fixture(header=b'\0' * 4, symbol=False))
    accepted(fixture(header=gate.HEADER_PATCH, symbol=False), fixture(header=gate.HEADER_PATCH, symbol=False))

    orig_header_only = fixture(symbol=False)
    expected, _ = gate.expected_proca_kernel(orig_header_only)
    accepted(orig_header_only, expected)
    orig_string_only = fixture(header=b'\0' * 4)
    expected, _ = gate.expected_proca_kernel(orig_string_only)
    accepted(orig_string_only, expected)

    blocked(stock, stock)  # PROCA patch omitted
    tampered = bytearray(modified)
    tampered[80] ^= 1
    blocked(stock, bytes(tampered))  # unrelated kernel change
    blocked(stock, modified + b'\0')  # unexpected expanded size
    blocked(bytes(192), modified)  # not an ARM64 image
    ambiguous = bytearray(stock)
    ambiguous[155:155 + len(gate.PROCA_FROM)] = gate.PROCA_FROM
    blocked(bytes(ambiguous), modified)
    blocked(stock, gzip.compress(b'not a valid kernel'))
    assert count == 12, count
    print(f'r0s exact PROCA delta fixture tests PASS: {count} positive/negative scenarios')


if __name__ == '__main__':
    main()
