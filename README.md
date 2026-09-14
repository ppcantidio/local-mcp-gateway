# local-mcp-gateway

CLI: **`lmg`**

Expose localhost MCP servers (Paper Desktop, etc.) through a small authenticated proxy and a pluggable tunnel (Tailscale Funnel, Cloudflare Tunnel, or ngrok) so **Cursor Cloud Agents** and other remote clients can reach them.

## Why this exists

Paper Desktop only listens on loopback. Cloud Agents cannot reach `127.0.0.1` on your laptop.

Two constraints that bite in practice:

1. **Host rewrite.** Paper rejects MCP requests unless the HTTP `Host` header is `127.0.0.1:29979` (DNS-rebinding protection). Tailscale / Cloudflare / ngrok send their public hostname → Paper returns `403 Invalid host`. The gateway rewrites `Host` and strips `Authorization`, `Cookie`, and `Origin` before proxying upstream.
2. **Public HTTPS for Cloud HTTP MCP.** Cursor Cloud Agent HTTP MCP is proxied from Cursor’s backend, which is **not** on your tailnet. A tailnet-only URL (`tailscale serve` without Funnel) is unreachable. Use Funnel, Cloudflare, or ngrok for Cloud Agents. Tailnet-only `serve` is still valid for other tailnet clients.

## Install

```bash
# from this repo
uv sync
uv run lmg --help

# or as a tool
uv tool install .
# later: uv tool install git+https://github.com/ppcantidio/local-mcp-gateway
```

Requires Python 3.12+.

## Quick start

```bash
lmg init                          # writes ./lmg.toml, prints LMG_API_KEY once
export LMG_API_KEY=...            # paste the key from init / keygen

# Paper Desktop open with a file loaded (confirms http://127.0.0.1:29979/mcp)
lmg serve --publisher tailscale --mode funnel
```

Register more local MCPs (file **or** CLI):

```bash
lmg add paper http://127.0.0.1:29979 --rewrite-host 127.0.0.1:29979
lmg add other http://127.0.0.1:3100
lmg ls
lmg rm other

# ephemeral for one run
lmg serve --publisher local --mcp demo=http://127.0.0.1:3200
```

Config search order: `--config` → `./lmg.toml` → `~/.config/lmg/config.toml`.

`LMG_API_KEY` is required for `serve`. It is never written to the TOML file and never logged.

## Routing

Each registered MCP is exposed under its name:

| Local upstream | Public URL |
| --- | --- |
| `paper` → `http://127.0.0.1:29979/mcp` | `https://<published-host>/paper/mcp` |

`GET /` and `GET /healthz` are unauthenticated (tunnel probes). Everything else requires `Authorization: Bearer <LMG_API_KEY>`.

## Publishers

| Name | Mode | Public? | Notes |
| --- | --- | --- | --- |
| `local` | — | No | `http://127.0.0.1:<port>` — tests / laptop only |
| `tailscale` | `serve` | Tailnet only | Not enough for Cursor Cloud HTTP MCP |
| `tailscale` | `funnel` | Yes | Public HTTPS; needs Funnel enabled on the tailnet |
| `cloudflare` | — | Yes | `cloudflared tunnel --url …` (quick tunnel) |
| `ngrok` | — | Yes | `ngrok http <port>` |

The proxy only binds localhost. A **Publisher** starts after the server is listening and returns the public origin. Adding a publisher = one module + registry entry (no `if publisher ==` in the proxy).

CLIs must already be on `PATH`. Missing binary errors include an install hint.

**Tailscale stop:** `lmg` turns off the `--https=443` serve/funnel mapping it created. It does not wipe unrelated Tailscale serve routes; if you share port 443 with other mappings, stop carefully.

## Cursor plugin (Cloud Agents)

This repo is a **Team Marketplace**. Import it so Cloud Agents can use Paper over your public gateway.

1. Dashboard → **Plugins** → **Team Marketplaces** → **Add Marketplace** → import  
   `https://github.com/ppcantidio/local-mcp-gateway`
2. Install the **paper** plugin.
3. **Configure** variables (same fixed values as your laptop):

| Variable | Example |
| --- | --- |
| `LMG_PAPER_MCP_URL` | `https://laptop-de-pedro.tail0ee25d.ts.net/paper/mcp` |
| `LMG_API_KEY` | value from `~/.config/lmg/env` |

4. Enable the MCP for Cloud Agents at [cursor.com/agents](https://cursor.com/agents).
5. Keep `lmg serve` + Paper Desktop running on the Mac while agents work.

Plugin sources live under `plugins/paper/` (manifest + `mcp.json`). Never commit API keys.

## Security

Funnel / Cloudflare / ngrok put a **public** HTTPS endpoint on the internet. The API key is the only gate.

- Generate a long `token_urlsafe` key (`lmg keygen`)
- Rotate when shared or leaked
- Never commit `LMG_API_KEY` or a TOML file that contains secrets
- Turn Funnel / tunnels off when idle

## CLI

| Command | Purpose |
| --- | --- |
| `lmg init` | Write `lmg.toml` from the example; print a key once |
| `lmg keygen` | Print a new key (not written to disk) |
| `lmg add NAME URL` | Register a local MCP |
| `lmg ls` / `lmg rm NAME` | List / remove |
| `lmg serve` | Start proxy + publisher |

## Develop

```bash
uv sync
uv run pytest
uv run ruff check
uv run ty check
```

### Package layout

```
src/local_mcp_gateway/
  cli/          # Typer entrypoint (`lmg`) — thin UX layer
  config/       # TOML models, file IO, env secrets (LMG_API_KEY)
  proxy/        # Starlette app: auth, routing, Host rewrite, SSE
  publishers/   # Pluggable tunnels (local / tailscale / cloudflare / ngrok)
  runtime/      # Process runner + proxy/publisher lifecycle
  data/         # Packaged example TOML
  errors.py     # Shared exceptions
```

## Out of scope (v1)

OAuth / Tailscale identity headers, Windows-specific installers, putting this in the Spryx monorepo, committing API keys.
