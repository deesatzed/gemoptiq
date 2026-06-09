from __future__ import annotations

import logging
import os
import pty
import queue
import signal
import fcntl
import struct
import subprocess
import termios
import threading

logger = logging.getLogger(__name__)


class PtyAgentRunner:
    def __init__(
        self,
        command: str,
        *,
        cwd: str | None = None,
        terminal_rows: int = 24,
        terminal_cols: int = 80,
    ):
        self.command = command
        self.cwd = cwd
        self.terminal_rows = terminal_rows
        self.terminal_cols = terminal_cols
        self.process = None
        self.output_queue = queue.Queue()
        self.reader_thread = None
        self.master_fd = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self.process and self.process.poll() is None:
                raise RuntimeError("Process is already active")

            master_fd, slave_fd = pty.openpty()
            try:
                self._set_window_size(slave_fd)
                self.process = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    start_new_session=True,
                    close_fds=True,
                    cwd=self.cwd,
                )
            finally:
                os.close(slave_fd)

            self.master_fd = master_fd
            self._stop_event.clear()
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()

    def _read_output(self):
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    master_fd = self.master_fd
                if master_fd is None:
                    break
                try:
                    data = os.read(master_fd, 4096)
                except OSError:
                    break
                if not data:
                    break
                self._respond_to_terminal_queries(data)
                self.output_queue.put(data.decode(errors="replace"))
        except Exception as e:
            logger.error(f"Error reading PTY output: {e}")
        finally:
            logger.debug("PTY reader thread stopped")

    def _set_window_size(self, fd: int):
        rows = max(1, self.terminal_rows)
        cols = max(1, self.terminal_cols)
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    def _respond_to_terminal_queries(self, data: bytes):
        responses: list[bytes] = []
        if b"\x1b[6n" in data:
            responses.append(b"\x1b[1;1R")
        if b"\x1b[c" in data:
            responses.append(b"\x1b[?1;2c")
        if b"\x1b[?u" in data:
            responses.append(b"\x1b[?0u")
        if b"\x1b]10;?\x1b\\" in data:
            responses.append(b"\x1b]10;rgb:ffff/ffff/ffff\x1b\\")
        if b"\x1b]11;?\x1b\\" in data:
            responses.append(b"\x1b]11;rgb:0000/0000/0000\x1b\\")
        if not responses:
            return

        with self._lock:
            master_fd = self.master_fd
            process_alive = self.process and self.process.poll() is None
        if master_fd is None or not process_alive:
            return

        for response in responses:
            try:
                os.write(master_fd, response)
            except OSError as e:
                logger.debug(f"Error writing PTY terminal response: {e}")
                break

    def suspend(self):
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGSTOP)
                except (ProcessLookupError, OSError):
                    logger.warning("Process group not found during PTY suspend.")

    def resume(self):
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGCONT)
                except (ProcessLookupError, OSError):
                    logger.warning("Process group not found during PTY resume.")

    def kill(self):
        reader_thread = None
        with self._lock:
            self._stop_event.set()

            if self.process:
                try:
                    if self.process.poll() is None:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    logger.debug("PTY process or process group already gone during kill.")

                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    logger.warning("PTY process did not exit after SIGKILL and 2s timeout")

            if self.master_fd is not None:
                try:
                    os.close(self.master_fd)
                except OSError:
                    pass
                self.master_fd = None

            reader_thread = self.reader_thread
            self.process = None
            self.reader_thread = None

        if reader_thread:
            reader_thread.join(timeout=2)

    def get_output(self) -> str | None:
        try:
            return self.output_queue.get_nowait()
        except queue.Empty:
            return None

    def write_input(self, data: str):
        with self._lock:
            if self.master_fd is not None and self.process and self.process.poll() is None:
                try:
                    os.write(self.master_fd, data.encode())
                except OSError as e:
                    logger.error(f"Error writing PTY input: {e}")
