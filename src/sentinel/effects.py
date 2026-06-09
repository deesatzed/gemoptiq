from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from sentinel.policy import FileEffect


@dataclass(frozen=True)
class FileFingerprint:
    size: int
    mtime_ns: int


class FileEffectObserver:
    DEFAULT_IGNORES = {".git", ".pytest_cache", "__pycache__", "venv", ".venv"}

    def __init__(self, root: str | Path, ignore_dirs: set[str] | None = None):
        self.root = Path(root).resolve()
        self.ignore_dirs = set(ignore_dirs or self.DEFAULT_IGNORES)
        self._baseline: dict[str, FileFingerprint] = {}

    def snapshot(self) -> None:
        self._baseline = self._scan()

    def content_snapshot(self, path_patterns: list[str]) -> dict[str, bytes]:
        files = self._scan()
        snapshot: dict[str, bytes] = {}
        for relative_path in files:
            if not self._matches_any(relative_path, path_patterns):
                continue
            path = self.safe_path(relative_path)
            if path is None or not path.exists() or path.is_symlink() or not path.is_file():
                continue
            snapshot[relative_path] = path.read_bytes()
        return snapshot

    def diff(self) -> list[FileEffect]:
        current = self._scan()
        effects: list[FileEffect] = []

        for path in sorted(current.keys() - self._baseline.keys()):
            effects.append(FileEffect("created", path))

        for path in sorted(self._baseline.keys() - current.keys()):
            effects.append(FileEffect("deleted", path))

        for path in sorted(current.keys() & self._baseline.keys()):
            if current[path] != self._baseline[path]:
                effects.append(FileEffect("modified", path))

        return effects

    def _scan(self) -> dict[str, FileFingerprint]:
        if not self.root.exists():
            return {}

        files: dict[str, FileFingerprint] = {}
        for path in self.root.rglob("*"):
            if self._is_ignored(path) or path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
            files[self._relative(path)] = FileFingerprint(
                size=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
            )
        return files

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _is_ignored(self, path: Path) -> bool:
        relative_parts = path.relative_to(self.root).parts
        return any(part in self.ignore_dirs for part in relative_parts)

    def safe_path(self, relative_path: str) -> Path | None:
        path = self.root / relative_path
        try:
            resolved = path.resolve()
            resolved.relative_to(self.root)
        except (OSError, ValueError):
            return None
        return resolved

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        for pattern in patterns:
            normalized_pattern = str(Path(pattern).expanduser()).replace("\\", "/")
            if fnmatch(path, normalized_pattern):
                return True
            if normalized_pattern.startswith("**/") and fnmatch(path, normalized_pattern[3:]):
                return True
        return False
