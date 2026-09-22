# Windows desktop setup — September 21, 2026

Mr. Owl was built, installed for the current Windows user and launched against this repository.

## Verified

- Node.js 24.18.0, npm 12.0.2, Visual Studio 2022 C++ Build Tools and WebView2 were already installed.
- Installed Rust stable 1.98.1, x86_64-pc-windows-msvc, minimal profile. Global PATH was not changed.
- Both Codex and Claude reported existing account sign-ins under the owner's Windows account.
- Created blank .env from .env.example and verified Git ignores it. Native CLI logins remain in their existing secure stores.
- Initialized local Git metadata; no commit, remote or publication was made.
- Installer completed with exit code 0. The running app reported this repository.
- FinalCoat's six tabs loaded at widths 1440 and 650 with no JavaScript page errors.
- Loaded all four sample-card landing pages and checked all registered tab files exist.
- Voice was unconfigured/inactive; Win-key shortcut and permission bypass were false; no agent sessions were started.
- Project MCP configuration remains empty. Existing global CLI integrations were not changed.
- FinalCoat is pinned. The four samples were explicitly archived, retaining their media and files. Teaching Studio was preserved.

## Launch

Double-click Start Mr. Owl.cmd. No rebuild is needed for ordinary use or Markdown/card content changes.

In Chats, press +, choose Codex or Claude, select this repository and name the chat FinalCoat Concepts. Existing global CLI integrations may be inherited by a new CLI session; no new MCP connections were configured during setup.

## Rebuild on this machine

Setup.ps1 -Mode Desktop encountered npm 12 EALLOWSCRIPTS while running nested npm scripts. A local Tauri command override successfully avoided that nesting without changing global npm configuration or application source.

Run from this repository in PowerShell:

    $env:PATH = 'C:\Users\jaybo\.cargo\bin;' + $env:PATH
    New-Item -ItemType Directory -Force .cache/setup | Out-Null
    Set-Content .cache/setup/build-config.json '{"build":{"beforeBuildCommand":"node desktop/prepare.mjs"}}' -Encoding ASCII
    npm.cmd ci
    & .\node_modules\.bin\tauri.cmd build --config .cache/setup/build-config.json

Installer output: src-tauri/target/release/bundle/nsis/Mr. Owl Workspace_0.1.0_x64-setup.exe.

The original Setup.ps1/npm desktop:build route has not been patched for npm 12. Use the command above on this machine. Obtain permission before installing an update that interrupts a running app or chat.

## FinalCoat

The owner's directly supplied game summary is recorded in projects/finalcoat/README.md and workspace/2026-09-21_finalcoat/. The share URL itself could not be fetched.

No generation tool or budget is selected and no paid jobs ran. The roller/tray/bucket set is only a proposed first asset. Modeling software, target engine and technical asset constraints still need the owner's choice.
