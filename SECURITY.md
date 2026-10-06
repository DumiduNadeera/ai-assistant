# Security Model

This repository contains a public assessment POC with synthetic data. Demo tokens are public fixtures and must never protect real information.

## Enforced controls

- Pydantic bounds message length and restricts session identifiers.
- Authentication derives the principal and role outside the graph.
- Per-user token buckets reject excess requests with `429` and `Retry-After`.
- Deterministic patterns deny prompt extraction, authorization bypass, administrative tool abuse, and bulk classified-data requests.
- Retrieved chunks are untrusted data. Chunks with instruction-like content are excluded from trusted evidence.
- Document classifications are filtered server-side by role before ranking.
- Tool permissions are centralized and rechecked directly before execution.
- Python analysis uses curated operations over bounded records and never evaluates user code.
- Citation IDs are created from and checked against validated evidence.
- Session ownership prevents a second demo identity from reading an existing session.
- Credentials come only from environment variables and are excluded from logs and source control.
- OpenAI requests use `store=False` in the provider adapter.

## Role policy

| Capability | Viewer | Analyst | Administrator |
|---|---:|---:|---:|
| Authorized document search | Yes | Yes | Yes |
| Python analysis | No | Yes | Yes |
| Read-only MCP tools | No | Yes | Yes |
| Restricted documents | No | No | Yes |

The MCP server contains synthetic data. Its client is reachable only after the graph's role gate. `MCP_TRANSPORT=stdio` runs the protocol path; local mode is a deterministic offline adapter.

## Production replacements

Before real deployment, replace demo auth with OIDC/JWT, use a centralized policy service, persist audit and memory data with retention controls, distribute rate limits through Redis, isolate tenants, add secrets management and DLP, authenticate the MCP transport, and complete a threat model and penetration test.
