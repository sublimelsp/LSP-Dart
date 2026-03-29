from __future__ import annotations

from LSP.plugin import __version__
from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import LspTextCommand
from LSP.plugin import notification_handler
from LSP.plugin import register_plugin
from LSP.plugin import Request
from LSP.plugin import unregister_plugin
from LSP.plugin import WorkspaceFolder
from LSP.plugin.core.views import location_to_encoded_filename
from LSP.plugin.core.views import text_document_position_params
from LSP.protocol import Location
from LSP.protocol import Range
from LSP.protocol import TextDocumentPositionParams
from LSP.protocol import URI
from os import environ
from os.path import dirname
from os.path import join
from os.path import realpath
from typing import final
from typing import TypedDict
from typing_extensions import NotRequired
from typing_extensions import override
import shutil
import sublime


class PublishClosingLabelsParams(TypedDict):
    labels: list[Label]
    uri: URI


class Label(TypedDict):
    label: str
    range: Range


class PublishOutlineParam(TypedDict):
    outline: Outline
    uri: URI


class Outline(TypedDict):
    children: list[Outline]
    codeRange: Range
    element: Element
    range: Range


class Element(TypedDict):
    kind: str
    name: str
    parameters: NotRequired[str]
    range: Range
    returnType: NotRequired[str]
    typeParameters: NotRequired[str]


class PublishFlutterOutlineParam(TypedDict):
    outline: FlutterOutline
    uri: URI


class FlutterOutline(TypedDict):
    attributes: NotRequired[list[FlutterOutlineAttribute]]
    children: list[Outline]
    className: NotRequired[str]
    codeRange: Range
    dartElement: NotRequired[Element]
    kind: str
    label: NotRequired[str]
    range: Range
    variableName: NotRequired[str]


class FlutterOutlineAttribute(TypedDict):
    name: str
    label: str


def build_label(view: sublime.View, label: str) -> str:
    html_template = "<div style='color: {foreground}'>// {text}</div>"
    try:
        style = view.style_for_scope('comment.line')
        foreground = style['foreground']
    except:
        foreground = 'color(var(--foreground) blend(var(--background) 30%))'
    return html_template.format(
            foreground=foreground,
            text=label)


def getenv(configuration: ClientConfig, key: str) -> str | None:
    value = configuration.env.get(key)
    if value:
        return realpath(value)
    value = environ.get(key)
    if value:
        return realpath(value)
    return None


def which_realpath(exe: str) -> str | None:
    if path := shutil.which(exe):
        return realpath(path)
    return None


def flutter_root_to_dart_sdk(flutter_root: str) -> str:
    return join(flutter_root, "bin", "cache", "dart-sdk")


def plugin_loaded() -> None:
    register_plugin(Dart)


def plugin_unloaded() -> None:
    unregister_plugin(Dart)


@final
class Dart(AbstractPlugin):
    phantom_key = "flutter_closing_labels"

    @classmethod
    @override
    def name(cls) -> str:
        return "Dart"

    @classmethod
    @override
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        sdk_path: str | None = None
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

    def closing_labels(self, view: sublime.View, labels: list[Label]) -> list[sublime.Phantom] | None:
        phantoms: list[sublime.Phantom] = []
        for label in labels:
            final_character_position = label["range"]["end"]
            if final_character_position["character"] < 1:
                return None
            row = label["range"]["end"]["line"]
            point = view.line(view.text_point(row, 0)).end()
            region = sublime.Region(point, point + 1)
            phantoms.append(sublime.Phantom(
                region,
                build_label(view, label["label"]),
                sublime.LAYOUT_INLINE))
        return phantoms

    # handle custom notifications

    @notification_handler("dart/textDocument/publishClosingLabels")
    def on_dart_text_document_publish_closing_labels(self, params: PublishClosingLabelsParams) -> None:
        session = self.weaksession()
        if not session:
            return
        sb = session.get_session_buffer_for_uri_async(params["uri"])
        if not sb:
            return
        for sv in sb.session_views:
            try:
                phantom_set = sv._lsp_dart_labels
            except AttributeError:
                phantom_set = sublime.PhantomSet(sv.view, self.phantom_key)
                sv._lsp_dart_labels = phantom_set
            closing_labels = self.closing_labels(sv.view, list(reversed(params["labels"])))
            phantom_set.update(closing_labels or [])

    @notification_handler("dart/textDocument/publishOutline")
    def on_dart_text_document_publish_outline(self, params: PublishOutlineParam) -> None:
        # TODO: Implement me.
        pass

    @notification_handler("dart/textDocument/publishFlutterOutline")
    def on_dart_text_document_publish_flutter_outline(self, params: PublishFlutterOutlineParam) -> None:
        # TODO: Implement me.
        pass


@final
class LspDartReanalyzeCommand(LspTextCommand):
    session_name = Dart.name()

    @override
    def run(self, _: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        req: Request[None, None] = Request("dart/reanalyze")
        session.send_request(req, self.on_result)

    def on_result(self, params: None) -> None:
        if not self.view.is_valid():
            return
        window = self.view.window()
        if not window:
            return
        window.status_message("Re-analyzed")


@final
class LspDartSuperCommand(LspTextCommand):
    session_name = Dart.name()

    @override
    def run(self, _: sublime.Edit) -> None:
        session = self.session_by_name(self.session_name)
        if not session:
            return
        params = text_document_position_params(self.view, self.view.sel()[0].b)
        req: Request[TextDocumentPositionParams, Location | None] = Request("dart/textDocument/super", params)
        session.send_request(req, self.on_result)

    def on_result(self, params: Location | None) -> None:
        window = self.view.window()
        if not window:
            return
        if not isinstance(params, dict):
            sublime.error_message("No superclass found")
            return
        window.open_file(
            location_to_encoded_filename(params), flags=sublime.ENCODED_POSITION
        )
