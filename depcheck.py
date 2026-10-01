#!/usr/bin/env python3
"""
depcheck.py - Simple dependency existence checker (supply-chain attack detection aid)

Usage:
    python depcheck.py <language> <dependency-file>

Example:
    python depcheck.py npm package.json
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Dict, List, Set

def usage():
    print("Usage: python depcheck.py <language> <dependency-file>")
    print("Supported languages right now: npm")
    print("Example: python depcheck.py npm package.json")
    sys.exit(1)

def load_npm_dependencies(file_path: str) -> Set[str]:
    """Extract all package names from package.json (dependencies + devDependencies)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {file_path}: {e}")
        sys.exit(1)

    deps: Set[str] = set()

    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        section_deps = data.get(section, {})
        if isinstance(section_deps, dict):
            deps.update(section_deps.keys())

    return deps

def package_exists_on_npm(package_name: str) -> bool:
    encoded_name = package_name.replace("/", "%2F")
    url = f"https://registry.npmjs.org/{encoded_name}"

    # Create SSL context (prefer certifi if available)
    context = None
    try:
        import certifi
        import ssl
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass  # use default system certificates

    try:
        with urllib.request.urlopen(url, context=context, timeout=10) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        print(f"[WARN] Unexpected HTTP {e.code} while checking '{package_name}'")
        return True
    except Exception as e:
        print(f"[WARN] Network error while checking '{package_name}': {e}")
        return True

def check_npm(file_path: str) -> None:
    packages = load_npm_dependencies(file_path)

    if not packages:
        print("No dependencies found in the file.")
        return

    print(f"Checking {len(packages)} package(s) against the npm registry...\n")

    missing: List[str] = []
    existing: List[str] = []

    for pkg in sorted(packages):
        print(f"  → {pkg} ... ", end="", flush=True)
        if package_exists_on_npm(pkg):
            print("OK")
            existing.append(pkg)
        else:
            print("MISSING / DOES NOT EXIST")
            missing.append(pkg)

    print("\n" + "=" * 60)
    print(f"Summary: {len(existing)} found, {len(missing)} missing")
    print("=" * 60)

    if missing:
        print("\n[!] The following packages do NOT exist on the public npm registry:")
        for pkg in missing:
            print(f"    - {pkg}")
        print("\nThese could be typos, private packages, or indicators of a "
              "possible supply-chain / dependency-confusion attack.")
        sys.exit(2)  # non-zero exit code for automation / CI
    else:
        print("\nAll packages exist on the public npm registry.")
        sys.exit(0)

def main():
    if len(sys.argv) != 3:
        usage()

    language = sys.argv[1].lower()
    file_path = sys.argv[2]

    if language == "npm":
        check_npm(file_path)
    else:
        print(f"[ERROR] Language '{language}' is not supported yet.")
        print("Currently supported: npm")
        sys.exit(1)

if __name__ == "__main__":
    main()
