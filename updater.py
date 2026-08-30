import contextlib
import json
import os
from urllib.request import Request as HttpRequest, urlopen
from shutil import rmtree
import time
	  
class Updater:
	def __init__(self, server_path, platform, arch):
		self.server_path = server_path
		self.platform = platform
		self.arch = arch

	def download_binary(self, desired_version: str) -> bool:
		if not desired_version:
			raise RuntimeError()
		if desired_version == "none":
			return False
		
		os.makedirs(self.server_path, exist_ok=True)

		version = desired_version if desired_version != "latest" else self.available_version()
		try:
			with contextlib.closing(urlopen(self.download_url(version))) as response:
				with open(self.server_file(), "wb") as out:
					while True:
						block = response.read(5 * 1024 * 1024)
						if not block:
							break
						out.write(block)

			os.chmod(self.server_file(), 0o755)
			self.save_metadata(True, version)
		except:
			return False
		# write update cookie
		return True

	def needs_update(self, desired_version: str) -> bool:
		if desired_version == "none":
			return False

		is_upgrade = os.path.isfile(self.server_file())

		if is_upgrade:
			next_update_check, version = self.load_metadata()
		else:
			next_update_check, version = 0, ""

		if desired_version == "latest":
			if int(time.time()) >= next_update_check:
				try:
					available_version = self.available_version()
					if available_version != version:
						version = available_version
						return True
				except BaseException:
					self.save_metadata(False, version)

			return False

		return desired_version != version

	def available_version(self):
		# response url ends with latest available version tag, e.g. "v2026.08.03"
		request = HttpRequest(url=f"{self.repo_url()}/releases/latest", method="HEAD")
		with contextlib.closing(urlopen(request)) as response:
			return response.url.rstrip("/").rsplit("/", 1)[1]

	def remove_server_path(self):
		path = self.server_path
		# Enable long path support on on Windows
		# to avoid errors when cleaning up paths with more than 256 chars.
		# see: https://stackoverflow.com/a/14076169/4643765
		if self.platform == "windows":
			path = Rf"\\?\{self.server_path}"

		rmtree(path, ignore_errors=True)

	def repo_url(self) -> str:
		return "https://github.com/JFryy/systemd-lsp"

	def download_url(self, version: str) -> str:
		# systemd-lsp only ships prebuilt binaries for these targets, see
		# https://github.com/JFryy/systemd-lsp/releases
		release_assets = {
			"osx-arm64": "systemd-lsp-aarch64-apple-darwin",
			"osx-x64": "systemd-lsp-x86_64-apple-darwin",
			"windows-x64": "systemd-lsp-x86_64-pc-windows-msvc.exe",
			"linux-x64": "systemd-lsp-x86_64-unknown-linux-gnu",
		}
		platform_arch = f"{self.platform}-{self.arch}"
		try:
			asset = release_assets[platform_arch]
		except KeyError:
			raise RuntimeError(f"LspSystemd: no prebuilt systemd-lsp binary available for {platform_arch}")
		return f"{self.repo_url()}/releases/download/{version}/{asset}"

	def server_file(self) -> str:
		name = os.path.join(self.server_path, "systemd-lsp")
		if self.platform == "windows":
			name += ".exe"
		return name

	def metadata_file(self) -> str:
		return os.path.join(self.server_path, "update.json")

	def load_metadata(self) -> "tuple[int, str]":
		try:
			with open(self.metadata_file()) as fobj:
				data = json.load(fobj)
				return int(data["timestamp"]), data["version"]
		except (FileNotFoundError, KeyError, TypeError, ValueError):
			return 0, ""

	def save_metadata(self, success: bool, version: str) -> bool:
		next_run_delay = (7 * 24 * 60 * 60) if success else (6 * 60 * 60)
		try:
			with open(self.metadata_file(), "w") as fobj:
				json.dump(
					{
						"timestamp": int(time.time()) + next_run_delay,
						"version": version,
					},
					fp=fobj,
				)
			return True
		except:
			return False 