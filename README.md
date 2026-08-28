# LSP-systemd

systemd unit file support for Sublime Text's LSP plugin, provided through
[systemd-lsp](https://github.com/JFryy/systemd-lsp).

Provides diagnostics, context-aware autocompletion, hover documentation, and
formatting for `.service`, `.socket`, `.timer`, `.mount`, `.automount`,
`.swap`, `.target`, `.path`, `.slice`, `.scope`, as well as 
Quadlet `.container`,`.volume`, `.kube`, `.pod`, `.image`, and `.build` unit files. 

## Installation

1. Install [LSP](https://packagecontrol.io/packages/LSP), [Systemd](https://packagecontrol.io/packages/Systemd)
   (syntax highlighting), and [LSP-systemd](https://packagecontrol.io/packages/LSP-systemd)
   from Package Control.
2. Restart Sublime Text.

> [!NOTE]
>
> The plugin does not distribute but download language server binaries from
> the official [systemd-lsp releases](https://github.com/JFryy/systemd-lsp/releases).

## Configuration

Open configuration file by running `Preferences: LSP-systemd Settings` from
the Command Palette or via Main Menu
(`Preferences > Package Settings > LSP > Servers > LSP-systemd`).
