import subprocess
from pathlib import Path

import pytest

from capture.browser import (
    ChromeLaunchError,
    build_chrome_command,
    find_chrome_executable,
    launch_isolated_chrome,
)


def test_build_chrome_command_uses_isolated_profile_and_proxy(tmp_path: Path):
    command = build_chrome_command(
        executable=Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        profile_dir=tmp_path / "profile",
        url="https://example.com",
        proxy_host="127.0.0.1",
        proxy_port=18527,
    )

    assert f"--user-data-dir={tmp_path / 'profile'}" in command
    assert "--proxy-server=http://127.0.0.1:18527" in command
    assert "--proxy-bypass-list=localhost;127.0.0.1" in command
    assert "--disable-sync" in command
    assert "--ignore-certificate-errors" in command
    assert command[-1] == "https://example.com"


def test_build_chrome_command_can_require_valid_certificates(tmp_path: Path):
    command = build_chrome_command(
        executable=Path("/chrome"),
        profile_dir=tmp_path / "profile",
        url="about:blank",
        ignore_certificate_errors=False,
    )

    assert "--ignore-certificate-errors" not in command


def test_find_chrome_executable_rejects_missing_explicit_path(tmp_path: Path):
    with pytest.raises(ChromeLaunchError, match="does not exist"):
        find_chrome_executable(tmp_path / "missing-chrome")


def test_temporary_profile_is_removed_after_browser_closes(tmp_path: Path):
    executable = tmp_path / "chrome"
    executable.write_text("fake", encoding="utf-8")
    calls = []

    class FakeProcess:
        def wait(self, timeout=None):
            return 0

        def terminate(self):
            return None

        def kill(self):
            return None

    def fake_popen(command, **options):
        calls.append((command, options))
        return FakeProcess()

    session = launch_isolated_chrome(
        chrome_path=executable,
        popen_factory=fake_popen,
    )
    profile_dir = session.profile_dir
    assert profile_dir.exists()

    assert session.wait() == 0
    assert not profile_dir.exists()
    assert calls
    assert calls[0][1]["stdout"] == subprocess.DEVNULL


def test_custom_profile_is_never_deleted(tmp_path: Path):
    executable = tmp_path / "chrome"
    executable.write_text("fake", encoding="utf-8")
    custom_profile = tmp_path / "custom-profile"

    class FakeProcess:
        def wait(self, timeout=None):
            return 0

    session = launch_isolated_chrome(
        chrome_path=executable,
        profile_dir=custom_profile,
        popen_factory=lambda *args, **kwargs: FakeProcess(),
    )
    session.wait()

    assert custom_profile.exists()
