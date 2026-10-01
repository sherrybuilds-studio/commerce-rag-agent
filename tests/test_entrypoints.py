"""
The documented run commands work without PYTHONPATH and from any working directory: the terminal chat
from the repo root, the webhook module from its own folder (cd agents/whatsapp-sales && uvicorn api:app),
and the cache file, which stays in rag/. The subprocess cases call no network service.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_python(args, cwd, stdin=""):
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["OPENROUTER_API_KEY"] = "test-key"
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, env=env, input=stdin, capture_output=True, text=True, timeout=120, check=False
    )


def test_terminal_chat_starts_from_the_repo_root():
    result = run_python(["agents/whatsapp-sales/bot.py"], cwd=ROOT, stdin="quit\n")

    assert result.returncode == 0, result.stderr
    assert "Type 'quit' to exit" in result.stdout


def test_webhook_module_imports_from_its_own_folder():
    result = run_python(["-c", "import api; print(api.app.title)"], cwd=ROOT / "agents" / "whatsapp-sales")

    assert result.returncode == 0, result.stderr


def test_cache_file_lives_next_to_the_cache_module():
    from rag import cache

    assert Path(cache.CACHE_FILE) == ROOT / "rag" / "cache.json"
