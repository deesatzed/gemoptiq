import os
import subprocess as sp
import sys
import time
import fcntl
import struct
import termios

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


def test_pty_runner_answers_cursor_position_query():
    script = (
        f"{sys.executable} -c \""
        "import os, sys, termios, tty; "
        "tty.setraw(sys.stdin.fileno()); "
        "sys.stdout.write('\\\\x1b[6n'); sys.stdout.flush(); "
        "response=os.read(sys.stdin.fileno(), 16); "
        "termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, termios.tcgetattr(sys.stdin.fileno())); "
        "print('response:' + repr(response), flush=True)"
        "\""
    )
    runner = PtyAgentRunner(script)
    runner.start()
    try:
        output = wait_for_text(runner, "response:")
        assert "b'\\x1b[1;1R'" in output
    finally:
        runner.kill()


def test_pty_runner_starts_child_with_usable_window_size():
    script = (
        f"{sys.executable} -c \""
        "import fcntl, struct, sys, termios; "
        "rows, cols, _, _ = struct.unpack('HHHH', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b'\\\\0' * 8)); "
        "print(f'size:{rows}x{cols}', flush=True)"
        "\""
    )
    runner = PtyAgentRunner(script)
    runner.start()
    try:
        output = wait_for_text(runner, "size:")
        assert "size:24x80" in output
    finally:
        runner.kill()
