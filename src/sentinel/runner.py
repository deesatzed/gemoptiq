import subprocess
import os
import signal
import threading
import queue
import logging

# Get logger for this module
logger = logging.getLogger(__name__)

class AgentRunner:
    def __init__(self, command: str):
        """
        Initializes the AgentRunner with the specified command.
        """
        self.command = command
        self.process = None
        self.output_queue = queue.Queue()
        self.reader_thread = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self):
        """
        Starts the agent process in a new process group.
        """
        with self._lock:
            if self.process and self.process.poll() is None:
                raise RuntimeError("Process is already active")

            logger.info(f"Starting agent with command: {self.command}")
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                start_new_session=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self._stop_event.clear()
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

    def _read_output(self):
        """
        Background thread function to read stdout line by line.
        """
        try:
            # Capture stdout reference while holding the lock
            with self._lock:
                if not self.process or not self.process.stdout:
                    return
                stdout = self.process.stdout

            while not self._stop_event.is_set():
                try:
                    line = stdout.readline()
                    if not line:
                        break
                    self.output_queue.put(line)
                except (ValueError, OSError, EOFError):
                    # Handle cases where stdout is closed or other I/O errors
                    break
        except Exception as e:
            logger.error(f"Error reading output: {e}")
        finally:
            logger.debug("Reader thread stopped")

    def suspend(self):
        """
        Sends SIGSTOP to the process group.
        """
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    pgid = os.getpgid(self.process.pid)
                    logger.info(f"Suspending agent process group (PGID: {pgid})")
                    os.killpg(pgid, signal.SIGSTOP)
                except (ProcessLookupError, OSError):
                    logger.warning("Process group not found during suspend.")

    def resume(self):
        """
        Sends SIGCONT to the process group.
        """
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    pgid = os.getpgid(self.process.pid)
                    logger.info(f"Resuming agent process group (PGID: {pgid})")
                    os.killpg(pgid, signal.SIGCONT)
                except (ProcessLookupError, OSError):
                    logger.warning("Process group not found during resume.")

    def kill(self):
        """
        Sends SIGKILL to the process group and joins the reader thread.
        """
        reader_thread = None
        with self._lock:
            if self.process:
                self._stop_event.set()
                
                # Close stdout to unblock any potential hanging read in the reader thread
                if self.process.stdout:
                    try:
                        self.process.stdout.close()
                    except Exception:
                        pass
                
                # Close stdin to unblock any potential hanging read in the child
                if self.process.stdin:
                    try:
                        self.process.stdin.close()
                    except Exception:
                        pass

                try:
                    if self.process.poll() is None:
                        pgid = os.getpgid(self.process.pid)
                        logger.info(f"Killing agent process group (PGID: {pgid})")
                        os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    logger.debug("Process or process group already gone during kill.")
                
                # Ensure wait() is called to avoid zombies
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not exit after SIGKILL and 2s timeout, retrying wait...")
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.error("Process still hasn't exited after SIGKILL and extended wait")
                
                reader_thread = self.reader_thread
                self.process = None
                self.reader_thread = None

        if reader_thread:
            reader_thread.join(timeout=2)

    def get_output(self) -> str | None:
        """
        Non-blocking read from the output queue.
        """
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    def write_input(self, data: str):
        """
        Writes data to the process's stdin.
        """
        with self._lock:
            if self.process and self.process.stdin and self.process.poll() is None:
                try:
                    self.process.stdin.write(data)
                    self.process.stdin.flush()
                except BrokenPipeError:
                    logger.error("Failed to write to stdin: Broken pipe")
                except Exception as e:
                    logger.error(f"Error writing to stdin: {e}")
