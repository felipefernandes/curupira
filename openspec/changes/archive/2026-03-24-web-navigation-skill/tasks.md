## 1. Setup and Dependencies

- [x] 1.1 Add `trafilatura` and `httpx` to `requirements.txt`.
- [x] 1.2 Verify if `trafilatura` installs correctly on the target environment (RPi3 simulation).

## 2. Skill Implementation

- [x] 2.1 Create `skills/web_navigation.py` inheriting from `BaseSkill`.
- [x] 2.2 Implement the `name`, `display_name`, `description`, and `parameters` properties.
- [x] 2.3 Implement the `execute` method with action dispatch logic.
- [x] 2.4 Implement the internal `_extract` method using `httpx` and `trafilatura`.
- [x] 2.5 Implement the internal `_summarize` method that uses extraction + AI provider.
- [x] 2.6 Add error handling for common HTTP issues (404, 403, timeouts).
- [x] 2.7 Implement text length limits and HTML fetch size limits for RAM safety.

## 3. Registration and Integration

- [x] 3.1 Register the new skill in `core/agent.py`.
- [x] 3.2 Update `ROADMAP.md` to reflect the completion of the Web Navigation skill.

## 4. Testing and Validation

- [x] 4.1 Test the `extract` action with a plain article URL.
- [x] 4.2 Test the `summarize` action and verify the Brazilian Portuguese output.
- [x] 4.3 Test resilience with invalid URLs and large pages.
- [x] 4.4 Run `iara analyze` (or `ruff` and `bandit`) on the new files.
