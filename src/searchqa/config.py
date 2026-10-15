"""
Configuration loading for searchqa.

Reads Elasticsearch connection settings per environment from `.env`.
"""
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_DIR = PROJECT_ROOT / "repos" / "bigdata_elasticsearch"


class Environment(str, Enum):
    """Target Elasticsearch environment."""
    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"

    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """
        Convert string to Environment (case-insensitive).

        Args:
            value: Environment name.

        Returns:
            Environment enum instance.

        Raises:
            ValueError: If value is not a valid environment.
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid = ", ".join(e.value for e in cls)
            raise ValueError(f"Invalid env: {value}. Must be one of: {valid}") from None


DEFAULT_ENV = Environment.STAGE


@dataclass(frozen=True)
class ESConfig:
    """Connection settings for one Elasticsearch environment."""
    env: Environment
    host: str
    username: str
    password: str

    def __repr__(self) -> str:
        # Keep the password out of logs and tracebacks.
        return f"ESConfig(env={self.env.value}, host={self.host}, username={self.username})"


class ConfigLoader:
    """Loads settings from `.env` at the project root."""

    def __init__(self, env_file: Path | None = None):
        """
        Args:
            env_file: Path to the .env file. Defaults to `<project root>/.env`.
        """
        load_dotenv(env_file or PROJECT_ROOT / ".env")

    def es_config(self, env: Environment) -> ESConfig:
        """
        Build ESConfig for the given environment.

        Args:
            env: Target environment.

        Returns:
            ESConfig with host and credentials.

        Raises:
            ValueError: If any required variable is missing.
        """
        prefix = f"ES_{env.value.upper()}_"
        values = {key: os.getenv(prefix + key.upper(), "") for key in ("host", "username", "password")}
        missing = [prefix + key.upper() for key, value in values.items() if not value]
        if missing:
            raise ValueError(f"Missing in .env: {', '.join(missing)}")
        return ESConfig(
            env=env,
            host=values["host"].rstrip("/"),
            username=values["username"],
            password=values["password"],
        )

    @staticmethod
    def repo_url() -> str:
        """
        Returns:
            Git URL of the bigdata_elasticsearch repo.
        """
        return os.getenv("ES_REPO_URL", "git@github.com:PChome24h/bigdata_elasticsearch.git")
