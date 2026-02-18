# Tasks: Implement RSS Skill

- [x] **Dependency Management**
  - [x] Add `feedparser` to `requirements.txt`
  - [x] Install dependency

- [x] **Core Implementation**
  - [x] Create `skills/rss.py` with `RssSkill` class
  - [x] Implement `rss_read` method (fetch & parse)
  - [x] Implement `rss_list` method (read from config)
  - [x] Add `RSS_FEEDS` to `core/config.py` (default structure)

- [x] **Integration**
  - [x] Register `RssSkill` in `core/agent.py`

- [x] **Validation**
  - [x] Add unit tests `tests/test_rss_skill.py`
  - [x] Verify functioning with a real feed (e.g., G1, Hacker News)
