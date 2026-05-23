# Hotkeys

Worldbuilder Canon has 14 commands. You won't use all of them daily. Set
hotkeys for the five you'll use constantly — the rest stay in the command
palette.

---

## The five worth binding

| Command | Recommended | What it does |
|---------|-------------|--------------|
| `Canon: Log brainstorm` | **Ctrl+Shift+B** | Capture an idea fast, without breaking flow |
| `Canon: Open pane` | **Ctrl+Shift+C** | Toggle the Canon side panel |
| `Canon: Search` | **Ctrl+Shift+K** | Concept-aware search across your world |
| `Canon: Ask about my world` | **Ctrl+Shift+A** | Ask in plain English, get an answer with citations |
| `Canon: Develop this entity` | **Ctrl+Shift+D** | When stuck on a character — get a probing question |

(Ctrl+Shift+F is taken by Obsidian's built-in search, so Canon's gets
Ctrl+Shift+K instead.)

---

## How to set them

This vault ships with these hotkeys **already configured** in
`.obsidian/hotkeys.json`. Open Obsidian on this vault and they should
just work.

To change one (or add others):

1. **Settings** (gear icon, bottom left) → **Hotkeys**
2. Search for "Canon"
3. Click the `+` next to a command, press the keys you want
4. Done. Obsidian saves automatically.

---

## Reset if something breaks

If a hotkey conflicts with an Obsidian default or another plugin:

1. Settings → Hotkeys → search "Canon"
2. Click the `×` next to the broken binding
3. Re-add it with a different key combo

You're never locked in. The plugin remembers nothing about hotkeys; it's
all Obsidian config.

---

## Other commands worth knowing about

Use the command palette (`Ctrl+P`) for these. They're not daily, but
they're useful:

- `Canon: New entity` — scaffold a new entity sheet (asks for name and
  type)
- `Canon: Extract facts from selection` — highlight prose, get fact
  proposals
- `Canon: Process to canon` — same, but for the whole current note
- `Canon: Show unprocessed` — list of brainstorm notes you haven't
  triaged
- `Canon: Show timeline` — chronological view of facts with chapter
  numbers
- `Canon: Find unlinked mentions` — entity names in prose that aren't
  wikilinked
- `Canon: Triage inbox` — for migrating old documents (see INSTALL.md)
- `Canon: Suggest names` — propose names from a culture's conventions
- `Canon: Rename entity` — safely rename a character across all
  wikilinks and references
- `Canon: Contradiction check` — flag claims in current text that
  conflict with established facts
- `Canon: Toggle GM / Player view` — switch the Canon side pane
  between "see everything" (GM) and "see only what players know"
  (Player). Useful if you're running a TTRPG in this vault and want
  to spot-check what your players collectively know.
- `Canon: Export player wiki` — write a player-safe copy of every
  entity sheet (secrets stripped) to `exports/player-wiki-<date>/`.
  Drop the folder in a shared drive and your players have a curated
  lore reference.
