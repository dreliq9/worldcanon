# Concepts

Worldbuilder Canon thinks of your work in five pieces. Once you have these
in your head, every command in the plugin becomes obvious.

---

## 1. Entity

**Anything named in your world.** People, places, organizations, magic
systems, important objects, gods, ships, whatever.

Each entity gets one markdown file. The plugin tracks where it's mentioned,
what facts you've established about it, who it's connected to.

You'll find example entities under `entities/`. To make a new one, use the
command palette: **`Canon: New entity`**.

---

## 2. Fact

**An atomic claim about an entity.** Examples:

- "Lyra has a scar on her left forearm."
- "Brackwater sits at the mouth of the Bracken River."
- "Stillweaving cannot be performed during a storm."

Facts live inside an entity sheet, under a `## Facts` section, in a
specific YAML format (see `[[Lyra Vance]]` for an example). You don't have
to write them by hand — the plugin can propose facts from your drafts and
add them with one click.

**Why atomic?** Because then the plugin can answer questions like "what do
I know about Lyra's appearance?" without surfacing the entire 3,000-word
character bio.

---

## 3. Canon vs Draft (vs Retconned, Proposed)

Every fact has a **status**:

- **canon** — true in your world. Locked in.
- **draft** — you're trying this out but haven't committed.
- **proposed** — the plugin's LLM extracted this from your prose and is
  asking you to confirm it.
- **retconned** — it WAS true but you've changed your mind. Kept for
  history, hidden from "what's true now" queries.

The same distinction applies to whole files. The `canon/` folder is for
prose you've settled on; `drafts/` is for prose you're still wrestling
with. Promote a draft to canon by moving the file from `drafts/` to
`canon/`.

---

## 4. Brainstorm

**A timestamped half-formed idea.** You'll have these constantly:

> "What if Lyra's mother was the antagonist of book two?"
>
> "The northern coastline should have lighthouses. The lighthouses are
> what suppress Stillweaving on land."

You don't want these as canon. You don't want to lose them. You want a
fast capture path that says "hold this for later."

Use **`Canon: Log brainstorm`** (recommended hotkey: Ctrl+Shift+B). A
timestamped note appears in `brainstorm/`. Later, when you have ten of
these, **`Canon: Show unprocessed`** lists them so you can decide which
ones to graduate to facts, drafts, or new entities.

---

## 5. Mention

**Any `[[Wikilink]]` to an entity from prose or another sheet.**

When you write `Lyra knelt by the [[Brackwater]] harbor`, the plugin
notices Brackwater is mentioned in that scene. The Brackwater entity
sheet's "Mentions" tab in the Canon side pane will show that chapter.

This is what makes the plugin useful when you're 200,000 words deep and
can't remember "did I describe Brackwater's smell yet?"

---

## How they fit together

```
You have an idea          → brainstorm note
You write a chapter       → drafts/<chapter>.md
You name a new character  → entities/people/<Name>.md  (entity)
Inside the chapter:       → [[Name]]                    (mention)
The plugin reads prose,
proposes facts            → entries in entities/people/<Name>.md
                            under ## Facts (proposed)
You confirm or reject     → status becomes canon or is removed
You finish the chapter    → move to canon/
```

---

Next: open **[[02 — Obsidian basics]]** if Obsidian is new to you, or
skip straight to **[[03 — Daily rhythm]]**.
