# Top Commons

Research and analysis tools exploring a "top most viewed/downloaded images on Wikimedia Commons" list — analogous to [top.hatnote.com](https://top.hatnote.com) for Wikipedia articles.

## Scripts

| Script | Purpose |
|---|---|
| `organic_ranking.py` | Analyze SDC (Structured Data on Commons) usage vs Commons category membership rankings |
| `show_thumbs.py` | Fetch thumbnail usage statistics for Commons files |
| `show_thumbs_v2.py` | Improved thumbnail usage fetcher with additional analysis |
| `analyze_usage.py` | Analyze file usage across Wikimedia projects |
| `ascii_thumb.py` | Analyze ASCII thumbnail generation |

See [`REPORT.md`](REPORT.md) for the full research findings.

## Setup

No third-party packages are required — all scripts use only Python's standard library.

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Verify the environment (no packages to install)
pip list

# Run a script
python organic_ranking.py
```

> **Note:** Some scripts call out to `curl` (via `subprocess`) for API requests. `curl` is pre-installed on macOS and most Linux systems. If you're on a minimal system, install it via your package manager.

## Prerequisites

- Python 3.8+
- `curl` (for scripts that use subprocess-based API calls)

## Commands reference

```bash
# Activate venv (macOS/Linux)
source .venv/bin/activate

# Activate venv (Windows)
.venv\Scripts\activate

# Deactivate when done
deactivate
```
