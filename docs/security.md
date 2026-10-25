# Tracera Security Model

This document describes the threat model, implemented controls, and residual risks for
Tracera's scan pipeline. It is intended to be read before deploying the service anywhere
beyond a local development machine.

## Threat model

Tracera's defining feature is that it fetches **attacker-influenced URLs on demand**. That
makes the backend an SSRF (server-side request forgery) target: a malicious caller can try
to use the scanner as a proxy to reach internal services, cloud metadata endpoints, or
otherwise-protected infrastructure. Secondary concerns are resource exhaustion (huge
responses, redirect chains, slowloris-style hangs) and abuse of the scan-creation endpoint
as a free HTTP proxy.

The scan itself is **passive**: it issues normal GET requests and never attempts
exploitation, fuzzing, or injection.

## Implemented controls

### URL validation (`backend/app/core/url_validator.py`)

- Scheme allowlist: only `http` and `https`.
- Hostname sanity checks; IP-literal hosts are parsed, not passed through blindly.
- Destination-port allowlist via `SCANNER_ALLOWED_PORTS` (default `[80, 443, 8080, 8443]`).
  Ports commonly used for internal services (PostgreSQL 5432, Redis 6379, etc.) are refused
  before any connection is attempted.

### IP blocking (`backend/app/core/ssrf_guard.py`)

`is_blocked_ip()` rejects targets in, for both IPv4 and IPv6:

- Loopback, unspecified, and link-local ranges
- RFC 1918 private ranges
- CGNAT (100.64.0.0/10)
- Benchmark/testing ranges (198.18.0.0/15)
- 6to4 relay prefix (192.88.99.0/24)
- NAT64 well-known prefix (64:ff9b::/96)
- IPv4-mapped IPv6 addresses (unwrapped and re-checked as IPv4)

`is_private_ip()` remains a strict RFC 1918 check and is kept separate for compatibility
with existing call sites and tests.

### DNS-rebinding mitigation (connection pinning)

The classic rebinding attack relies on a TOCTOU gap: validate the DNS answer, then let the
HTTP client resolve the name again and connect somewhere else. Tracera closes this gap by
pinning the connection:

1. The guard resolves the hostname and validates the resulting IP addresses.
2. The collector rewrites the request URL to the validated IP and attaches the original
   hostname via the `Host` header and `sni_hostname`, so TLS certificate identity is still
   checked against the intended name.
3. httpcore honors the explicit host/SNI and never performs a second DNS lookup for that
   request.

Tests in `backend/tests/test_collector_security.py` prove the pinning behavior (the DNS
resolver is never consulted a second time) and that redirect targets are revalidated.

### Redirect handling

Every redirect hop is run through the same validation pipeline (`validate_redirect_target`):
scheme, port, and resolved-IP checks are repeated for the new target. A redirect to a
blocked IP, blocked port, or non-HTTP(S) scheme aborts the scan with a finding/explanation
rather than following it. Redirect count is capped (`SCANNER_MAX_REDIRECTS`).

### Resource limits

- `SCANNER_TIMEOUT_SECONDS` — per-request timeout.
- `SCANNER_CONNECT_TIMEOUT_SECONDS` — connect timeout.
- `SCANNER_TOTAL_TIME_SECONDS` — wall-clock budget for the entire scan including redirects.
- `SCANNER_MAX_RESPONSE_BYTES` — maximum response body size.

### API hardening (`backend/app/api/v1/scans.py`)

- Scan creation is rate limited per client IP (`SCAN_RATE_LIMIT_MAX` requests per
  `SCAN_RATE_LIMIT_WINDOW_SECONDS`); excess requests get `429` with `Retry-After`.
- `limit` on list endpoints is capped at 100.
- A global exception handler returns a generic 500 without internal details.
- Timezone-aware timestamps are persisted and returned.

## Residual risks (known, accepted for now)

1. **No authentication or tenancy.** Anyone who can reach the API can create scans, read
   every scan, and download every report. Scans are global. This is the single largest gap
   and blocks any public deployment.
2. **In-memory rate limiter.** The limiter is per worker process and resets on restart.
   Behind multiple workers or hosts the effective limit multiplies. Replace with a shared
   store (Redis) before scaling out.
3. **DNS pinning covers A/AAAA at scan start.** CNAME chains are resolved through the
   system resolver and the final addresses are validated and pinned; a rebinding that
   happens *between* hops to a *new* hostname is revalidated per hop, but the TLS SNI
   verification relies on httpcore's handling of the pinned connection. Exotic resolver
   behavior is not individually re-verified.
4. **IPv6 transition tricks.** Blocked categories cover the well-known transition
   mechanisms (6to4, NAT64, mapped addresses), but the IPv6 space is large; new tunneling
   mechanisms would need to be added to `BLOCKED_NETWORKS`.
5. **No outbound egress allowlist.** The scanner can fetch any public site. If Tracera is
   deployed inside a network that treats outbound traffic as sensitive, run it in an
   egress-restricted network segment.
6. **No CSRF/auth hardening on mutations.** `POST /scans` is unauthenticated by design
   today; CORS is an allowlist but that is not a CSRF defense for non-browser clients.
7. **Information exposure via scan history.** Scan results reveal response metadata about
   scanned sites to anyone with API access; without auth this is effectively public.

## Pre-deployment checklist

Before exposing Tracera beyond localhost:

- [ ] Add authentication and per-user/project scan ownership with data isolation.
- [ ] Move the rate limiter to a shared store (Redis) or per-user quotas.
- [ ] Run the backend in an egress-controlled network segment; consider a dedicated egress
      proxy with its own allowlist.
- [ ] Set explicit `CORS_ORIGINS` for the deployed frontend origin.
- [ ] Ensure `DATABASE_URL` credentials are provisioned via a secrets manager, not dotenv.
- [ ] Review `SCANNER_ALLOWED_PORTS` — remove 8080/8443 if your threat model doesn't need them.
- [ ] Add request logging/audit trail for who scanned what.
- [ ] Re-run the full test suite (`pytest`, `npm run typecheck`, `npm test`, `npm run build`).
