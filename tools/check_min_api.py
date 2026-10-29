#!/usr/bin/env python3
"""Fail if an Android driver imports bionic symbols newer than its minimum API.

bionic tags every symbol with the release that introduced it (LIBC, LIBC_N, LIBC_O, LIBC_P,
LIBC_Q, LIBC_R, ...). A driver built for a newer API can link symbols an older device does
not have, and dlopen then fails with "cannot locate symbol", which AdrenoTools hides by
silently falling back to the system driver. This reads the .so's undefined dynamic symbols
and reports any whose version tag is newer than the API the driver claims to support.

usage: check_min_api.py <libvulkan_freedreno.so> <min api, e.g. 29>
"""
import re
import subprocess
import sys

# bionic version tag -> first Android API level that has it.
TAG_API = {
    "LIBC": 1, "LIBC_N": 24, "LIBC_O": 26, "LIBC_P": 28, "LIBC_Q": 29, "LIBC_R": 30,
    "LIBC_S": 31, "LIBC_T": 33, "LIBC_U": 34, "LIBC_V": 35, "LIBC_W": 36,
}


def undefined_versioned(path):
    out = subprocess.run(["readelf", "--dyn-syms", "-W", path], check=True,
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        cols = line.split()
        # Num: Value Size Type Bind Vis Ndx Name
        if len(cols) < 8 or cols[6] != "UND":
            continue
        bind, name = cols[4], cols[7]
        m = re.match(r"([^@]+)@+(\S+)", name)
        if m:
            yield m.group(1), m.group(2), bind


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    path, min_api = sys.argv[1], int(sys.argv[2])
    too_new, unknown = [], set()
    for sym, tag, bind in undefined_versioned(path):
        if not tag.startswith("LIBC"):
            continue
        api = TAG_API.get(tag)
        if api is None:
            unknown.add(tag)
            continue
        if api > min_api and bind != "WEAK":
            too_new.append((api, tag, sym))
    if unknown:
        print(f"note: unrecognised bionic version tags (treated as OK): {', '.join(sorted(unknown))}")
    if too_new:
        print(f"FAIL: {path} imports {len(too_new)} symbol(s) newer than API {min_api}:")
        for api, tag, sym in sorted(too_new):
            print(f"  {sym}@{tag} (API {api})")
        sys.exit(1)
    print(f"OK: every versioned bionic import in {path} exists on API {min_api}")


if __name__ == "__main__":
    main()
