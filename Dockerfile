ARG UPSTREAM_TAG=latest
FROM maximhq/bifrost:${UPSTREAM_TAG}

USER root
SHELL ["/bin/sh", "-euxo", "pipefail", "-c"]

RUN if command -v npx >/dev/null 2>&1; then \
      exit 0; \
    fi; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends nodejs npm; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk add --no-cache nodejs npm; \
    elif command -v microdnf >/dev/null 2>&1; then \
      microdnf install -y nodejs npm; \
      microdnf clean all; \
    elif command -v dnf >/dev/null 2>&1; then \
      dnf install -y nodejs npm; \
      dnf clean all; \
    elif command -v yum >/dev/null 2>&1; then \
      yum install -y nodejs npm; \
      yum clean all; \
    else \
      echo "No supported package manager found to install npm/npx" >&2; \
      exit 1; \
    fi; \
    command -v npx >/dev/null 2>&1 || npm install -g npx; \
    node --version; \
    npm --version; \
    npx --version

USER 1000:0
