from __future__ import annotations

import contextlib
import json
import os
import time
from urllib.request import Request as HttpRequest, urlopen

import sublime
from LSP.plugin import AbstractPlugin, ClientConfig, WorkspaceFolder, register_plugin, unregister_plugin

__all__ = [
    "SystemdLspPlugin",
    "plugin_loaded",
    "plugin_unloaded",
]


class SystemdLspPlugin(AbstractPlugin):
    package_name: str = __spec__.parent
    """
    The package name on file system.

    Main purpose is to provide python version agnostic package name for use
    in path sensitive locations, to ensure plugin even works if user installs
    package with different name.
    """

    server_version: str = ""
    """
    The language server version to use.
    """

    settings: sublime.Settings
    """
    Package settings
    """

    # ---- public API methods ----

    @classmethod
    def name(cls):
        return "LSP-systemd"

    @classmethod
    def configuration(cls):
        settings_file_name = f"{cls.name()}.sublime-settings"
        cls.settings = sublime.load_settings(settings_file_name)
        return cls.settings, f"Packages/{cls.package_name}/{settings_file_name}"

    @classmethod
    def needs_update_or_installation(cls):
        server_file = cls.server_file()
        is_upgrade = os.path.isfile(server_file)
        if is_upgrade:
            next_update_check, server_version = cls.load_metadata()
        else:
            next_update_check, server_version = 0, ""

        cls.server_version = str(cls.settings.get("server_version", "latest"))
        if cls.server_version == "latest":
            if int(time.time()) >= next_update_check:
                try:
                    available_version = cls.available_version()
                    if available_version != server_version:
                        cls.server_version = available_version
                        return True
                except BaseException:
                    cls.save_metadata(False, server_version)

            return False

        return cls.server_version != server_version

    @classmethod
    def install_or_update(cls):
        if not cls.server_version:
            raise RuntimeError()

        os.makedirs(cls.server_path(), exist_ok=True)

        server_file = cls.server_file()
        with contextlib.closing(urlopen(cls.download_url(cls.server_version))) as response:
            with open(server_file, "wb") as out:
                while True:
                    block = response.read(5 * 1024 * 1024)
                    if not block:
                        break
                    out.write(block)

        os.chmod(server_file, 0o755)

        # write update cookie
        cls.save_metadata(True, cls.server_version)

    @classmethod
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        if not os.path.isfile(cls.server_file()):
            return f"{cls.name()}: server binary not found, please run 'Package Control: Satisfy Dependencies'"
        return super().can_start(window, initiating_view, workspace_folders, configuration)

    @classmethod
    def additional_variables(cls) -> dict[str, str]:
        return {"server_file": cls.server_file(), "server_path": cls.server_path()}

    # ---- internal methods -----

    @classmethod
    def available_version(cls):
        # response url ends with latest available version tag, e.g. "v2026.08.03"
        request = HttpRequest(url=f"{cls.repo_url()}/releases/latest", method="HEAD")
        with contextlib.closing(urlopen(request)) as response:
            return response.url.rstrip("/").rsplit("/", 1)[1]

    @classmethod
    def cleanup(cls):
        try:
            from package_control import events  # type: ignore

            if events.remove(cls.package_name):
                sublime.set_timeout_async(cls.remove_server_path, 1000)
        except ImportError:
            pass  # Package Control is not required.

    @classmethod
    def remove_server_path(cls):
        from shutil import rmtree

        server_path = cls.server_path()
        # Enable long path support on on Windows
        # to avoid errors when cleaning up paths with more than 256 chars.
        # see: https://stackoverflow.com/a/14076169/4643765
        if sublime.platform() == "windows":
            server_path = Rf"\\?\{server_path}"

        rmtree(server_path, ignore_errors=True)

    @classmethod
    def repo_url(cls) -> str:
        return "https://github.com/JFryy/systemd-lsp"

    @classmethod
    def download_url(cls, version: str) -> str:
        # systemd-lsp only ships prebuilt binaries for these targets, see
        # https://github.com/JFryy/systemd-lsp/releases
        release_assets = {
            "osx-arm64": "systemd-lsp-aarch64-apple-darwin",
            "osx-x64": "systemd-lsp-x86_64-apple-darwin",
            "windows-x64": "systemd-lsp-x86_64-pc-windows-msvc.exe",
            "linux-x64": "systemd-lsp-x86_64-unknown-linux-gnu",
        }
        platform_arch = f"{sublime.platform()}-{sublime.arch()}"
        try:
            asset = release_assets[platform_arch]
        except KeyError:
            raise RuntimeError(f"{cls.name()}: no prebuilt systemd-lsp binary available for {platform_arch}")
        return f"{cls.repo_url()}/releases/download/{version}/{asset}"

    @classmethod
    def server_file(cls) -> str:
        name = os.path.join(cls.server_path(), "systemd-lsp")
        if sublime.platform() == "windows":
            name += ".exe"
        return name

    @classmethod
    def server_path(cls) -> str:
        return os.path.join(cls.storage_path(), cls.package_name)

    @classmethod
    def metadata_file(cls) -> str:
        return os.path.join(cls.server_path(), "update.json")

    @classmethod
    def load_metadata(cls) -> tuple[int, str]:
        try:
            with open(cls.metadata_file()) as fobj:
                data = json.load(fobj)
                return int(data["timestamp"]), data["version"]
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            return 0, ""

    @classmethod
    def save_metadata(cls, success: bool, version: str) -> None:
        next_run_delay = (7 * 24 * 60 * 60) if success else (6 * 60 * 60)
        with open(cls.metadata_file(), "w") as fobj:
            json.dump(
                {
                    "timestamp": int(time.time()) + next_run_delay,
                    "version": version,
                },
                fp=fobj,
            )


def plugin_loaded() -> None:
    register_plugin(SystemdLspPlugin)


def plugin_unloaded() -> None:
    SystemdLspPlugin.cleanup()
    unregister_plugin(SystemdLspPlugin)
