from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise AI Assistant"
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
    graph_timeout_seconds: float = 120.0
    max_graph_steps: int = 20
    max_rlm_depth: int = 2
    max_rlm_subqueries: int = 4
    max_rlm_documents: int = 12
    memory_max_messages: int = 20
    llm_provider: str = "deterministic"
    llm_model: str = "gpt-5-mini"
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_timeout_seconds: float = 90.0
    llm_max_output_tokens: int = 320
    ollama_think: bool = False
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    openai_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = ""
    langsmith_endpoint: str = ""
    langsmith_workspace_id: str = ""
    # Backward compatibility for deployments using the former variable names.
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "enterprise-ai-assistant"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def tracing_enabled(self) -> bool:
        return self.langsmith_tracing or self.langchain_tracing_v2

    @property
    def tracing_api_key(self) -> str:
        return self.langsmith_api_key or self.langchain_api_key

    @property
    def tracing_project(self) -> str:
        return self.langsmith_project or self.langchain_project


settings = Settings()
