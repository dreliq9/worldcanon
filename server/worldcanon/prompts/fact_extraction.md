You are extracting atomic facts from prose for a worldbuilding canon ledger.

Source: {source}

Text:
{text}

Extract every atomic claim about a specific named entity in the text. A "named entity" is anything wikilinked as [[Entity]] OR mentioned by name (use your judgment — capitalised proper nouns that appear to be characters, places, factions, items, or events).

Each fact should:
- Be a single self-contained claim
- Name the entity it's about (so the ledger can route it)
- NOT include speculation or fan theories — only what the text actually says

Output strict JSON, nothing else:

{{"proposed_facts": [{{"entity": "<entity name>", "claim": "<atomic claim>", "confidence": "high|medium|low"}}]}}

If no facts can be extracted, output: {{"proposed_facts": []}}
