# TTRPG Roadmap

Captures the work to extend Worldbuilder Canon for tabletop use, beyond
the spoiler-control + GM/player view feature being built now. Driven by
Adam's friend, who is actively running a TTRPG in his WC vault and plans
to design his own system within ~12 months.

This is a roadmap, not an implementation plan. Each section sketches
scope, motivation, and rough effort. When any of these graduates to a
concrete build, it gets its own plan doc.

---

## What's being built now (separate, not in this doc)

**Spoiler control + GM/Player view.** Every fact gets a
`player_visibility` field (`secret` | `revealed` | `hinted` |
`red_herring`). The plugin gains a view toggle (GM sees everything;
Player view filters secrets). Sidecar gets a `/export/player-wiki`
endpoint and the plugin gets a `Canon: Export player wiki` command.

This is the foundation everything below builds on.

---

## Immediate follow-ups (next 1–3 months)

### 1. `sessions/` corpus

**Why:** A TTRPG GM accumulates session recaps that aren't fiction prose
and shouldn't pollute `canon/` or `drafts/`. They're operational notes.
Right now there's no canonical home for them.

**Scope:**
- New corpus in `corpora.yaml`: `sessions/` with the `journal` chunker
  (reuse what brainstorm uses).
- New file template (created by a `Canon: New session` command):
  ```yaml
  ---
  type: session
  session: 7
  real_date: 2026-06-12
  world_date: "Third Age 3019.03.25"
  present_players: [Alex, Mira, Sam]
  npcs_appearing: [Tom, Captain Greaves]
  locations_visited: [Brackwater, the lighthouse]
  facts_revealed_to_players: ["lyra-mother-alive"]
  loose_threads: ["who rebuilt the lighthouse?"]
  ---

  # Session 7 — The Lighthouse Confrontation

  Recap...
  ```
- The `facts_revealed_to_players` field references fact IDs (or claim
  hashes). When a session note is saved, the indexer flips those facts'
  `player_visibility` to `revealed` and stamps `revealed_in_session: 7`.
  This is the "auto-reveal hook" that pairs with the spoiler-control
  feature being built now.
- `Canon: Session recap` command: opens the LLM with the session
  transcript and a "summarize this session for the players" prompt.

**Effort:** ~6 hours. New chunker (or reuse journal), new endpoint,
plugin command, tests.

---

### 2. NPC quick-roster

**Why:** TTRPG worlds spawn disposable NPCs (barkeeps, guards, random
merchants) at 10x the rate fiction does. Making a full entity sheet for
each is friction.

**Scope:**
- A convention: `entities/people/_npcs.md` is a single file with a
  YAML-list section under `## NPCs`:
  ```yaml
  ## NPCs

  - name: Tom
    role: barkeep at Brackwater Inn
    knows: ["smuggler operation", "lyra-childhood"]
    location: Brackwater
    notes: friendly but loose-lipped after two drinks
  ```
- A new chunker parses this file into individual `npc` ledger rows.
- `Canon: Quick NPC` command: prompts for name + role, appends to the
  file in the right format. Faster than creating an entity sheet.
- An NPC can graduate to a full entity sheet later; the quick-roster
  entry stays as a redirect.

**Effort:** ~3 hours. Lighter than a full entity sheet pipeline.

---

### 3. In-world calendars

