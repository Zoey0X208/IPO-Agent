"""Run the local release gates without calling an external model provider."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_gate(name: str, command: list[str]) -> dict[str, object]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "gate": name,
        "status": "passed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "command": command,
        "output_tail": (result.stdout + result.stderr)[-1200:],
    }


def main() -> None:
    gates = [
        run_gate("G0_local_contracts", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        run_gate("G1_canonical_evidence_replay", [sys.executable, "-m", "ipo_agent.replay"]),
    ]
    result = {
        "status": "passed" if all(gate["status"] == "passed" for gate in gates) else "failed",
        "gates": gates,
        "note": "该门禁不调用外部模型，也不替代人工业务复核。",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
