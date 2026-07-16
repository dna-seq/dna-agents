from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Runtime configuration for the DNA Agents MCP server.

    Values can be overridden via ``JUST_DNA_AGENTS_MCP_*`` environment variables or a
    local ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_prefix="JUST_DNA_AGENTS_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    output_dir: str = Field(
        default=".",
        description="Default output directory for module spec files.",
    )
    resolve_with_ensembl: bool = Field(
        default=True,
        description="Resolve missing rsid/position via Ensembl DuckDB.",
    )


def get_settings() -> Settings:
    return Settings()
