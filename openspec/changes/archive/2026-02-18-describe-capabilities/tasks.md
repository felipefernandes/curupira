# Tasks: Skill Introspection

1.  Create `skills/introspection.py` with `IntrospectionSkill` class.
    - [x] Implement `__init__` accepting `agent_brain`.
    - [x] Implement `describe_capabilities` tool logic (list/detail).
2.  Update `core/agent.py` to register `IntrospectionSkill`.
    - [x] Import `IntrospectionSkill`.
    - [x] Initialize and register in `__init__`.
3.  Add Unit Tests.
    - [x] Create `tests/test_introspection_skill.py`.
    - [x] Test listing skills (mocking agent).
    - [x] Test detailing specific skill.
    - [x] Test handling non-existent skill.
4.  Verification.
    - [ ] Run bot and test "O que você sabe fazer?".
    - [ ] Run bot and test "Como funciona a skill github?".
