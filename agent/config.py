"""
agent/config.py
---------------
Central configuration for PentraceAI.

Loads all settings from environment variables at import time.
Fails fast with a clear, actionable error if anything is missing or malformed.

All other agent modules import from here — never from os.environ directly.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# ── Logging ───────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_RETRIES: int = 3
RETRY_BACKOFF_SECONDS: float = 1.5
HTTP_TIMEOUT_SECONDS: int = 10
CONFIDENCE_THRESHOLD: float = 0.6
CHROMA_COLLECTION_NAME: str = "pentrace_knowledge"

# Expected API version format: YYYY-MM-DD or YYYY-MM-DD-preview
_API_VERSION_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(-preview)?$")

# ── Config dataclass ──────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    """
    Immutable settings object built from environment variables.

    Frozen so nothing can accidentally mutate config at runtime.
    All fields are required — missing any will raise at startup.
    """

    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    sandbox_base_url: str
    nvd_base_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0"


# ── Validation helpers ────────────────────────────────────────────────────────

def _require(key: str) -> str:
    """
    Read an environment variable or raise immediately with a clear message.

    Args:
        key: The environment variable name.

    Returns:
        The stripped, non-empty value of the environment variable.

    Raises:
        EnvironmentError: If the variable is not set or is empty.
    """
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is missing or empty.\n"
            f"Expected location: {Path('.env').resolve()}\n"
            f"Add this line to your .env file: {key}=your_value_here"
        )
    return value


def _validate_url(key: str, value: str) -> str:
    """
    Validate that a config value looks like a URL.

    Args:
        key: The environment variable name (for error messages).
        value: The value to validate.

    Returns:
        The value unchanged if valid.

    Raises:
        EnvironmentError: If the value does not start with http:// or https://.
    """
    if not value.startswith(("http://", "https://")):
        raise EnvironmentError(
            f"Environment variable '{key}' must be a valid URL starting with "
            f"http:// or https://. Got: '{value}'"
        )
    return value


def _validate_api_version(key: str, value: str) -> str:
    """
    Validate that the API version matches the expected Azure format.

    Args:
        key: The environment variable name (for error messages).
        value: The value to validate.

    Returns:
        The value unchanged if valid.

    Raises:
        EnvironmentError: If the value does not match YYYY-MM-DD or YYYY-MM-DD-preview.
    """
    if not _API_VERSION_PATTERN.match(value):
        raise EnvironmentError(
            f"Environment variable '{key}' must match format YYYY-MM-DD or "
            f"YYYY-MM-DD-preview. Got: '{value}'"
        )
    return value


# ── Loader ────────────────────────────────────────────────────────────────────

def _load_settings() -> Settings:
    """
    Build and return the Settings object from environment variables.

    Locates and loads the .env file, validates all required variables,
    and returns an immutable Settings instance. Any missing or malformed
    variable raises immediately so the system never starts in a broken state.

    Returns:
        A fully populated, immutable Settings instance.

    Raises:
        EnvironmentError: If the .env file is missing, or any required
                          variable is absent or malformed.
    """
    env_path = Path(".env")

    if not env_path.exists():
        raise EnvironmentError(
            f".env file not found at {env_path.resolve()}.\n"
            f"Copy .env.example to .env and fill in your values."
        )

    load_dotenv(dotenv_path=env_path)

    endpoint = _validate_url(
        "AZURE_OPENAI_ENDPOINT",
        _require("AZURE_OPENAI_ENDPOINT"),
    )
    api_key = _require("AZURE_OPENAI_API_KEY")
    api_version = _validate_api_version(
        "AZURE_OPENAI_API_VERSION",
        _require("AZURE_OPENAI_API_VERSION"),
    )
    chat_deployment = _require("AZURE_OPENAI_CHAT_DEPLOYMENT")
    embedding_deployment = _require("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    sandbox_base_url = _validate_url(
        "SANDBOX_BASE_URL",
        _require("SANDBOX_BASE_URL"),
    )

    settings = Settings(
        azure_openai_endpoint=endpoint,
        azure_openai_api_key=api_key,
        azure_openai_api_version=api_version,
        azure_openai_chat_deployment=chat_deployment,
        azure_openai_embedding_deployment=embedding_deployment,
        sandbox_base_url=sandbox_base_url,
    )

    logger.info(
        "PentraceAI config loaded | endpoint=%s | chat=%s | embedding=%s | sandbox=%s",
        settings.azure_openai_endpoint,
        settings.azure_openai_chat_deployment,
        settings.azure_openai_embedding_deployment,
        settings.sandbox_base_url,
    )

    return settings


# ── Module-level singleton ────────────────────────────────────────────────────
# Loaded once at import time. All modules import this object.

settings = _load_settings()