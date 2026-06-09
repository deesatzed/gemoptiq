import json
import importlib.util
import subprocess
import sys
import threading
import time
from pathlib import Path

from sentinel.policy import PolicyAction, PolicyDecision


def test_enforcement_smoke_dry_run_outputs_structured_report():
    result = subprocess.run(
        [sys.executable, "scripts/enforcement_smoke.py", "--dry-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "dry-run"
    assert report["protected_effect_detected"] is True
    assert report["runner_suspended"] is True
    assert report["protected_file_present"] is False
    assert report["rollback_performed"] is True
    assert report["disposable_workspace"] is True


def test_enforcement_smoke_waits_for_rollback_after_block_decision():
    module = load_enforcement_smoke_module()
    enforcer = FakeEnforcer()

    def set_delayed_rollback():
        enforcer.last_decision = PolicyDecision(PolicyAction.BLOCK, "blocked")
        time.sleep(0.1)
        enforcer.last_rollback_results = [
            {"path": ".env", "operation": "created", "rollback": "deleted-created-file"}
        ]

    worker = threading.Thread(target=set_delayed_rollback)
    worker.start()
    try:
        assert module.wait_for_block_and_rollback(enforcer, timeout_seconds=1.0) is True
        assert enforcer.last_rollback_results
    finally:
        worker.join(timeout=1)


class FakeEnforcer:
    last_decision = None
    last_rollback_results = []


def load_enforcement_smoke_module():
    script_path = Path("scripts/enforcement_smoke.py").resolve()
    spec = importlib.util.spec_from_file_location("enforcement_smoke", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
