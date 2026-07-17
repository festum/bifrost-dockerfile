# syntax=docker/dockerfile:1.7
ARG NODE_FALLBACK_IMAGE=node:20-bookworm-slim
ARG UPSTREAM_TAG=latest
FROM ${NODE_FALLBACK_IMAGE} AS node_fallback

FROM maximhq/bifrost:${UPSTREAM_TAG}

USER root
SHELL ["/bin/sh", "-euxo", "pipefail", "-c"]

RUN --mount=from=node_fallback,src=/usr/local,target=/node-local \
    if command -v npx >/dev/null 2>&1; then \
      exit 0; \
    fi; \
    install_npm_with_rpm_pm() { \
      pm="$1"; \
      "$pm" install -y nodejs npm \
      || "$pm" install -y npm \
      || "$pm" install -y nodejs \
      || "$pm" install -y nodejs20 npm \
      || "$pm" install -y nodejs20 \
      || "$pm" install -y nodejs18 npm \
      || "$pm" install -y nodejs18 \
      || true; \
    }; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs npm; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache nodejs npm; \
    elif command -v microdnf >/dev/null 2>&1; then \
      install_npm_with_rpm_pm microdnf; \
      microdnf clean all; \
    elif command -v dnf >/dev/null 2>&1; then \
      install_npm_with_rpm_pm dnf; \
      dnf clean all; \
    elif command -v yum >/dev/null 2>&1; then \
      install_npm_with_rpm_pm yum; \
      yum clean all; \
    fi; \
    if ! command -v node >/dev/null 2>&1; then \
      cp -a /node-local/. /usr/local/; \
    fi; \
    command -v npx >/dev/null 2>&1 || npm install -g npx; \
    node --version; \
    npm --version; \
    npx --version

USER 1000:0
