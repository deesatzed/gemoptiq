import time
import pytest
import os
import signal
import threading
from src.sentinel.runner import AgentRunner

def test_runner_basic_output():
    runner = AgentRunner("echo 'hello world'")
    runner.start()
    
    # Wait for output
    output = None
    for _ in range(10):
        output = runner.get_output()
        if output:
            break
        time.sleep(0.1)
    
    assert output is not None
    assert "hello world" in output
    runner.kill()

def test_runner_input():
    # A simple script that reads from stdin and echoes it back
    runner = AgentRunner("python3 -c \"import sys; print(f'received: {sys.stdin.readline().strip()}')\"")
    runner.start()
    
    runner.write_input("test input\n")
    
    # Wait for output
    output = None
    for _ in range(20):
        output = runner.get_output()
        if output:
            break
        time.sleep(0.1)
    
    assert output is not None
    assert "received: test input" in output
    runner.kill()

def test_runner_suspend_resume():
    # A script that prints a counter every 0.1s
    script = "python3 -c \"import time; i=0; [print(i:=i+1, flush=True) or time.sleep(0.1) for _ in range(100)]\""
    runner = AgentRunner(script)
    runner.start()
    
    # Get first few outputs
    time.sleep(0.5)
    outputs = []
    while True:
        out = runner.get_output()
        if not out: break
        outputs.append(out.strip())
    
    assert len(outputs) > 0
    last_val = int(outputs[-1])
    
    # Suspend
    runner.suspend()
    time.sleep(0.5)
    
    # Check that no new output was produced (or at least it stopped)
    outputs_during_suspend = []
    while True:
        out = runner.get_output()
        if not out: break
        outputs_during_suspend.append(out.strip())
    
    # It might have one or two in-flight lines but it should stop
    runner.resume()
    time.sleep(0.5)
    
    outputs_after_resume = []
    while True:
        out = runner.get_output()
        if not out: break
        outputs_after_resume.append(out.strip())
    
    assert len(outputs_after_resume) > 0
    assert int(outputs_after_resume[-1]) > last_val
    
    runner.kill()

def test_runner_kill():
    # A script that ignores SIGTERM but can't ignore SIGKILL
    script = "python3 -c \"import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('started', flush=True); [time.sleep(1) for _ in range(60)]\""
    runner = AgentRunner(script)
    runner.start()
    
    # Wait for 'started'
    output = None
    for _ in range(20):
        output = runner.get_output()
        if output:
            break
        time.sleep(0.1)
    
    assert "started" in output
    
    pid = runner.process.pid
    runner.kill()
    
    # Check if process is gone
    time.sleep(0.5)
    try:
        os.kill(pid, 0)
        assert False, "Process should be killed"
    except ProcessLookupError:
        pass # Success

def test_runner_kill_process_group():
    # A script that starts a child process in the same process group and then sleeps
    # We use 'exec' to make the shell replace itself with python, and we start a child
    script = "python3 -c \"import subprocess, time, os; subprocess.Popen(['python3', '-c', 'import time; [time.sleep(1) for _ in range(60)]']); print(os.getpid(), flush=True); [time.sleep(1) for _ in range(60)]\""
    runner = AgentRunner(script)
    runner.start()
    
    # Wait for the PID output
    output = None
    for _ in range(20):
        output = runner.get_output()
        if output:
            break
        time.sleep(0.1)
    
    assert output is not None
    parent_pid = int(output.strip())
    pgid = os.getpgid(parent_pid)
    
    # Find all processes in the same process group
    import subprocess as sp
    def get_pgid_processes(pgid):
        try:
            # -g matches PGID
            out = sp.check_output(["ps", "-o", "pid=", "-g", str(pgid)]).decode()
            return [int(p) for p in out.split()]
        except sp.CalledProcessError:
            return []

    pids_in_group = get_pgid_processes(pgid)
    assert len(pids_in_group) >= 2 # Should have at least the shell/python and its child
    
    runner.kill()
    time.sleep(0.5)
    
    # All processes in the group should be gone
    pids_after = get_pgid_processes(pgid)
    assert len(pids_after) == 0

def test_prevent_double_start():
    runner = AgentRunner("sleep 10")
    runner.start()
    first_process = runner.process
    assert first_process is not None
    
    with pytest.raises(RuntimeError, match="Process is already active"):
        runner.start()
    
    assert runner.process == first_process
    runner.kill()

def test_robustness_any_time():
    runner = AgentRunner("sleep 10")
    # Should not crash when calling these before start
    runner.suspend()
    runner.resume()
    runner.kill()
    
    runner.start()
    runner.kill()
    # Should not crash after kill
    runner.suspend()
    runner.resume()
    runner.kill()

def test_thread_safety_kill():
    runner = AgentRunner("sleep 10")
    runner.start()
    
    def kill_it():
        try:
            runner.kill()
        except Exception:
            pass
            
    threads = [threading.Thread(target=kill_it) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert runner.process is None
