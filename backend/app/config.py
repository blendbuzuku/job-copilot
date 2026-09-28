"""App settings, read from environment variables (or a .env file)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    database_url: str = "postgresql+psycopg://copilot:copilot@localhost:5432/copilot"
    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-5"
    # Small, fast embedding model that runs locally on the CPU (384 numbers per text)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    # How similar a CV line must be to a job requirement to count as a match (0 to 1)
    match_threshold: float = 0.75
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def demo_mode(self) -> bool:
        """No real API key set: use example answers instead of calling Claude."""
        key = self.anthropic_api_key.strip()
        return not key or key.endswith("...")


settings = Settings()
