"""
agent/visitor_log.py

Logs every page visit to a private HuggingFace dataset.
Persists across Space restarts. Read it from your laptop anytime.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────

_DATASET_REPO = "sanjay/pentrace-visits"   # your private HF dataset repo
_LOG_FILE     = "visits.jsonl"             # file inside the dataset
_LOCAL_CACHE  = Path("/tmp/visits.jsonl")  # temp write before push


def log_visit() -> None:
    """
    Fire-and-forget. Runs in a background thread so it never
    blocks the Streamlit page load.
    """
    threading.Thread(target=_push_visit, daemon=True).start()


def _push_visit() -> None:
    token = os.environ.get("HF_VISIT_TOKEN")
    if not token:
        # Running locally — just write to a local file, no push needed
        _write_local()
        return

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)

        entry = _make_entry()

        # Download existing file if it exists, append, re-upload
        try:
            api.hf_hub_download(
                repo_id   = _DATASET_REPO,
                filename  = _LOG_FILE,
                repo_type = "dataset",
                local_dir = "/tmp",
            )
            existing = _LOCAL_CACHE.read_text(encoding="utf-8")
        except Exception:
            existing = ""

        updated = existing + json.dumps(entry) + "\n"
        _LOCAL_CACHE.write_text(updated, encoding="utf-8")

        api.upload_file(
            path_or_fileobj = str(_LOCAL_CACHE),
            path_in_repo    = _LOG_FILE,
            repo_id         = _DATASET_REPO,
            repo_type       = "dataset",
            commit_message  = f"visit {entry['ts']}",
        )

    except Exception as exc:
        # Never crash the app over analytics
        print(f"[visitor_log] push failed: {exc}")


def _make_entry() -> dict:
    return {
        "ts"     : datetime.now(timezone.utc).isoformat(),
        "source" : os.environ.get("SPACE_ID", "local"),
    }


def _write_local() -> None:
    """Fallback for local dev — writes to data/visits.json."""
    path = Path(__file__).parent.parent / "data" / "visits.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(_make_entry()) + "\n")