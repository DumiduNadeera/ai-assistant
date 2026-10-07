# Assumptions and Trade-offs

- The corpus and enterprise tools contain synthetic demonstration data.
- Hardcoded bearer identities keep the local POC repeatable; the authorization interface remains replaceable.
- The modular monolith keeps tracing and policy enforcement within one boundary while preserving extractable service ports.
- The default profile must run without paid credentials, so deterministic grounded synthesis and local hybrid retrieval remain supported.
- The evaluated semantic profile uses `text-embedding-3-small` at 1,536 dimensions; the Pinecone index must match that configuration.
- Model IDs remain environment configuration. `gpt-5-mini` is the default OpenAI profile, while deterministic synthesis is the default offline profile.
- The controlled RLM workflow demonstrates decomposition, concurrent targeted retrieval, evidence-based recursive refinement, bounded analysis, and aggregation within explicit depth and document budgets.
- Session memory and token buckets are in-process for the POC. This limits the API to one worker and does not survive restart.
- LangSmith is enabled only when its key and tracing flag are supplied. Synthetic demo content is the default trace payload.
- MCP tools and Python analysis are read-only. A future mutating tool requires human approval, stronger audit, and idempotency controls.
- The Streamlit UI prioritizes execution transparency, operational clarity, and portfolio demonstration value.
- Publishing a public repository, trace link, and demo video requires the project owner's accounts and remains outside local implementation.
