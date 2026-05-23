You are triaging a worldbuilder's old document so it can be filed into the right folder of their vault.

Filename: {filename}

Content (first ~2000 characters):
{content}

Choose ONE classification from this list:
- canon — finished or polished chapters, settled lore
- drafts — work-in-progress scenes, partial chapters, ideas that have prose
- entities/characters — describes one named character
- entities/places — describes one named place
- entities/factions — describes one named faction or organization
- entities/items — describes one named item
- entities/events — describes one named event
- research — external reference, real-world notes, citations
- discard — too short, off-topic, junk

Output strict JSON, nothing else:

{{"classification": "<one of the values above>", "confidence": "high|medium|low", "reasoning": "<one short sentence>"}}
