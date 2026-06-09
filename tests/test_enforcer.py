import time
from unittest.mock import MagicMock

from sentinel.config import SentinelConfig
from sentinel.effects import FileEffectObserver
from sentinel.enforcer import ContinuousEnforcer
from sentinel.policy import FileEffect, PolicyAction, SentinelPolicy


def test_check_once_suspends_runner_on_protected_effect():
    runner = MagicMock()
    observer = MagicMock()
    observer.diff.return_value = [FileEffect("created", ".env")]
    policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))

    enforcer = ContinuousEnforcer(runner=runner, observer=observer, policy=policy)

    decision = enforcer.check_once()

    assert decision is not None
    assert decision.action is PolicyAction.BLOCK
    runner.suspend.assert_called_once()
    observer.snapshot.assert_called_once()


def test_check_once_deletes_created_protected_file(tmp_path):
    runner = MagicMock()
    observer = FileEffectObserver(tmp_path)
    policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))
    enforcer = ContinuousEnforcer(runner=runner, observer=observer, policy=policy)

    observer.snapshot()
    protected_file = tmp_path / ".env"
    protected_file.write_text("SECRET=1")

    decision = enforcer.check_once()

    assert decision is not None
    assert decision.action is PolicyAction.BLOCK
    runner.suspend.assert_called_once()
    assert not protected_file.exists()
    assert enforcer.last_rollback_results == [
        {"path": ".env", "operation": "created", "rollback": "deleted-created-file"}
    ]


def test_check_once_restores_modified_protected_file(tmp_path):
    runner = MagicMock()
    protected_file = tmp_path / ".env"
    protected_file.write_text("SECRET=original")
    observer = FileEffectObserver(tmp_path)
    policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))
    enforcer = ContinuousEnforcer(runner=runner, observer=observer, policy=policy)

    enforcer.capture_protected_baseline()
    observer.snapshot()
    protected_file.write_text("SECRET=changed")

    decision = enforcer.check_once()

    assert decision is not None
    assert decision.action is PolicyAction.BLOCK
    assert protected_file.read_text() == "SECRET=original"
    assert enforcer.last_rollback_results == [
        {"path": ".env", "operation": "modified", "rollback": "restored-baseline"}
    ]


def test_check_once_restores_default_secret_path_without_configured_protected_paths(tmp_path):
    runner = MagicMock()
    protected_file = tmp_path / ".env"
    protected_file.write_text("SECRET=original")
    observer = FileEffectObserver(tmp_path)
    policy = SentinelPolicy(SentinelConfig())
    enforcer = ContinuousEnforcer(runner=runner, observer=observer, policy=policy)

    enforcer.capture_protected_baseline()
    observer.snapshot()
    protected_file.write_text("SECRET=changed")

    decision = enforcer.check_once()

    assert decision is not None
    assert decision.action is PolicyAction.BLOCK
    assert "secret" in decision.reason.lower()
    assert protected_file.read_text() == "SECRET=original"


def test_check_once_ignores_empty_diff():
    runner = MagicMock()
    observer = MagicMock()
    observer.diff.return_value = []
    policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))

    enforcer = ContinuousEnforcer(runner=runner, observer=observer, policy=policy)

    assert enforcer.check_once() is None
    runner.suspend.assert_not_called()


def test_background_loop_detects_no_prompt_protected_write(tmp_path):
    runner = MagicMock()
    observer = FileEffectObserver(tmp_path)
    policy = SentinelPolicy(SentinelConfig(protected_paths=["**/.env"]))
    enforcer = ContinuousEnforcer(
        runner=runner,
        observer=observer,
        policy=policy,
        interval_seconds=0.05,
    )

    enforcer.start()
    try:
        (tmp_path / ".env").write_text("SECRET=1")
        deadline = time.time() + 2
        while time.time() < deadline and not runner.suspend.called:
            time.sleep(0.05)
    finally:
        enforcer.stop()

    runner.suspend.assert_called_once()
    assert enforcer.last_decision is not None
    assert enforcer.last_decision.action is PolicyAction.BLOCK
