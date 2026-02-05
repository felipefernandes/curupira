# Design: Personalization & Onboarding

## Goals
- Identify user by a self-chosen name/surname.
- Adapt to user's communication style.
- Minimal disruption: Onboarding should happen naturally.

## Architecture

### 1. Data Model (Leveraging existing SQLite)
No new tables needed. We will use the `facts` table (Key-Value) for flexibility.
- Key: `personal_name` (User's first name choice)
- Key: `personal_surname` (User's surname choice)
- Key: `assistant_nickname` (If user names the bot)
- Key: `trait_verbosity` (High/Low)
- Key: `trait_tone` (Formal/Casual)

### 2. Onboarding Logic (The "Handshake")
Modified `responder` flow:
1.  **Check:** Does user have `personal_surname` fact?
2.  **If No:** Enter `OnboardingState`.
    -   *Turn 1:* "Olá! Sou o Curupira. Antes de começarmos, como gostaria de ser chamado?"
    -   *Turn 2:* "Como sou único, qual sobrenome devo usar para me diferenciar dos outro Curupiras?"
    -   *Finish:* Save facts, exit state, resume normal chat.
3.  **If Yes:** Proceed to `get_ai_response`.

### 3. Prompt Injection
Update `get_ai_response` prompt:
```text
[User Profile]
Name: {personal_name}
Surname: {personal_surname}
Key Traits: {traits_summary}
```

## Risks
- **State Management:** Storing "current state" (e.g., waiting for surname) usually requires a `states` table or memory.
- **Mitigation:** For "Lite" version, we can use a runtime dictionary `user_states = {}` in Python memory (RAM). If bot restarts, onboarding acts as "fresh start" if not completed (acceptable).
