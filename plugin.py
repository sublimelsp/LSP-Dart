from LSP.plugin import __version__
from LSP.plugin import AbstractPlugin
from LSP.plugin import Request
from LSP.plugin.core.registry import LspTextCommand  # TODO: Move to public API
from LSP.plugin.core.typing import Any, Tuple
from LSP.plugin.core.views import text_document_position_params  # TODO: Move to public API
import os
import sublime
import shutil


class DartAnalysisServer(AbstractPlugin):

    @classmethod
    def name(cls) -> str:
        return "Dart-Analysis"

    @classmethod
    def configuration(cls) -> Tuple[sublime.Settings, str]:
        settings, file_name, sdk_path = cls.dart_sdk()
        command = [cls.dart_exe(sdk_path), cls.server_snapshot(sdk_path)]
        command.append("--lsp")
        command.append("--client-id")
        command.append("Sublime Text LSP")
        command.append("--client-version")
        command.append(".".join(map(str, __version__)))
        settings.set("command", command)
        return settings, file_name

    @classmethod
    def dart_sdk(cls) -> Tuple[sublime.Settings, str, str]:
        # TODO: This entire function is bad
        sdk_path = ""
        if "DART_SDK" in os.environ:
            sdk_path = os.environ["DART_SDK"]
        settings, file_name = super().configuration()
        env = settings.get("env")
        if isinstance(env, dict) and "DART_SDK" in env:
            sdk_path = env["DART_SDK"]
        if not sdk_path:
            via_shutil = shutil.which("dart")
            if via_shutil:
                sdk_path = os.path.dirname(os.path.dirname(via_shutil))
            else:
                platform = sublime.platform()
                if platform == "linux":
                    candidate = "/usr/lib/dart"
                    if os.path.exists(candidate):
                        sdk_path = candidate
                # TODO: Implement this
                elif platform == "windows":
                    sdk_path = ""
                else:
                    sdk_path = ""
        return settings, file_name, sdk_path

    @classmethod
    def bindir(cls, sdk_path: str) -> str:
        return os.path.join(sdk_path, "bin")

    @classmethod
    def dart_exe(cls, sdk_path: str) -> str:
        return os.path.join(cls.bindir(sdk_path), "dart")

    @classmethod
    def server_snapshot(cls, sdk_path: str) -> str:
        return os.path.join(
            cls.bindir(sdk_path), "snapshots", "analysis_server.dart.snapshot")

    # handle custom notifications

    def m___analyzerStatus(self, params: Any) -> None:

        def run() -> None:
            session = self.weaksession()
            if session:
                analyzing = isinstance(params, dict) and params.get("isAnalyzing")
                status_key = self.name() + "_analyzing";
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
    session_name = DartAnalysisServer.name()

    def run(self, edit: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        req = Request("dart/reanalyze")
        session.send_request(
            req,
            lambda r: sublime.set_timeout(
                lambda: self.on_result(r)))

    def on_result(self, params: Any) -> None:
        if not self.view.is_valid():
            return
        window = self.view.window()
        if not window:
            return
        window.status_message("Re-analyzed")


class LspDartTextDocumentSuper(LspTextCommand):
    session_name = DartAnalysisServer.name()

    def run(self, edit: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        params = text_document_position_params(self.view, self.view.sel()[0].b)
        req = Request("dart/textDocument/super", params)
        session.send_request(req, self.on_result)

    def on_result(self, params: Any) -> None:
        if not isinstance(params, dict):
            return
        # TODO: Implement me

