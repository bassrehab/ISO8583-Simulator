# SPDX-FileCopyrightText: 2024-2026 Subhadip Mitra <contact@subhadipmitra.com>
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-iso8583sim-Commercial

"""Export the REST API's OpenAPI spec for the docs (docs/rest/openapi.json).

Run from the repository root (needs the web extra):

    python scripts/export_openapi.py          # write the spec
    python scripts/export_openapi.py --check  # exit 1 if the committed spec is stale
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "rest" / "openapi.json"


def build() -> str:
    from iso8583sim.web.app import create_app

    spec = create_app().openapi()
    # subhadipmitra@: The docs playground calls the first server by default: the public demo,
    # which has LLM features turned off. The local server is listed for everything else.
    spec["servers"] = [
        {"url": "https://api.iso8583sim.com", "description": "Public demo (LLM features off)"},
        {"url": "http://127.0.0.1:8000", "description": "Local server (iso8583sim web)"},
    ]
    # subhadipmitra@: A fixed version keeps the committed spec from changing on every release;
    # it only changes when the API itself does.
    spec["info"]["version"] = "1"
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the committed spec is out of date")
    args = parser.parse_args()
    text = build()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print(f"out of date: {OUT.relative_to(ROOT)}. Run: python scripts/export_openapi.py")
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
