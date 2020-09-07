from LSP.plugin import __version__
from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import Request
from LSP.plugin import WorkspaceFolder
from LSP.plugin.core.typing import Any, List, Optional, Tuple

# TODO: Move to public API
from LSP.plugin.core.registry import LspTextCommand
from LSP.plugin.core.views import location_to_encoded_filename
from LSP.plugin.core.views import text_document_position_params

from os import environ
from os.path import dirname
from os.path import join
from os.path import realpath

import sublime
import shutil


def getenv(configuration: ClientConfig, key: str) -> Optional[str]:
    value = configuration.env.get(key)
    if value:
        return realpath(value)
    value = environ.get(key)
    if value:
        return realpath(value)
    return None


def which_realpath(exe: str) -> Optional[str]:
    path = shutil.which(exe)
    if path:
        return realpath(path)
    return None


def flutter_root_to_dart_sdk(flutter_root: str) -> str:
    return join(flutter_root, "cache", "dart-sdk")


class Dart(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return "Dart"

    @classmethod
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: List[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> Optional[str]:
        sdk_path = None  # type: Optional[str]
        # 1: Try FLUTTER_ROOT
        flutter_root = getenv(configuration, "FLUTTER_ROOT")
        if flutter_root:
            sdk_path = flutter_root_to_dart_sdk(flutter_root)
        # 2: Try `which flutter`
        if not sdk_path:
            flutter_bin = which_realpath("flutter")
            if flutter_bin:
                flutter_root = dirname(dirname(flutter_bin))
                sdk_path = flutter_root_to_dart_sdk(flutter_root)
        # 3: Try DART_SDK
        if not sdk_path:
            sdk_path = configuration.env.get("DART_SDK")
        # 4: Try `which dart`
        if not sdk_path:
            dart_bin = which_realpath("dart")
            if dart_bin:
                sdk_path = dirname(dirname(dart_bin))
        # 5: Exhausted all options
        if not sdk_path:
            return 'missing "DART_SDK" environment variable'
        configuration.command = [
            cls.dart_exe(sdk_path),
            cls.server_snapshot(sdk_path),
            "--lsp",
            "--client-id",
            "Sublime Text LSP",
            "--client-version",
            ".".join(map(str, __version__)),
        ]
        return None

    @classmethod
    def dart_exe(cls, sdk_path: str) -> str:
        return join(sdk_path, "bin", "dart")

    @classmethod
    def server_snapshot(cls, sdk_path: str) -> str:
        return join(sdk_path, "bin", "snapshots", "analysis_server.dart.snapshot")

    # handle custom notifications

    def m___analyzerStatus(self, params: Any) -> None:
        def run() -> None:
            session = self.weaksession()
            if not session:
                return
            analyzing = isinstance(params, dict) and params.get("isAnalyzing")
            status_key = self.name() + "_analyzing"
            for sv in session.session_views_async():
                if sv.view.is_valid():
                    if analyzing:
                        sv.view.set_status(status_key, "Analyzing")
                    else:
                        sv.view.erase_status(status_key)

        sublime.set_timeout_async(run)

    def m_dart_textDocument_publishClosingLabels(self, params: Any) -> None:
        # TODO: Implement me.
        pass

    def m_dart_textDocument_publishOutline(self, params: Any) -> None:
        # TODO: Implement me.
        pass

    def m_dart_textDocument_publishFlutterOutline(self, params: Any) -> None:
        # TODO: Implement me.
        pass


class LspDartReanalyzeCommand(LspTextCommand):
    session_name = Dart.name()

    def run(self, _: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        req = Request("dart/reanalyze")
        session.send_request(
            req, lambda r: sublime.set_timeout(lambda: self.on_result(r))
        )

    def on_result(self, params: Any) -> None:
        if not self.view.is_valid():
            return
        window = self.view.window()
        if not window:
            return
        window.status_message("Re-analyzed")


class LspDartSuperCommand(LspTextCommand):
    session_name = Dart.name()

    def run(self, _: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        params = text_document_position_params(self.view, self.view.sel()[0].b)
        req = Request("dart/textDocument/super", params)
        session.send_request(req, self.on_result)

    def on_result(self, params: Any) -> None:
        window = self.view.window()
        if not window:
            return
        if not isinstance(params, dict):
            return sublime.error_message("No superclass found")
        window.open_file(
            location_to_encoded_filename(params), flags=sublime.ENCODED_POSITION
        )
