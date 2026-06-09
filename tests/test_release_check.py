import json
import subprocess
import sys


def test_release_check_dry_run_reports_metadata_without_building_wheel():
    result = subprocess.run(
        [sys.executable, "scripts/release_check.py", "--skip-wheel"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["project"]["name"] == "cortex-sentinel"
    assert report["project"]["version"] == "0.1.0"
    assert report["console_script"] == "sentinel.main:main"
    assert report["readme"]["required_sections_present"] is True
    assert report["wheel"]["built"] is False


def test_release_check_builds_wheel(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/release_check.py",
            "--wheel-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "ok"
    assert report["wheel"]["built"] is True
    assert report["wheel"]["files"]
    assert report["wheel"]["files"][0].endswith(".whl")
