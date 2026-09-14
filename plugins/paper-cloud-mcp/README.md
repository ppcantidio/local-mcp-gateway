# Paper Cloud MCP

Cursor plugin that points **Cloud Agents** at Paper Desktop through your laptop gateway.

This is **not** the local Paper Desktop MCP (`http://127.0.0.1:29979/mcp`). Use that for IDE-on-laptop; use this plugin for Cloud Agents only.

## Variables (Dashboard → Plugins → Configure)

| Variable | Value |
| --- | --- |
| `LMG_PAPER_MCP_URL` | Public URL from `lmg serve`, e.g. `https://laptop-de-pedro.tail0ee25d.ts.net/paper/mcp` |
| `LMG_API_KEY` | Fixed Bearer token from `~/.config/lmg/env` (never commit) |

## On the Mac

```bash
# Paper Desktop open + file loaded
lmg serve   # publisher: tailscale funnel (see ~/.config/lmg/config.toml)
```

## Install

Import this GitHub repo as a **Team Marketplace**, then install **paper-cloud-mcp** and set the variables above. Enable it for Cloud Agents at [cursor.com/agents](https://cursor.com/agents).
