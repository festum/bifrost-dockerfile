#!/usr/bin/env python3
"""Resolve tags from Docker Hub for maximhq/bifrost."""

from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from typing import Any


def fetch_tags(repository: str, page_size: int = 100) -> list[str]:
    namespace, name = repository.split("/", 1)
    base_url = f"https://hub.docker.com/v2/repositories/{namespace}/{name}/tags"
    url = f"{base_url}?{urllib.parse.urlencode({'page_size': page_size})}"
    tags: list[str] = []

    while url:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        for entry in payload.get("results", []):
            tag_name = entry.get("name")
            if isinstance(tag_name, str) and tag_name:
                tags.append(tag_name)
        url = payload.get("next")

    return tags


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Docker Hub tags as JSON")
    parser.add_argument("--repository", default="maximhq/bifrost")
    args = parser.parse_args()

    tags = fetch_tags(args.repository)
    print(json.dumps(tags))


if __name__ == "__main__":
    main()
