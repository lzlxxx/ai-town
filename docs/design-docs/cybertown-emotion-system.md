# CyberTown NPC Emotion System

## Goal

Add a v1 emotion layer alongside affinity. Affinity remains the long-term relationship score, while emotion represents accumulated mood tendencies that can shift over multiple interactions.

## Model

Each NPC/player pair has these in-memory emotion values:

- `joy`
- `sadness`
- `anger`
- `excitement`

The dominant emotion is calculated from the highest value. If no value reaches the neutral threshold, the dominant emotion is `neutral`.

## Storage Boundary

Version 1 keeps all emotion state in backend memory:

- `emotion_states`: current values and latest reason.
- `emotion_history`: recent changes for debugging and API inspection.

Emotion state is not written to memory metadata in v1. Restarting the backend resets emotion values to NPC baselines.

Future persistent relationship state should use a dedicated storage design instead of replaying conversation memory metadata.

## Update Flow

1. Before NPC response generation, current emotion is injected into the prompt.
2. The NPC response is generated.
3. Relationship analysis updates affinity and emotion using LLM output.
4. If LLM analysis fails or parses poorly, deterministic fallback rules provide safe emotion deltas.
5. Emotion moves slightly toward the NPC baseline after each update.
6. Updated emotion is returned in the API response and affects the next response.

## Affinity Coupling

Emotion deltas weakly influence affinity:

- Increased joy can add a small positive adjustment.
- Increased anger can add a small negative adjustment.
- Sadness does not automatically reduce affinity.
- Excitement affects expression and sharing more than liking.

Single-turn affinity changes stay clamped to avoid noisy relationship drift.

## Expression

Emotion affects:

- NPC reply style through prompt modifiers.
- Information sharing willingness.
- Godot UI display of dominant emotion.

Version 1 does not affect NPC movement, proactive behavior, or task trigger probability.

## API

`POST /chat`, `GET /npcs`, and `GET /npcs/{npc_name}` expose emotion summaries:

- `dominant`
- `label`
- `intensity`
- `level`
- `values`
- `reason`

The UI can display the label and intensity while keeping full values available for debugging.
