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

Download from <https://obsidian.md/download>. Don't create a vault yet —
you'll use the starter vault that came with this zip (see Step 2 below).

### 2. Place your vault

Inside the zip you extracted, there's a folder called `starter-vault`.
**Copy that folder** to where you want your stories to live — typically
your Documents folder. Rename it to something meaningful (e.g.,
`WorldVault`, or the working title of your novel).

So you should end up with something like:
`C:\Users\<you>\Documents\WorldVault\` containing folders called `canon`,
`drafts`, `entities`, etc. and notes called `00 — Start here.md` and so
on.

**Write down the path** — you'll need it when running install.ps1 below.

> Don't have a vault to use as a starting point? You can skip this step,
> create an empty folder, point install.ps1 at it, and start from
> scratch — but the starter vault has example entity sheets and notes
> that explain the system. Recommended.

### 3. Ollama (for the LLM)

Download from <https://ollama.com/download> and run the installer.

**Pick a model based on your computer's RAM.** Bigger models give better
answers but use more memory and run slower. To find your RAM: press
**Windows + Pause/Break**, or right-click "This PC" → Properties.

| Your RAM | Recommended model | `ollama pull` command | Disk |
|----------|-------------------|------------------------|------|
| 8 GB     | phi3:mini         | `ollama pull phi3:mini`     | 2.3 GB |
| 16 GB    | gemma3:4b (default) | `ollama pull gemma3:4b`   | 3.3 GB |
| 32 GB+   | qwen2.5:14b       | `ollama pull qwen2.5:14b`   | 9 GB |

Open PowerShell (Start menu → type "PowerShell"), paste the command for
your RAM tier, hit Enter. Wait for the download — bigger models take
several minutes on a slow connection.

**Changing the model later:** if you picked `phi3:mini` and want to try
`gemma3:4b` later:
1. `ollama pull gemma3:4b` to download it
2. Set the environment variable `WORLDCANON_LLM_MODEL` to the new model
   name. (Windows: Start menu → "Environment Variables" → New, name
   `WORLDCANON_LLM_MODEL`, value `gemma3:4b`.)
3. Restart the sidecar: `Stop-ScheduledTask -TaskName WorldbuilderCanonSidecar; Start-ScheduledTask -TaskName WorldbuilderCanonSidecar`

### 4. Pandoc (for the document importer)

Only required if you want to import existing `.docx`, `.html`, or `.rtf`
files into the vault. Download from <https://pandoc.org/installing.html>.
Use the default install location.

---

## Install the sidecar

1. Extract `worldcanon-windows-x64.zip`. You should see a folder containing:
   - `worldcanon-sidecar\` (a subfolder)
   - `worldcanon-import.exe`
   - `install.cmd` ← **the one you double-click**
   - `install.ps1` (used by install.cmd; don't run directly)
   - `uninstall.cmd`, `diagnose.cmd`, and their `.ps1` counterparts
   - This `INSTALL.md`
2. **Double-click `install.cmd`.** A blue PowerShell window opens.
   - If Windows SmartScreen flags it, click **More info → Run anyway**.
   - You should NOT need to mess with ExecutionPolicy — `install.cmd`
     launches PowerShell with the right flags already set.
3. When prompted, paste the path to your vault folder (e.g.,
   `C:\Users\<you>\Documents\WorldVault`) and press Enter.
4. The window stays open with the result. If install succeeded, press
   Enter to close it. If it failed, the error is right there — read it
   or send a screenshot to Adam.

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
- `install.cmd` ← double-click this
- `install.ps1` (used by install.cmd)

Double-click the plugin's `install.cmd`. Paste the same vault path you
used for the sidecar.

---

## Enable the plugin in Obsidian

1. Open your vault in Obsidian (File → Open vault → point at the folder
   you copied in Step 2).
2. **Settings → Community plugins**.
3. If "Restricted mode" is on, click **Turn off**. (The starter vault
   pre-enables the Worldbuilder Canon plugin — Restricted mode is the
   only thing blocking it.)
4. The plugin should now be active. Verify: look at the bottom-right of
   the Obsidian window. You should see `Canon: ✓ N chunks, M facts` in
   green. If it's red, the sidecar isn't reachable — see Verify above.

---

## First steps

**If you used the starter vault, the very first thing to do is open
`00 — Start here.md`** (top of the file explorer on the left). It walks
through the concepts you need before the commands make sense.

Otherwise, open the command palette (Ctrl+P) and try:
- `Canon: Open pane` — Canon side pane appears
- `Canon: New entity` — creates an entity sheet
- `Canon: Search` — fuzzy search across the vault
- `Canon: Ask about my world` — ask the LLM a question
- `Canon: Develop this entity` — one-question-at-a-time ideation

The starter vault also pre-configures five hotkeys (Ctrl+Shift+B for
brainstorm, etc.) — see `04 — Hotkeys.md` inside the vault for details.
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

**Before troubleshooting anything else: double-click `diagnose.cmd`** in
the install folder (or in `%LOCALAPPDATA%\WorldbuilderCanon\` if the
install at least started). It captures sidecar logs, the `/stats`
endpoint, Ollama state, plugin version, and system specs into a zip on
your Desktop. Send that zip to Adam — he can usually answer in one
round-trip instead of playing twenty questions.

The diagnose script is read-only: it doesn't restart anything or change
any settings, and it does NOT include your story content.

**A blue PowerShell window flashes open then closes immediately.**
This means the script ran (or errored) and the window auto-closed
before you could read it. Use `install.cmd` (double-click), not
`install.ps1` directly — the `.cmd` wrapper holds the window open
with the result. If you only have a v0.1.1 zip (no `.cmd` files), ask
Adam for the v0.1.2 zip.

**Status bar shows red "sidecar down".**
The sidecar isn't running. Open Task Scheduler, find
`WorldbuilderCanonSidecar`, click Run. Check the last run result for errors.

**`Canon: Ask about my world` returns "LLM unavailable".**
The plugin's error toast usually tells you exactly what's wrong now. If
it doesn't:

1. Look at the system tray (bottom-right of the taskbar). Is the llama
   icon there? If not, open the Start menu, type "Ollama", press Enter,
   wait a few seconds.
2. Open PowerShell and run `ollama list` to see what's installed. If
   the model name you expected isn't there, run
   `ollama pull <model-name>` (e.g., `ollama pull gemma3:4b`).
3. If Ollama still won't start: open PowerShell and run `ollama serve`.
   Leave that window open while you use Canon.

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
