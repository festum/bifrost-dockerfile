# bifrost-dockerfile

Extends the upstream [`maximhq/bifrost`](https://hub.docker.com/r/maximhq/bifrost) image and guarantees `npx` is available.

This repo adds `npx` support as a practical workaround for upstream gap tracked in [maximhq/bifrost#1548](https://github.com/maximhq/bifrost/issues/1548).

## What this repository does

- Builds from `maximhq/bifrost:<upstream-tag>`.
- Installs Node.js + npm only when `npx` is missing.
- Publishes images automatically with GitHub Actions.
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

- **Schedule** (`cron`): checks Docker Hub and builds only the newest unprocessed upstream tag.
- **Manual dispatch**: optional `backfill_all=true` to build every unprocessed upstream tag.

Outputs are pushed to:

- `ghcr.io/<github-owner>/bifrost-dockerfile:<upstream-tag>`
- `ghcr.io/<github-owner>/bifrost-dockerfile:latest` (only for current newest upstream tag)
- `docker.io/<dockerhub-user>/bifrost-dockerfile:<upstream-tag>`
- `docker.io/<dockerhub-user>/bifrost-dockerfile:latest` (only for current newest upstream tag)

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

Detect new tags (default: latest only):

```bash
python scripts/detect_new_tags.py --repository maximhq/bifrost --latest-only true
```

Detect all missing tags (for backfill):

```bash
python scripts/detect_new_tags.py --repository maximhq/bifrost --latest-only false
```
