# bifrost-dockerfile

Extends the upstream [`maximhq/bifrost`](https://hub.docker.com/r/maximhq/bifrost) image and guarantees `npx` is available.

This repo adds `npx` support as a practical workaround for upstream gap tracked in [maximhq/bifrost#1548](https://github.com/maximhq/bifrost/issues/1548).

## What this repository does

- Builds from `maximhq/bifrost:<upstream-tag>`.
- Installs Node.js + npm only when `npx` is missing.
- Publishes images automatically with GitHub Actions.
- For each upstream tag, builds all platforms available in upstream tag metadata (not a fixed hardcoded platform list).
- Tracks already-processed upstream tags via git tags (`upstream/<tag>`).

## Local usage

Build from a specific upstream tag:

```bash
docker build --build-arg UPSTREAM_TAG=latest -t bifrost-npx:latest .
```

Verify `npx` in the built image:

```bash
docker run --rm bifrost-npx:latest sh -lc 'node --version && npm --version && npx --version'
```

## Automation workflow

Workflow file: `.github/workflows/build.yml`

Triggers:

- **Schedule** (`cron`): builds up to 3 lanes by default — `latest` + newest unprocessed stable tag + newest unprocessed pre-release tag (if any). Non-image artifact tags are skipped.
- **Manual dispatch**:
  - `backfill_all=true` builds unprocessed upstream tags, capped by `max_tags` (default `200`, hard ceiling `256`).
  - `explicit_tags` (comma-separated) force-builds selected upstream tags (for manual sync).
  - `max_tags` controls matrix size per run (default `200`, hard max `256`).

Per selected upstream tag, the workflow resolves the exact platform set from Docker Hub tag metadata (`maximhq/bifrost:<tag>`), then builds all resolved platforms for both image registries.

Outputs are pushed to:

- `ghcr.io/<github-owner>/bifrost-dockerfile:<upstream-tag>` (all platforms available on upstream tag)
- `ghcr.io/<github-owner>/bifrost-dockerfile:latest` (only for current newest upstream tag; uses that tag's resolved platform set)
- `docker.io/<dockerhub-user>/bifrost:<upstream-tag>` (all platforms available on upstream tag)
- `docker.io/<dockerhub-user>/bifrost:latest` (only for current newest upstream tag; uses that tag's resolved platform set)

## Required repository settings

### GitHub Actions permissions

The workflow uses:

- `contents: write` (to create/push marker tags `upstream/<tag>`)
- `packages: write` (to push images to GHCR)

### Secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

`DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN` are required because the workflow now pushes to Docker Hub and GHCR on each run.

## Tag utilities

List upstream tags:

```bash
python scripts/get_upstream_tags.py --repository maximhq/bifrost
```

Detect new tags (default: latest + newest unprocessed stable + newest unprocessed pre-release):

```bash
python scripts/detect_new_tags.py --repository maximhq/bifrost --latest-only true
```

Force selected tags (manual sync):

```bash
python scripts/detect_new_tags.py --repository maximhq/bifrost --explicit-tags "latest,v2.0.0-prerelease2"
```

Detect all missing tags (for backfill):

```bash
python scripts/detect_new_tags.py --repository maximhq/bifrost --latest-only false --max-tags 200
```
