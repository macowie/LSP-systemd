from __future__ import annotations

import contextlib
import json
import os
import time
from urllib.request import Request as HttpRequest, urlopen

import sublime
from package_control import events 
from LSP.plugin import ClientConfig, ClientResponse, LspPlugin, OnPreStartContext, PluginStartError, ST_STORAGE_PATH

from .updater import Updater

__all__ = [
    "LspSystemdPlugin",
    "build_updater",
    "server_path",
    "plugin_loaded",
    "plugin_unloaded",
]

class LspSystemdPlugin(LspPlugin):
    package_name: str = __spec__.parent

    @classmethod
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        desired_version = context.configuration.server_version 
        if desired_version is None or desired_version == "":
            desired_version = "latest"
            
        updater = build_updater()
        context.variables["server_file"] = updater.server_file()
        if updater.needs_update(desired_version):
            updater.download_binary(desired_version)
            if not os.path.isfile(updater.server_file()):
                raise PluginStartError("Server binary missing after installation attempt")

def server_path() -> str:
    return os.path.join(ST_STORAGE_PATH, LspSystemdPlugin.package_name)
 
def build_updater() -> Updater:
    return Updater(server_path(), sublime.platform(), sublime.arch())

def plugin_loaded() -> None:
    LspSystemdPlugin.register()

def plugin_unloaded() -> None:
    LspSystemdPlugin.unregister()