from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Dict

import restconf_final

STUDENT_ID = getattr(restconf_final, "STUDENT_ID", "66070014")
ROUTER_NAME = "CSR1KV-Pod1-5"
PLAYBOOK_PATH = Path("playbook.yaml")
OUTPUT_FILE = Path(f"show_run_{STUDENT_ID}_{ROUTER_NAME}.txt")


def showrun() -> Dict[str, str]:
    if not PLAYBOOK_PATH.exists():
        return {"status": "FAIL", "msg": "Error: Ansible"}

    command = ["ansible-playbook", str(PLAYBOOK_PATH)]
    result = subprocess.run(command, capture_output=True, text=True)
    output = result.stdout + result.stderr
    print(output)

    if result.returncode != 0 or "failed=0" not in output:
        return {"status": "FAIL", "msg": "Error: Ansible"}

    if not OUTPUT_FILE.exists():
        return {"status": "FAIL", "msg": "Error: Ansible"}

    return {
        "status": "OK",
        "msg": "show running config",
        "path": str(OUTPUT_FILE),
    }


if __name__ == "__main__":
    showrun()
