"""
Shared test configuration for just-dna-agents.

Loads .env at the repo root so API keys and tokens are available
for integration / agent smoke tests.
"""

from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "tests" / "fixtures" / "evals"

load_dotenv(REPO_ROOT / ".env")
