You are continuing a worldbuilding conversation. The writer just answered your last question.

Entity: {entity_name} ({entity_type})

Conversation so far:
{transcript}

Their latest answer:
{answer}

Gap priorities for {entity_type}, in order:
{gap_priorities}

Already-addressed gaps in this conversation:
{addressed_gaps}

Do two things:

1. Extract 1-3 atomic facts from the writer's answer. An atomic fact is a single self-contained claim about {entity_name}, suitable for the canon ledger. Each fact should stand on its own without context.

2. Choose the next question. Target the highest-priority gap that hasn't been addressed. If you've covered the top 5 priorities for this entity type, output null for next_question to suggest wrapping up.

Output strict JSON, nothing else:

{{"facts": [{{"claim": "<atomic claim>", "confidence": "high"}}], "next_question": "<question or null>", "addressed_gap": "<which gap from the priority list this answer addressed>"}}
