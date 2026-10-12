#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tiny fixture checks for target-files ZIP structure; no firmware/ROM build."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('target_files_gate', ROOT / 'scripts/r0s/check_target_files_zip.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

INFO = '\n'.join((
    'device=r0s', 'model=SM-S901B', 'os_version=16',
    'source_fingerprint=samsung/r0sxxx/r0s:16/GZH3/123:user/release-keys',
    'target_fingerprint=samsung/r0sxxx/r0s:16/GZH3/123:user/release-keys',
    'use_dynamic_partitions=true', 'super_partition_size=11744051200',
    'super_partition_group=group_basic',
    'super_group_basic_group_size=11739856896',
)) + '\n'


def sparse(blocks):
    return struct.pack('<IHHHHIIII', 0xED26FF3A, 1, 0, 28, 12, 4096, blocks, 1, 0)


def write_fixture(path, *, metadata=INFO, extras=None, omit=None, overflow=False, duplicate=False):
    images = {p + '.img': bytes(4096) for p in MODULE.PARTITIONS}
    images.update({name: bytes(4096) for name in MODULE.RAW_MAX})
    images['unsparse_super_empty.img'] = bytes(4096)
    if overflow:
        images['system.img'] = sparse(3_000_000)  # >11.7GB expanded, only 28 bytes stored
    if omit:
        images.pop(omit)
    if extras:
        images.update(extras)
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('build_info.txt', metadata)
        for name, value in images.items():
            z.writestr(name, value)
        if duplicate:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                z.writestr('boot.img', images['boot.img'])


def run():
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        arc = temp / 'fixture.zip'
        lock = temp / 'assertions.edify'
        lock.write_text('abort("E3099: UN1CA is NOT qualified for flashing.");\n')
        def expect(reject=False, **options):
            write_fixture(arc, **options)
            try:
                MODULE.inspect(arc, lock)
            except MODULE.Blocked as exc:
                if not reject:
                    raise AssertionError('fixture unexpectedly rejected: ' + str(exc)) from exc
            else:
                assert not reject, 'invalid fixture incorrectly accepted'
        expect()
        expect(reject=True, extras={'system_ext.img': b'fake'})
        expect(reject=True, omit='odm.img')
        expect(reject=True, overflow=True)
        expect(reject=True, metadata=INFO.replace('os_version=16', 'os_version=15'))
        expect(reject=True, metadata=INFO.replace('device=r0s', 'device=e1s'))
        expect(reject=True, duplicate=True)
        expect(reject=True, extras={'../escape.img': b'bad'})
        lock.write_text('ui_print("UNSAFE");\n')
        expect(reject=True)
    print('r0s target-files ZIP synthetic gate: 9 positive/negative scenarios PASS')


if __name__ == '__main__':
    run()
