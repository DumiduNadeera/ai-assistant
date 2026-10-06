from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Orysys Commercial Bank AI Assistant"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    rate_limit_capacity: int = 20
    rate_limit_refill_per_second: float = 0.2
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    pinecone_namespace: str = "enterprise-demo"
    hybrid_dense_weight: float = 0.55
    retrieval_top_k: int = 5
    retrieval_timeout_seconds: float = 8.0
    tool_timeout_seconds: float = 5.0
    mcp_transport: str = "local"
    graph_timeout_seconds: float = 30.0
    max_graph_steps: int = 20
    max_rlm_depth: int = 2
    max_rlm_subqueries: int = 4
    max_rlm_documents: int = 12
    memory_max_messages: int = 20
    llm_provider: str = "deterministic"
    llm_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "orysys-enterprise-assistant"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
