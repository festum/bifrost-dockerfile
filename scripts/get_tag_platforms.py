#!/usr/bin/env python3
"""Resolve all build platforms available for an upstream Docker Hub tag."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from typing import Any


def fetch_tag_detail(repository: str, tag: str) -> dict[str, Any]:
    namespace, name = repository.split("/", 1)
    base = f"https://hub.docker.com/v2/repositories/{namespace}/{name}/tags/{urllib.parse.quote(tag)}"
    with urllib.request.urlopen(base, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_platform(image: dict[str, Any]) -> str:
    os_name = (image.get("os") or "").strip().lower()
    arch = (image.get("architecture") or "").strip().lower()
    variant = (image.get("variant") or "").strip().lower()

    if not os_name or not arch or os_name == "unknown" or arch == "unknown":
        return ""

    platform = f"{os_name}/{arch}"
    if variant and variant != "unknown":
        platform = f"{platform}/{variant}"
    return platform


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def write_output(path: str, key: str, value: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Get platforms for Docker Hub tag")
    parser.add_argument("--repository", default="maximhq/bifrost")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    detail = fetch_tag_detail(args.repository, args.tag)
    images = detail.get("images", []) if isinstance(detail, dict) else []

    platforms = dedupe([
        p for p in (normalize_platform(img) for img in images if isinstance(img, dict)) if p
    ])

    result = {
        "repository": args.repository,
        "tag": args.tag,
        "platforms": platforms,
        "platforms_csv": ",".join(platforms),
        "count": len(platforms),
    }

    if args.github_output:
        write_output(args.github_output, "platforms", result["platforms_csv"])
        write_output(args.github_output, "platform_count", str(result["count"]))

    print(json.dumps(result))


if __name__ == "__main__":
    main()
