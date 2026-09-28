"""
Shared test setup. The suite runs offline: no .env file, no network, no model download.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Every variable the code reads. Cleared before each test so a local .env or shell cannot leak in.
PROJECT_ENV_VARS = (
    "OPENROUTER_API_KEY",
    "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID",
    "META_VERIFY_TOKEN",
    "META_APP_SECRET",
    "WEBHOOK_VERIFY_TOKEN",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "GOOGLE_SHEET_ID",
)


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    for name in PROJECT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def load_module():
    """Import a file by path. Needed for agents/*, whose folder names contain hyphens."""
    return _load_module
