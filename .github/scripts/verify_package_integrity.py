#!/usr/bin/env python3
"""Repair Windows checkout line-ending conversion only when signed hashes prove the LF bytes are canonical."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: verify_package_integrity.py <package-directory>")
        return 2

    root = Path(sys.argv[1]).resolve()
    manifest_path = root / "integrity_manifest.json"
    if not manifest_path.is_file():
        print(f"ERROR: missing {manifest_path}")
        return 2

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read manifest: {exc}")
        return 2

    failures: list[str] = []
    normalized_count = 0
    files = manifest.get("files", {})
    for relative_path, expected in files.items():
        path = (root / relative_path).resolve()
        if root not in path.parents:
            failures.append(f"unsafe path: {relative_path}")
            continue
        if not path.is_file():
            failures.append(f"missing: {relative_path}")
            continue

        actual_bytes = path.read_bytes()
        if sha256(actual_bytes) == expected:
            continue

        # Windows Git checkout may convert canonical LF text files to CRLF.
        # Normalize only if the signed manifest proves the normalized bytes are exact.
        canonical_bytes = actual_bytes.replace(b"\r\n", b"\n")
        if canonical_bytes != actual_bytes and sha256(canonical_bytes) == expected:
            path.write_bytes(canonical_bytes)
            normalized_count += 1
        else:
            failures.append(f"hash mismatch: {relative_path}")

    if failures:
        print("Package integrity validation FAILED:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    sys.path.insert(0, str(root))
    try:
        from integrity_guard import verify_integrity
        ok, detail = verify_integrity(root)
    except Exception as exc:
        print(f"ERROR: cannot execute package integrity guard: {exc}")
        return 1

    if not ok:
        print(f"Package integrity guard FAILED: {detail}")
        return 1

    print(f"Package integrity validation PASSED: {len(files)} signed files verified; {normalized_count} line-ending conversions normalized.")
    print("Integrity guard result: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
