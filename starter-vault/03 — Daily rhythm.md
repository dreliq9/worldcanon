# Daily rhythm

What it actually looks like to use this thing day to day. Take what's
useful, ignore the rest.

---

## Opening the day

1. Open Obsidian.
2. Glance at the bottom-right status bar. **`Canon: ✓ N chunks, M facts`**
   in green means the background sidecar is running and your world is
   indexed. If it's red, see INSTALL.md troubleshooting.
3. Optional: `Canon: Open pane` (or your hotkey). Side pane shows your
   entities and recent activity.

---

## While you're writing

You're in `drafts/ch07.md`. You write:

> Lyra stepped onto the dock. The salt smell of [[Brackwater]] was the
> same as twenty years ago, but the lighthouse on the headland had been
> rebuilt.

Three things to know:

**You typed `[[Brackwater]]` — that's now a tracked mention.** Click it
to jump to the Brackwater entity sheet.

**You wrote "the lighthouse on the headland had been rebuilt" — that's a
new fact about Brackwater you may not have established yet.** Two
options:

- Highlight that sentence, run `Canon: Extract facts from selection`.
  The plugin proposes "Brackwater's lighthouse on the headland was
  rebuilt" as a fact. Confirm it, and it lands in Brackwater's sheet
  with status `proposed` (waiting for your "yes, canon").
- Or: just keep writing. Run `Canon: Process to canon` later for the
  whole chapter at once.

**An idea hits you mid-sentence:** "Wait — what if the lighthouse keeper
is Lyra's estranged uncle?" Don't break flow. Hit your
`Canon: Log brainstorm` hotkey (recommended: Ctrl+Shift+B). A capture
window opens, you type the idea, hit save. A new note appears in
`brainstorm/`. Back to your chapter.

---

## When you need to look something up

| Question | Command |
|----------|---------|
| "What have I established about Brackwater?" | Click `[[Brackwater]]` in any note |
| "Where else have I mentioned the lighthouse?" | `Canon: Search` → "lighthouse" |
| "What does my world say about Stillweaving's limits?" | `Canon: Ask about my world` → ask in plain English |
| "Have I contradicted myself in this chapter?" | `Canon: Contradiction check` |
| "I'm stuck developing this character — give me a question to chew on" | `Canon: Develop this entity` from the entity's sheet |

---

## Closing the day

These are optional. Skip them on days you don't have energy.

- **Triage brainstorms.** `Canon: Show unprocessed` lists every
  brainstorm note you've logged but not graduated. Maybe one becomes a
  new entity. Maybe three get deleted. Maybe two become facts.
- **Promote drafts.** If a chapter is settled, drag it from `drafts/`
  to `canon/`.
- **Look at the timeline.** `Canon: Show timeline` lists every fact
  you've tagged with a chapter index, in order. Good for spotting
  pacing problems.

---

## Once a week

- **`Canon: Find unlinked mentions`** scans your prose for names that
  match existing entities but are NOT wikilinked. Catches "I called her
  Lyra but didn't write `[[Lyra Vance]]`." Fix those so the plugin can
  see the mention.
- Open `naming/` and add any names you've considered but not used. The
  plugin can suggest names later, drawing from your conventions.

---

## What NOT to do

- **Don't manually edit the `## Facts` YAML by hand.** Use the
  command palette. You'll typo the format and the indexer will skip
  the malformed entry.
- **Don't put files outside the expected folders.** Worldbuilder Canon
  only indexes `canon/`, `drafts/`, `entities/`, `systems/`, `naming/`,
  `brainstorm/`, `research/`. Files in random other folders are
  invisible to the plugin.
- **Don't worry about being "right."** The status of every fact is
  changeable. `retconned` is a first-class status — your world is
  allowed to evolve.

---

Next: **[[04 — Hotkeys]]**.
