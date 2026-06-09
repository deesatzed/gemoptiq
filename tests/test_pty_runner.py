import os
import subprocess as sp
import sys
import time

import pytest

from sentinel.pty_runner import PtyAgentRunner


def wait_for_text(runner, expected, timeout=5.0):
    deadline = time.time() + timeout
    seen = ""
    while time.time() < deadline:
        chunk = runner.get_output()
        if chunk:
            seen += chunk
            if expected in seen:
                return seen
        time.sleep(0.05)
    return seen


def test_pty_runner_reads_prompt_without_newline_and_writes_input():
    script = (
        f"{sys.executable} -c \""
        "import sys; "
        "sys.stdout.write('Proceed [y/n]? '); sys.stdout.flush(); "
        "answer=sys.stdin.readline().strip(); "
        "print('answer:' + answer, flush=True)"
        "\""
    )
    runner = PtyAgentRunner(script)
    runner.start()
    try:
        prompt = wait_for_text(runner, "Proceed [y/n]?")
        assert "Proceed [y/n]?" in prompt

        runner.write_input("y\n")
        response = wait_for_text(runner, "answer:y")
        assert "answer:y" in response
    finally:
        runner.kill()


def test_pty_runner_prevents_double_start():
    runner = PtyAgentRunner("sleep 10")
    runner.start()
    try:
        with pytest.raises(RuntimeError, match="Process is already active"):
            runner.start()
    finally:
        runner.kill()


def test_pty_runner_kills_process_group():
    script = (
        f"{sys.executable} -c \""
        "import subprocess, time, os; "
        f"subprocess.Popen(['{sys.executable}', '-c', 'import time; time.sleep(60)']); "
        "print(os.getpid(), flush=True); time.sleep(60)"
        "\""
    )
    runner = PtyAgentRunner(script)
    runner.start()

    output = wait_for_text(runner, "\n")
    parent_pid = int(output.strip().splitlines()[0])
    pgid = os.getpgid(parent_pid)

    def get_pgid_processes(process_group_id):
        try:
            out = sp.check_output(["ps", "-o", "pid=", "-g", str(process_group_id)]).decode()
            return [int(p) for p in out.split()]
        except sp.CalledProcessError:
            return []

    assert len(get_pgid_processes(pgid)) >= 2
    runner.kill()
    time.sleep(0.5)
    assert get_pgid_processes(pgid) == []
