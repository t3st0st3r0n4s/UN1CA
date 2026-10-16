#!/usr/bin/env python3
# Copyright (c) 2026 UN1CA contributors
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only GZH3 r0s target-files archive gate; NEVER qualifies flashing."""
import argparse
from pathlib import Path
import re
import struct
import sys
import zipfile

PARTITIONS = frozenset(('system', 'odm', 'product', 'vendor', 'vendor_dlkm'))
SUPER_BYTES = 11_744_051_200
GROUP_BYTES = 11_739_856_896
RAW_MAX = {'boot.img': 67_108_864, 'vendor_boot.img': 33_554_432,
           'dtbo.img': 8_388_608}
EXPECTED_IMAGES = {p + '.img' for p in PARTITIONS} | set(RAW_MAX) | {'unsparse_super_empty.img'}
SPARSE_MAGIC = 0xED26FF3A


class Blocked(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Blocked(reason)


def partition_expanded_size(archive, member):
    """Return expanded logical bytes, not misleading sparse file byte length."""
    with archive.open(member) as stream:
        header = stream.read(28)
    if len(header) >= 4 and struct.unpack_from('<I', header)[0] == SPARSE_MAGIC:
        require(len(header) == 28, f'truncated Android sparse header: {member}')
        (magic, major, minor, file_header, chunk_header, block_size,
         blocks, chunks, checksum) = struct.unpack('<IHHHHIIII', header)
        require(major == 1 and file_header >= 28 and chunk_header >= 12,
                f'invalid Android sparse format: {member}')
        require(block_size >= 4096 and block_size % 4096 == 0 and blocks > 0 and chunks > 0,
                f'invalid Android sparse geometry: {member}')
        expanded = block_size * blocks
        require(expanded > 0, f'empty Android sparse image: {member}')
        return expanded, True
    require(archive.getinfo(member).file_size > 0, f'empty image: {member}')
    return archive.getinfo(member).file_size, False


def inspect(archive_path):
    require(archive_path.is_file(), f'archive absent: {archive_path}')
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        require(len(names) == len(set(names)), 'archive contains duplicate filenames')
        require(all(not name.startswith('/') and '..' not in name.split('/') and
                    '\\' not in name for name in names), 'unsafe archive path')
        require(all(not entry.flag_bits & 0x1 for entry in infos), 'encrypted archive member')
        require('build_info.txt' in names, 'missing build_info.txt')
        require(0 < archive.getinfo('build_info.txt').file_size <= 65536,
                'invalid build_info.txt size')
        image_names = {name for name in names if name.endswith('.img')}
        require(image_names == EXPECTED_IMAGES,
                'unexpected/missing image names: missing=' + repr(sorted(EXPECTED_IMAGES - image_names)) +
                ', extra=' + repr(sorted(image_names - EXPECTED_IMAGES)))
        require(all('/' not in name for name in image_names), 'images must be at archive root')

        # Do not unzip multi-gigabyte images: only read the bounded metadata record.
        try:
            metadata = archive.read('build_info.txt').decode('utf-8')
        except UnicodeError as exc:
            raise Blocked(f'non-UTF8 build metadata: {exc}') from exc
        info = {}
        for line in metadata.splitlines():
            if not line.strip():
                continue
            require('=' in line, 'invalid build_info.txt line')
            key, value = line.split('=', 1)
            require(key not in info, f'duplicate build info key {key}')
            info[key] = value
        required = {'device': 'r0s', 'model': 'SM-S901B', 'os_version': '16',
                    'use_dynamic_partitions': 'true',
                    'super_partition_size': str(SUPER_BYTES),
                    'super_partition_group': 'group_basic',
                    'super_group_basic_group_size': str(GROUP_BYTES)}
        for key, value in required.items():
            require(info.get(key) == value,
                    f'build_info {key}: expected {value!r}, got {info.get(key)!r}')
        for key in ('source_fingerprint', 'target_fingerprint'):
            fingerprint = info.get(key, '')
            require(fingerprint.startswith('samsung/') and ':16/' in fingerprint,
                    f'non-Samsung/Android-16 fingerprint: {key}')

        occupied = 0
        print('r0s native GZH3 target-files contents (read-only)')
        for partition in sorted(PARTITIONS):
            name = partition + '.img'
            expanded, sparse = partition_expanded_size(archive, name)
            require(expanded % 4096 == 0, f'{name} expanded image is not 4K aligned')
            occupied += expanded
            print(f'{name}: archive_bytes={archive.getinfo(name).file_size} '
                  f'expanded_bytes={expanded} sparse={str(sparse).lower()}')
        require(occupied <= GROUP_BYTES,
                f'expansion exceeds GZH3 group: {occupied} > {GROUP_BYTES}')
        for name, maximum in RAW_MAX.items():
            size, sparse = partition_expanded_size(archive, name)
            require(not sparse, f'{name} unexpectedly Android-sparse')
            require(size <= maximum, f'{name} larger than reference cap: {size} > {maximum}')
            print(f'{name}: {size} bytes (reference cap {maximum})')
        super_empty, _ = partition_expanded_size(archive, 'unsparse_super_empty.img')
        require(super_empty <= SUPER_BYTES, 'super-empty exceeds native super capacity')
        print(f'unsparse_super_empty.img: expanded_bytes={super_empty}')
        print(f'logical_total={occupied} native_group_cap={GROUP_BYTES}')
        print('TARGET-FILES STRUCTURE PRECHECK PASS — BOARD DEFERRED; NOT FLASH-QUALIFIED')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path, help='UN1CA-produced r0s target_files.zip')
    args = parser.parse_args()
    try:
        inspect(args.zip)
    except (Blocked, zipfile.BadZipFile, OSError, RuntimeError) as exc:
        print(f'r0s TARGET-FILES BLOCKED: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
