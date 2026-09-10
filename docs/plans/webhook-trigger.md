# Plan: Replace Cron Schedule with Docker Hub Webhook Trigger

## Problem
The current hourly cron polls Docker Hub every 60 minutes. New tags are delayed up to an hour before being detected. A webhook would trigger builds within seconds of a push.

## Architecture

```
Docker Hub (push event)
    ↓ POST webhook payload
Cloudflare Worker (relay)
    ↓ POST /repos/{owner}/{repo}/dispatches
GitHub Actions (repository_dispatch)
    ↓
detect_new_tags.py → build-and-push
```

Docker Hub webhooks can't directly call GitHub's API (requires a PAT/App token), so a small relay is needed.

## Components to Create/Modify

### 1. `worker/index.js` — Cloudflare Worker relay (~30 lines)
- Receives Docker Hub webhook POST
- Extracts repo name and tag from payload
- POSTs to GitHub `repository_dispatch` API with a PAT secret
- Returns 200 to Docker Hub

### 2. `.github/workflows/build.yml` — Add `repository_dispatch` trigger
- Add `on: repository_dispatch` with event type `dockerhub-push`
- Keep existing `schedule` as fallback (reduce from hourly to every 12 hours)
- The detect + build jobs remain unchanged — they already handle tag detection

### 3. Docker Hub webhook config (manual, not in code)
- Webhook URL: `https://bifrost-webhook.<subdomain>.workers.dev`
- Trigger: "Push to a repository"

## Secrets Required
- `WORKER_GITHUB_PAT`: Personal access token with `repo` scope, stored in Cloudflare Worker env

## Fallback Strategy
- Keep cron schedule but reduce to every 12 hours (safety net if webhook misses)
- The existing `detect_new_tags.py` idempotently handles already-processed tags via marker tags

## Files Changed
| File | Change |
|------|--------|
| `worker/index.js` | New — Cloudflare Worker relay |
| `.github/workflows/build.yml` | Add `repository_dispatch` trigger, reduce cron frequency |

## Verification
1. Deploy worker: `cd worker && npx wrangler deploy`
2. Configure webhook in Docker Hub → trigger test push
3. Verify `repository_dispatch` event fires and workflow runs
4. Confirm existing `upstream/<tag>` markers prevent duplicate builds
