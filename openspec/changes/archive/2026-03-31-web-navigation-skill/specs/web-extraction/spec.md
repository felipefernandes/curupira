## ADDED Requirements

### Requirement: URL Text Extraction
The system SHALL accept a URL and return the clean text content from the page, removing boilerplate like navigation, ads, and footers.

#### Scenario: Successful Text Extraction
- **GIVEN** a valid URL to a text-heavy article
- **WHEN** the `extract` action is called
- **THEN** the system returns a JSON object with the status `success` and the `data` field containing the cleaned text.

### Requirement: Async Handling and Resilience
The extraction process MUST be asynchronous and MUST handle HTTP errors or timeouts without crashing.

#### Scenario: Handling 404 Error
- **GIVEN** a URL that does not exist
- **WHEN** the `extract` action is called
- **THEN** the system returns a JSON object with status `error` and an appropriate error message.

### Requirement: Memory Safety
The system SHALL limit the size of the fetched HTML and the extracted text to prevent Out-of-Memory (OOM) errors on the Raspberry Pi 3.

#### Scenario: Large Page Truncation
- **GIVEN** a URL to a very large page (e.g., 5MB HTML)
- **WHEN** the `extract` action is called
- **THEN** the system fetches only the first 500KB and truncates the final extracted text to 10,000 characters.
