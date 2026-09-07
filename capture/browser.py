"""Launch a Chrome instance isolated from the user's daily browser profile."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


PROFILE_PREFIX = "api-capture-chrome-"


class ChromeLaunchError(RuntimeError):
    """Raised when an isolated Chrome session cannot be started safely."""


def find_chrome_executable(explicit_path: Optional[Path] = None) -> Path:
    """Locate Google Chrome/Chromium on macOS, Windows, or Linux."""
    if explicit_path is not None:
        candidate = Path(explicit_path).expanduser().resolve()
        if candidate.is_file():
            return candidate
        raise ChromeLaunchError(f"Chrome executable does not exist: {candidate}")

    candidates: List[Path] = []
    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
                Path("/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"),
                Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ]
        )
    elif sys.platform == "win32":
        for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            root = os.environ.get(env_name)
            if root:
                candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")
    else:
        for binary_name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            executable = shutil.which(binary_name)
            if executable:
                candidates.append(Path(executable))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise ChromeLaunchError(
        "未找到 Chrome。请使用 --chrome-path 指定 Chrome/Chromium 可执行文件。"
    )


def build_chrome_command(
    executable: Path,
    profile_dir: Path,
    url: str,
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 18527,
    ignore_certificate_errors: bool = True,
) -> List[str]:
    """Build the command for an isolated, proxy-scoped Chrome process."""
    if not 1 <= proxy_port <= 65535:
        raise ChromeLaunchError(f"Invalid proxy port: {proxy_port}")
    if not proxy_host.strip():
        raise ChromeLaunchError("Proxy host cannot be empty")

    command = [
        str(executable),
        f"--user-data-dir={profile_dir}",
        f"--proxy-server=http://{proxy_host}:{proxy_port}",
        "--proxy-bypass-list=localhost;127.0.0.1",
        "--disable-sync",
        "--disable-default-apps",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
    ]
    if ignore_certificate_errors:
        command.append("--ignore-certificate-errors")
    command.append(url or "about:blank")
    return command


@dataclass
class IsolatedChromeSession:
    """A running Chrome process and the temporary profile owned by it."""

    process: subprocess.Popen
    profile_dir: Path
    temporary_profile: bool
    keep_profile: bool = False

    def wait(self) -> int:
        """Wait for Chrome to close, then remove only profiles created by this tool."""
        try:
            return int(self.process.wait())
        except KeyboardInterrupt:
            self.process.terminate()
            try:
                return int(self.process.wait(timeout=5))
            except subprocess.TimeoutExpired:
                self.process.kill()
                return int(self.process.wait())
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        if not self.temporary_profile or self.keep_profile:
            return
        temp_root = Path(tempfile.gettempdir()).resolve()
        profile = self.profile_dir.resolve()
        if profile.parent != temp_root or not profile.name.startswith(PROFILE_PREFIX):
            raise ChromeLaunchError(f"Refusing to remove non-temporary profile: {profile}")
        shutil.rmtree(profile, ignore_errors=True)


def launch_isolated_chrome(
    *,
    url: str = "about:blank",
    proxy_host: str = "127.0.0.1",
    proxy_port: int = 18527,
    chrome_path: Optional[Path] = None,
    profile_dir: Optional[Path] = None,
    keep_profile: bool = False,
    ignore_certificate_errors: bool = True,
    popen_factory: Optional[Callable[..., subprocess.Popen]] = None,
) -> IsolatedChromeSession:
    """Start Chrome with a dedicated profile and a process-local proxy."""
    executable = find_chrome_executable(chrome_path)
    temporary_profile = profile_dir is None
    if temporary_profile:
        actual_profile = Path(tempfile.mkdtemp(prefix=PROFILE_PREFIX)).resolve()
    else:
        actual_profile = Path(profile_dir).expanduser().resolve()
        actual_profile.mkdir(parents=True, exist_ok=True)

    command = build_chrome_command(
        executable=executable,
        profile_dir=actual_profile,
        url=url,
        proxy_host=proxy_host,
        proxy_port=proxy_port,
        ignore_certificate_errors=ignore_certificate_errors,
    )

    process_factory = popen_factory or subprocess.Popen
    process_options = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        process_options["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        process_options["start_new_session"] = True

    try:
        process = process_factory(command, **process_options)
    except Exception as exc:
        if temporary_profile:
            shutil.rmtree(actual_profile, ignore_errors=True)
        raise ChromeLaunchError(f"无法启动 Chrome: {exc}") from exc

    return IsolatedChromeSession(
        process=process,
        profile_dir=actual_profile,
        temporary_profile=temporary_profile,
        keep_profile=keep_profile,
    )
