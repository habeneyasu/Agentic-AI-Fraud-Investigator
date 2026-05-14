"""
Repo-root entry for hosts that run `streamlit run streamlit_app.py` (e.g. some HF defaults).

The real app lives at `dashboard/streamlit_app.py`. The supported production path is
Docker (`Dockerfile` + `scripts/run_oneapp.sh` → `dashboard/streamlit_app.py`).
"""

from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parent / "dashboard" / "streamlit_app.py"
if not _TARGET.is_file():
    raise FileNotFoundError(f"Expected dashboard at {_TARGET}")
runpy.run_path(str(_TARGET), run_name="__main__")
