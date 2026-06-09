from sentinel.effects import FileEffectObserver


def test_detects_created_file(tmp_path):
    observer = FileEffectObserver(tmp_path)
    observer.snapshot()

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "new.md").write_text("hello")

    effects = observer.diff()

    assert [(effect.operation, effect.path) for effect in effects] == [
        ("created", "docs/new.md")
    ]


def test_detects_modified_file(tmp_path):
    file_path = tmp_path / "src.py"
    file_path.write_text("one")
    observer = FileEffectObserver(tmp_path)
    observer.snapshot()

    file_path.write_text("two plus more bytes")

    effects = observer.diff()

    assert [(effect.operation, effect.path) for effect in effects] == [
        ("modified", "src.py")
    ]


def test_detects_deleted_file(tmp_path):
    file_path = tmp_path / "old.txt"
    file_path.write_text("old")
    observer = FileEffectObserver(tmp_path)
    observer.snapshot()

    file_path.unlink()

    effects = observer.diff()

    assert [(effect.operation, effect.path) for effect in effects] == [
        ("deleted", "old.txt")
    ]


def test_ignores_configured_directories(tmp_path):
    ignored_dir = tmp_path / ".git"
    ignored_dir.mkdir()
    observer = FileEffectObserver(tmp_path)
    observer.snapshot()

    (ignored_dir / "index").write_text("ignored")

    assert observer.diff() == []
