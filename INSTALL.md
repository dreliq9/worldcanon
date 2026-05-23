# Installing Worldbuilder Canon

This installs two pieces:
1. **Sidecar** — a small Windows program that watches your Obsidian vault and
   handles search, fact extraction, and LLM-powered features.
2. **Plugin** — runs inside Obsidian, adds the Canon side pane, commands,
   and other UI surfaces.

You need both. The plugin won't work without the sidecar.

---

## Prerequisites

Install these **once**. The order doesn't matter.

### 1. Obsidian Desktop

Download from <https://obsidian.md/download>. Create a vault folder (e.g.,
`C:\Users\<you>\Documents\WorldVault`). Write down the path — you'll need it.

### 2. Ollama (for the LLM)

Download from <https://ollama.com/download>. After installing, open a terminal
and pull a model:

```
ollama pull gemma3:4b
```

A bigger model gives better quality at the cost of speed and RAM. `gemma3:4b`
is a safe default. You can swap later by pulling a different model and
updating the sidecar's `WORLDCANON_LLM_MODEL` env variable.

### 3. Pandoc (for the document importer)

Only required if you want to import existing `.docx`, `.html`, or `.rtf`
files into the vault. Download from <https://pandoc.org/installing.html>.
Use the default install location.

---

## Install the sidecar

1. Extract `worldcanon-windows-x64.zip`. You should see a folder containing:
   - `worldcanon-sidecar\` (a subfolder)
   - `worldcanon-import.exe`
   - `install.ps1`
   - `uninstall.ps1`
   - This `INSTALL.md`
2. Right-click `install.ps1` and choose **Run with PowerShell**.
   - If Windows blocks the script: open PowerShell, run
     `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`,
     answer Y, then re-run install.ps1.
   - If Windows SmartScreen flags the script, click **More info → Run anyway**.
3. When prompted, paste the path to your vault folder (e.g.,
   `C:\Users\<you>\Documents\WorldVault`).

The script copies the sidecar to `%LOCALAPPDATA%\WorldbuilderCanon\`, creates
a Task Scheduler entry called `WorldbuilderCanonSidecar`, and starts it.
The sidecar will auto-start every time you log in.

**Verify:** open <http://127.0.0.1:7777/stats> in a browser. You should see
JSON output. If you see "this site can't be reached," the sidecar isn't
running — open Task Scheduler, find `WorldbuilderCanonSidecar`, and check
the last run result.

---

## Install the plugin

The plugin ships as a separate zip (`worldcanon-plugin.zip`). Extract it; you should see:
- `manifest.json`
- `main.js`
- `styles.css`
- `install.ps1`

Right-click the plugin's `install.ps1` and Run with PowerShell. Provide the
same vault path you used for the sidecar.

---

## Enable the plugin in Obsidian

1. Open your vault in Obsidian.
2. **Settings → Community plugins**.
3. If "Restricted mode" is on, click **Turn off**.
4. Find **Worldbuilder Canon** in the installed list and toggle it on.

You should see a status indicator at the bottom-right of the Obsidian window:
`Canon: ✓ N chunks, M facts` in green. If it's red, the sidecar isn't
reachable — see Verify above.

---

## First steps

- **Open command palette** (Ctrl+P) and try:
  - `Canon: Open pane` — Canon side pane appears
  - `Canon: New entity` — creates an entity sheet
  - `Canon: Search` — fuzzy search across the vault
  - `Canon: Ask about my world` — ask the LLM a question
  - `Canon: Develop this entity` — one-question-at-a-time ideation
- Set up a hotkey for `Canon: Log brainstorm` (Settings → Hotkeys, search
  for "Canon").
- If you have old documents to migrate, run `worldcanon-import.exe` from a
  terminal:
  ```
  cd %LOCALAPPDATA%\WorldbuilderCanon
  worldcanon-import.exe --source "C:\path\to\old\docs" --dest "C:\path\to\WorldVault\_inbox"
  ```
  Then in Obsidian, run `Canon: Triage inbox` to file the imported notes.

---

## Updating

When you receive a new release zip:

1. Run the **plugin's** `install.ps1` again (overwrites `main.js`).
2. Reload the plugin in Obsidian (Settings → Community plugins → toggle off + on).
3. For the **sidecar**: stop it, run the new sidecar's `install.ps1`, it
   will replace the old version and re-register the scheduled task.

To stop the sidecar without uninstalling:
```
Stop-ScheduledTask -TaskName WorldbuilderCanonSidecar
```

To restart:
```
Start-ScheduledTask -TaskName WorldbuilderCanonSidecar
```

---

## Uninstall

Run the sidecar's `uninstall.ps1`. By default this removes the install
folder; pass `-KeepFiles` to keep your logs and config.

For the plugin: in Obsidian, **Settings → Community plugins**, click the
trash icon next to Worldbuilder Canon. Or delete
`<Vault>\.obsidian\plugins\worldcanon-canon\` manually.

---

## Troubleshooting

**Status bar shows red "sidecar down".**
The sidecar isn't running. Open Task Scheduler, find
`WorldbuilderCanonSidecar`, click Run. Check the last run result for errors.

**`Canon: Ask about my world` returns "LLM unavailable".**
Ollama isn't running, or `WORLDCANON_LLM_MODEL` points at a model you
haven't pulled. From a terminal:
```
ollama list                # see what's installed
ollama pull gemma3:4b      # if the model is missing
ollama serve               # if the daemon isn't running
```

**Importer reports "pandoc not found on PATH".**
Install Pandoc from <https://pandoc.org/installing.html> and restart any
open terminal so PATH refreshes.

---

## Files and locations

- Sidecar binary: `%LOCALAPPDATA%\WorldbuilderCanon\worldcanon-sidecar\`
- Importer binary: `%LOCALAPPDATA%\WorldbuilderCanon\worldcanon-import.exe`
- Index database: `%LOCALAPPDATA%\WorldbuilderCanon\index.sqlite`
- Sidecar log: `%LOCALAPPDATA%\WorldbuilderCanon\sidecar.log`
- Vault: wherever you chose (the path is recorded in
  `%LOCALAPPDATA%\WorldbuilderCanon\vault-path.txt`)
- Plugin: `<Vault>\.obsidian\plugins\worldcanon-canon\`
