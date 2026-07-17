#!/usr/bin/env python3
"""Detect upstream Docker Hub tags that were not built yet."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def _import_fetch_tags():
    import importlib.util

    script_path = Path(__file__).with_name("get_upstream_tags.py")
    spec = importlib.util.spec_from_file_location("get_upstream_tags", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load get_upstream_tags.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module.fetch_tags


def get_processed_tags(prefix: str = "upstream/") -> set[str]:
    try:
        output = subprocess.check_output(
            ["git", "tag", "--list", f"{prefix}*"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        return set()

    processed: set[str] = set()
    for line in output.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            processed.add(line[len(prefix) :])
    return processed


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect new upstream tags")
    parser.add_argument("--repository", default="maximhq/bifrost")
    parser.add_argument("--latest-only", default="true")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    fetch_tags = _import_fetch_tags()
    upstream_tags: list[str] = fetch_tags(args.repository)
    processed_tags = get_processed_tags(prefix="upstream/")

    new_tags = [tag for tag in upstream_tags if tag not in processed_tags]
    if parse_bool(args.latest_only):
        new_tags = new_tags[:1]

    result: dict[str, Any] = {
        "repository": args.repository,
        "latest_only": parse_bool(args.latest_only),
        "latest_upstream": upstream_tags[0] if upstream_tags else "",
        "new_tags": new_tags,
        "new_tags_count": len(new_tags),
    }

    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"latest_upstream={result['latest_upstream']}\n")
            handle.write(f"new_tags_json={json.dumps(result['new_tags'])}\n")
            handle.write(f"new_tags_count={result['new_tags_count']}\n")

    print(json.dumps(result))


if __name__ == "__main__":
    main()