**Why:** Sessions and facts happen in fictional time. The friend's world
has a calendar (Third Age, or whatever). Without first-class calendar
support, `Canon: Show timeline` either uses real dates (wrong) or
`chapter_index` (doesn't apply to TTRPG sessions).

**Scope:**
- New corpus: `calendars/<name>.md`. Each file defines a calendar with:
  ```yaml
  ---
  type: calendar
  name: Third Age
  months: [March, April, ...]
  days_per_month: [31, 30, ...]
  weeks: [Sunday, Monday, ...]
  era_marker: "TA"
  ---
  ```
- Facts and session notes get a `world_date` field (e.g.,
  `world_date: "TA 3019.03.25"`).
- `Canon: Show timeline` accepts a `calendar:<name>` filter, renders
  events sorted by world_date instead of chapter_index.
- The calendar file can also list named events (festivals, historical
  battles) which appear on the timeline automatically.

**Effort:** ~6 hours. New chunker, new fact field, timeline UI rework
to support custom date strings.

---

### 4. Plot-thread tracker

**Why:** GMs plant hooks they want to pay off later — "the lighthouse
keeper acted suspicious," "Mira's amulet glowed when she touched
Brackwater iron." Without tracking, these get forgotten and players
notice ("you set that up months ago and never came back to it").

**Scope:**
- New corpus: `threads/<thread-id>.md` files.
- Each thread has frontmatter: `status: open | resolved | abandoned`,
  `planted_in: session-N`, `targets: [entity1, entity2]`, `expected_payoff: <chapter or session>`.
- `Canon: New thread` command (called mid-session: name, status=open,
  one-line description).
- `Canon: Show open threads` command: lists all threads with
  `status: open` sorted by how long they've been open. Stale threads
  get a warning marker.
- `Canon: Resolve thread` command: marks resolved, asks for the
  session/chapter where the payoff landed, links to it.

**Effort:** ~4 hours. Mostly plugin-side; ledger gets a `threads` table
similar to facts.

---

## Mid-term (3–6 months)

### 5. Excalidraw map integration

**Why:** Every TTRPG needs maps. Building a map editor is a tarpit;
Excalidraw is an existing Obsidian plugin that already does the
drawing.

**Scope:**
- `Canon: Open map for <place>` command: looks for an Excalidraw file
  at `maps/<place>.excalidraw.md`; creates it if missing, opens it via
  Excalidraw plugin's API.
- A place's entity sheet gets a `map: maps/<place>.excalidraw.md`
  frontmatter field. The Canon side pane shows a "View map" link when
  this field is set.
- Optional: a `Canon: Annotate map` command opens the map with a
  side-by-side note panel for GM annotations.

**Effort:** ~6 hours. Mostly figuring out Excalidraw's plugin API and
the file format.

---

### 6. Session prep workflow

**Why:** GMs do a lot of just-in-time prep before a session — looking up
NPCs the party might meet, refreshing on threads, generating quick
encounters. Right now this is a manual scavenger hunt.

**Scope:**
- `Canon: Prep session N` command: takes a session number, opens a
  side-pane prep view with:
  - Open threads (from #4)
  - NPCs the party might meet (from current location's entity sheet)
  - Last session's recap (from #1)
  - Facts the party has recently learned (per session-reveal log)
- LLM-driven: "What did the party do last session?" pulls from the
  previous session note + facts revealed.

**Effort:** ~5 hours. Mostly composition of existing endpoints into a
new UI surface.

---

## Long-term (when he starts designing his own TTRPG)

These graduate from worldbuilding (the setting) to game design (the
mechanics). Different problem space.

### 7. `rules/` corpus distinct from `systems/`

**Distinction:**
- `systems/` is in-world magic / metaphysics. Sentences like
  "Stillweaving cannot be performed during a thunderstorm."
- `rules/` is game mechanics. Sentences like "A Stillweave attempt
  rolls 2d6 + Composure; on 8+, it succeeds; on 12+, exceptional."
- They reference each other but live separately. A magic system might
  span both files.

**Scope:** New corpus, new chunker, new ledger table for rules with
fields for dice notation, modifiers, success/failure tiers.

---

### 8. Class / archetype sheets

Each playable archetype gets a sheet with:
- Starting stats
- Progression tables (level → ability gains)
- Signature mechanics
- Lore tie-in (which faction/culture is this archetype from?)

The lore tie-in is where this connects back to the existing entity
system — an archetype IS an entity, with mechanics.

---

### 9. Stat-block templates

Reusable templates for NPCs, monsters, encounters. The quick-roster
NPCs (#2) might evolve to include optional stat-blocks for combat
relevance.

---

### 10. Mechanics balance analysis

When designing rules, the friend will want to ask the LLM (or run
simulations) about questions like:
- "If I add this ability, does the damage curve spike too fast?"
- "What's the expected duration of a combat at level 5?"

Could integrate Monte Carlo simulation into the LLM tool surface, or
just provide structured queries against the rules table.

**Risk:** This is its own product. Might be better left external (a
spreadsheet, a Python notebook). Reconsider when he asks.

---

### 11. System reference doc export

The "compile" path for a finished TTRPG: take `rules/`, `classes/`,
representative `entities/`, and a chosen subset of `systems/`, compile
to a publishable PDF or HTML document. The TTRPG-equivalent of the
fiction manuscript compile.

**Effort:** ~8 hours, mostly Pandoc plumbing + a layout template.

---

## Explicitly out of scope

These come up in TTRPG worldbuilding tools but we don't ship them:

- **Real-time virtual tabletop.** WC is async / single-GM-machine; VTT is
  a different product (Roll20, FoundryVTT, Owlbear Rodeo).
- **Combat tracker.** The friend already uses something for this. If he
  asks, we'd integrate (read his initiative state, surface contextual
  lore during combat) — but we won't build one.
- **Dice roller.** Obsidian has plugins for this. Don't duplicate.
- **Character sheet management for players.** Players manage their own
  sheets in whatever they use. WC tracks the GM's view.
- **Chat / Discord integration.** Out of scope; encourages always-on
  network behavior that violates the local-first principle.

---

## Dependency graph

```
spoiler-control (now)
    │
    ├─→ sessions corpus ────→ session prep workflow
    │       │
    │       └─→ auto-reveal hook (sessions flip fact visibility)
    │
    ├─→ NPC quick-roster
    │
    ├─→ in-world calendars ──→ timeline rework
    │
    └─→ plot-thread tracker

excalidraw maps  (independent)

rules corpus ──→ class sheets ──→ stat-block templates
       │                                  │
       └─→ mechanics balance              └─→ SRD export
```

---

## Decision log

- **2026-05-22.** Spoiler control prioritized over series/book scoping
  for fiction writers, because friend is actively running a TTRPG and
  this is the binding feature. Book scoping moves to v0.3 candidate.
- **2026-05-22.** Excalidraw map integration preferred over building a
  map editor. Don't repeat World Anvil's mistake of being everything to
  everyone.
- **2026-05-22.** TTRPG features stay opt-in via vault structure
  (presence of `sessions/`, `threads/`, etc. corpora). Friend's vault
  becomes TTRPG-aware; a novelist's vault stays clean.
