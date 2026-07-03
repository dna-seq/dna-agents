"""
Agent evaluation tests using claude CLI in print mode.

These tests run the module-creator agent against freeform eval inputs,
then score the output against ground-truth references. They use your
Claude Code subscription (no API key needed).

Ground truth is loaded from HF parquet modules where available,
falling back to local spec directories for modules not on HF
(e.g. pharmacogenomics).

Run with:
    uv run pytest tests/test_agent_evals.py -v -m agent_eval

Configure via environment variables:
    CLAUDE_MODEL       — model override (e.g. "sonnet", "opus")
    EVAL_MIN_OVERALL   — minimum overall score (default: 0.70)
    EVAL_MIN_RECALL    — minimum variant recall (default: 0.60)
    EVAL_TIMEOUT       — claude process timeout in seconds (default: 600)
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from dna_agents.eval_scorer import score_module

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_DIR = REPO_ROOT / "data" / "evals"

MIN_OVERALL = float(os.environ.get("EVAL_MIN_OVERALL", "0.70"))
MIN_RECALL = float(os.environ.get("EVAL_MIN_RECALL", "0.60"))
TIMEOUT = int(os.environ.get("EVAL_TIMEOUT", "600"))

# Eval cases: (name, reference_source, optional rsid_filter)
# reference_source is an HF module name or a local spec dir
EVAL_CASES = [
    ("cyp_panel", None, None),  # uses local spec dir
    ("sirtuin_longevity", "longevitymap", {
        "rs3758391", "rs12778366", "rs7896005", "rs4746720",
        "rs11555236", "rs4980329", "rs107251",
    }),
]


def _run_claude_agent(freeform_input: str, output_dir: Path) -> subprocess.CompletedProcess:
    """Run the module-creator agent via claude CLI in print mode."""
    cmd = [
        "claude", "-p",
        "--permission-mode", "bypassPermissions",
        "--allowedTools", "Bash,Read,Write,Edit,WebSearch,mcp",
    ]

    model = os.environ.get("CLAUDE_MODEL")
    if model:
        cmd.extend(["--model", model])

    prompt = (
        f"Create a genetics annotation module based on the following input.\n"
        f"Write output files (module_spec.yaml, variants.csv, studies.csv) to: {output_dir}/\n"
        f"Then validate with: uv run dna-agents validate {output_dir}/\n"
        f"Fix any validation errors before finishing.\n\n"
        f"---\n\n"
        f"{freeform_input}"
    )

    return subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        cwd=str(REPO_ROOT),
    )


def _assert_output_files(output_dir: Path):
    """Check that the agent produced the expected files."""
    assert output_dir.exists(), f"Output directory not created: {output_dir}"
    variants = output_dir / "variants.csv"
    studies = output_dir / "studies.csv"
    assert variants.exists(), f"variants.csv not created in {output_dir}"
    assert studies.exists(), f"studies.csv not created in {output_dir}"
    assert variants.stat().st_size > 50, "variants.csv is suspiciously small"
    assert studies.stat().st_size > 20, "studies.csv is suspiciously small"


@pytest.mark.agent_eval
class TestAgentEvals:
    """Run module-creator agent against eval inputs and score output."""

    @pytest.fixture(autouse=True)
    def _check_claude_available(self):
        """Skip if claude CLI is not installed."""
        if not shutil.which("claude"):
            pytest.skip("claude CLI not found — install Claude Code to run agent evals")

    @pytest.mark.parametrize(
        "eval_name,hf_module,rsid_filter",
        EVAL_CASES,
        ids=[c[0] for c in EVAL_CASES],
    )
    def test_agent_eval(self, eval_name, hf_module, rsid_filter, tmp_path):
        eval_dir = EVALS_DIR / eval_name
        freeform_path = eval_dir / "freeform_input.md"

        if not freeform_path.exists():
            pytest.skip(f"No freeform_input.md in {eval_dir}")

        freeform_input = freeform_path.read_text(encoding="utf-8")
        output_dir = tmp_path / eval_name

        result = _run_claude_agent(freeform_input, output_dir)

        if result.returncode != 0:
            pytest.fail(
                f"claude exited with code {result.returncode}\n"
                f"stderr: {result.stderr[:2000]}\n"
                f"stdout: {result.stdout[:2000]}"
            )

        _assert_output_files(output_dir)

        # Use HF parquet as ground truth when available
        reference = hf_module if hf_module else eval_dir
        score = score_module(output_dir, reference, rsid_filter=rsid_filter)
        report = score.summary()

        print(f"\n{'=' * 60}")
        print(f"Eval: {eval_name}")
        print(f"Reference: {hf_module or eval_dir}")
        print(report)
        print(f"{'=' * 60}\n")

        score_path = tmp_path / f"{eval_name}_score.json"
        score_path.write_text(json.dumps(score.to_dict(), indent=2))

        assert score.variant_recall.normalized >= MIN_RECALL, (
            f"Variant recall {score.variant_recall.normalized:.0%} < {MIN_RECALL:.0%}\n"
            f"{report}"
        )
        assert score.overall >= MIN_OVERALL, (
            f"Overall score {score.overall:.0%} < {MIN_OVERALL:.0%}\n"
            f"{report}"
        )


@pytest.mark.agent_eval
class TestAgentEvalSmoke:
    """Lighter smoke test — just check the agent produces valid output."""

    @pytest.fixture(autouse=True)
    def _check_claude_available(self):
        if not shutil.which("claude"):
            pytest.skip("claude CLI not found")

    def test_agent_produces_valid_module(self, tmp_path):
        """Run agent on cyp_panel and check the output validates."""
        eval_dir = EVALS_DIR / "cyp_panel"
        freeform_input = (eval_dir / "freeform_input.md").read_text(encoding="utf-8")
        output_dir = tmp_path / "cyp_panel"

        result = _run_claude_agent(freeform_input, output_dir)

        if result.returncode != 0:
            pytest.fail(f"claude exited with code {result.returncode}")

        _assert_output_files(output_dir)

        from dna_agents.compiler import validate_spec
        validation = validate_spec(output_dir)
        assert validation.valid, (
            f"Agent output failed validation:\n"
            + "\n".join(validation.errors)
        )
