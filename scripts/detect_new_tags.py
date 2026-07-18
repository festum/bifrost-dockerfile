#!/usr/bin/env python3
"""Detect upstream Docker Hub tags that were not built yet."""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


MAX_TAGS_DEFAULT = 200
MAX_TAGS_HARD_CEILING = 256


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


def parse_csv_tags(value: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in value.split(","):
        tag = raw.strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def parse_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def dedupe_preserve_order(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        deduped.append(tag)
    return deduped


def is_prerelease_tag(tag: str) -> bool:
    t = tag.lower()
    hints = ("prerelease", "alpha", "beta", "rc", "nightly", "preview")
    return any(h in t for h in hints)


def has_valid_platform(images: Any) -> bool:
    if not isinstance(images, list):
        return False
    for img in images:
        if not isinstance(img, dict):
            continue
        os_name = str(img.get("os") or "").strip().lower()
        arch = str(img.get("architecture") or "").strip().lower()
        if os_name and arch and os_name != "unknown" and arch != "unknown":
            return True
    return False


def fetch_recent_tag_entries(
    repository: str,
    max_pages: int = 5,
    page_size: int = 100,
) -> list[dict[str, Any]]:
    namespace, name = repository.split("/", 1)
    base = f"https://hub.docker.com/v2/repositories/{namespace}/{name}/tags"
    url = f"{base}?{urllib.parse.urlencode({'page_size': page_size})}"

    entries: list[dict[str, Any]] = []
    pages = 0
    while url and pages < max_pages:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))

        for raw in payload.get("results", []):
            if not isinstance(raw, dict):
                continue
            tag = raw.get("name")
            if not isinstance(tag, str) or not tag:
                continue
            entries.append({"name": tag, "buildable": has_valid_platform(raw.get("images", []))})

        pages += 1
        url = payload.get("next")

    return entries


def select_latest_only_tags(entries: list[dict[str, Any]], processed_tags: set[str]) -> list[str]:
    # Default mode should only check whether the newest buildable upstream tag is new.
    latest = next((e["name"] for e in entries if e.get("buildable")), "")
    if latest and latest not in processed_tags:
        return [latest]
    return []


def select_new_tags(upstream_tags: list[str], processed_tags: set[str], latest_only: bool) -> list[str]:
    unprocessed = [tag for tag in upstream_tags if tag not in processed_tags]
    if not latest_only:
        return unprocessed

    latest = upstream_tags[0] if upstream_tags else ""
    newest_unprocessed_stable = next(
        (tag for tag in upstream_tags[1:] if tag not in processed_tags and not is_prerelease_tag(tag)),
        "",
    )
    newest_unprocessed_prerelease = next(
        (tag for tag in upstream_tags[1:] if tag not in processed_tags and is_prerelease_tag(tag)),
        "",
    )
    selected = [tag for tag in [latest, newest_unprocessed_stable, newest_unprocessed_prerelease] if tag]
    return dedupe_preserve_order(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect new upstream tags")
    parser.add_argument("--repository", default="maximhq/bifrost")
    parser.add_argument("--latest-only", default="true")
    parser.add_argument("--explicit-tags", default="")
    parser.add_argument("--max-tags", default=str(MAX_TAGS_DEFAULT))
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    latest_only = parse_bool(args.latest_only)
    explicit_tags = parse_csv_tags(args.explicit_tags)
    processed_tags = get_processed_tags(prefix="upstream/")

    upstream_tags: list[str] = []
    if latest_only and not explicit_tags:
        # Keep latest-only behavior independent from backfill caps.
        recent_entries = fetch_recent_tag_entries(args.repository, max_pages=5)
        upstream_tags = [e["name"] for e in recent_entries if e.get("buildable")]
        new_tags = select_latest_only_tags(recent_entries, processed_tags)
    else:
        fetch_tags = _import_fetch_tags()
        upstream_tags = fetch_tags(args.repository)
        new_tags = select_new_tags(upstream_tags, processed_tags, latest_only)

    if explicit_tags:
        # Manual mode: allow forcing selected tags regardless of processed markers,
        # but keep only tags that exist upstream.
        if not upstream_tags:
            fetch_tags = _import_fetch_tags()
            upstream_tags = fetch_tags(args.repository)
        upstream_set = set(upstream_tags)
        new_tags = [t for t in explicit_tags if t in upstream_set]

    requested_max_tags = parse_int(args.max_tags, MAX_TAGS_DEFAULT)
    if requested_max_tags <= 0:
        requested_max_tags = MAX_TAGS_DEFAULT

    backfill_cap = min(requested_max_tags, MAX_TAGS_HARD_CEILING)
    if not latest_only and len(new_tags) > backfill_cap:
        new_tags = new_tags[:backfill_cap]

    # Safety net: never exceed GitHub Actions matrix hard limit.
    if len(new_tags) > MAX_TAGS_HARD_CEILING:
        new_tags = new_tags[:MAX_TAGS_HARD_CEILING]

    result: dict[str, Any] = {
        "repository": args.repository,
        "latest_only": latest_only,
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
