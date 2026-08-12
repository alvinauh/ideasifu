# Web tier: Caddy serving the pre-built SPA (built on the host with
# VITE_API_BASE_URL=/api) plus an /api reverse proxy to the API container.
# The SPA is built outside Docker (see start.sh / `npm run build`) so this
# image needs no Node toolchain or npm registry access.
FROM caddy:2-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY dist /srv
