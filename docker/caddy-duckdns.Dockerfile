FROM caddy:2.11.6-builder-alpine AS builder
RUN xcaddy build v2.11.6 --with github.com/caddy-dns/duckdns@v0.5.0

FROM caddy:2.11.6-alpine
COPY --from=builder /usr/bin/caddy /usr/bin/caddy
