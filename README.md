# LSP-Dart

This is a helper package that automatically starts the [Dart Analysis Server](https://github.com/dart-lang/sdk/blob/master/pkg/analysis_server/tool/lsp_spec/README.md) for you.

To use this package, you must have:
- The [LSP](https://packagecontrol.io/packages/LSP) package.
- A Dart syntax. Try [Dartlight](https://packagecontrol.io/packages/Dartlight).
- **Either** a Flutter SDK, **or** a Dart SDK.

The language server is bundled inside the SDK. This package will attempt to utilize that fact. For this to work you must
have `FLUTTER_ROOT` defined in your environment variables or `DART_SDK` defined in your environment variables. You can
also define one of them in the `"env"` key of LSP-Dart.sublime-settings so that you can have different SDKs active per
*.sublime-project*. Run the command

```
Preferences: LSP-Dart Settings
```

to set up the environment variables.

## Applicable Selectors

This language server operates on views with the `source.dart` base scope.

## Installation Location

This helper package doesn't install any binaries.

## Server-specific commands

You can run

```
LSP-Dart: Goto Super
```

from the command palette to jump to a super class. The relevant command is `lsp_dart_super` in case you want to bind
it to a keybinding.

## Quirks

The language server is capable of "signature help", but you have to trigger it manually. Run the command

```
Preferences: LSP Keybindings
```
to find out what the keybinding is to manually invoke "signature help".

## Capabilities

Dart Analysis Server can do a lot of cool things, like

- code completion
- signature help
- hover info
- some quality code actions
- formatting
- find references
- goto def
