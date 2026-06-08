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

    def start(self):
        """
        Starts the agent process in a new process group.
        """
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
            while not self._stop_event.is_set():
                if self.process and self.process.stdout:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    self.output_queue.put(line)
                else:
                    break
        except Exception as e:
            logger.error(f"Error reading output: {e}")
        finally:
            logger.debug("Reader thread stopped")

    def suspend(self):
        """
        Sends SIGSTOP to the process group.
        """
        if self.process and self.process.poll() is None:
            try:
                pgid = os.getpgid(self.process.pid)
                logger.info(f"Suspending agent process group (PGID: {pgid})")
                os.killpg(pgid, signal.SIGSTOP)
            except ProcessLookupError:
                logger.warning("Process group not found during suspend.")

    def resume(self):
        """
        Sends SIGCONT to the process group.
        """
        if self.process and self.process.poll() is None:
            try:
                pgid = os.getpgid(self.process.pid)
                logger.info(f"Resuming agent process group (PGID: {pgid})")
                os.killpg(pgid, signal.SIGCONT)
            except ProcessLookupError:
                logger.warning("Process group not found during resume.")

    def kill(self):
        """
        Sends SIGKILL to the process group and joins the reader thread.
        """
        if self.process:
            try:
                if self.process.poll() is None:
                    pgid = os.getpgid(self.process.pid)
                    logger.info(f"Killing agent process group (PGID: {pgid})")
                    os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                logger.debug("Process or process group already gone during kill.")
            
            self._stop_event.set()
            # Close stdin to unblock any potential hanging read in the child if it wasn't killed
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                except Exception:
                    pass
            
            if self.reader_thread:
                self.reader_thread.join(timeout=2)
            
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            self.process = None

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
        if self.process and self.process.stdin and self.process.poll() is None:
            try:
                self.process.stdin.write(data)
                self.process.stdin.flush()
            except BrokenPipeError:
                logger.error("Failed to write to stdin: Broken pipe")
