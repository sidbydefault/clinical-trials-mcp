"""
Configuration management for the Clinical Trials MCP system.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database configuration
    database_url: str = Field(
        default="sqlite:///data/clinical_trials.db",
        description="Database connection URL"
    )

    # Vector store configuration
    vector_store_path: str = Field(
        default="data/vector_store",
        description="Path to vector store persistence directory"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")

    # MCP configuration
    mcp_server_name: str = Field(
        default="clinical-trials-mcp",
        description="MCP server name"
    )
    mcp_server_version: str = Field(
        default="0.1.0",
        description="MCP server version"
    )

    # Data paths
    data_dir: Path = Field(
        default=Path("data"),
        description="Base data directory"
    )

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings instance
    """
    return Settings()


def ensure_directories() -> None:
    """
    Ensure required directories exist.
    """
    settings = get_settings()

    directories = [
        settings.data_dir,
        settings.data_dir / "raw",
        settings.data_dir / "raw" / "clinical_trials",
        Path(settings.vector_store_path),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
