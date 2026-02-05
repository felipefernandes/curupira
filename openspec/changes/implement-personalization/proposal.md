# Implement Personalization (Phase 3)

## Why
To create a deeper connection with the user, Curupira must recognize them not just by ID, but by name and preference. The "Onboarding" experience establishes this relationship, and persistent memory of these traits ensures the assistant feels "alive" and tailored to the specific user.

## What Changes
- **Onboarding Flow:** When a known user interacts for the first time (or if name is missing), trigger an interview flow to ask for their name and preferred surname.
- **Fact Storage:** Explicitly store `preferred_name` and `surname` in the `users` table (schema update required).
- **Personality Adaptation:** The bot will analyze interactions to deduce and store personality traits (e.g., "likes brevity", "technical focus") in `facts`, adjusting its system prompt accordingly.

## Impact
- **Database:** `users` table schema change (alter table or use `facts` strictly? Design decision: use `facts` to keep schema simple/nosql-like, or add columns? Let's use `facts` for flexibility as per "Lite" philosophy).
- **Bot Logic:** `responder` needs a state machine or check for "is_onboarded".
- **Specs:** New `personalization` capability; updates to `memory`.
