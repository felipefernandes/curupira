## ADDED Requirements
### Requirement: Onboarding Flow
The system MUST initiate an introduction sequence for new or unrecognized users to establish identity.

#### Scenario: First Contact
- **GIVEN** a user interacts with the bot for the first time
- **WHEN** the user sends a message
- **THEN** the bot MUST reply introducing itself
- **AND** the bot MUST ask "Como gostaria de ser chamado?"

#### Scenario: Capturing Identity
- **GIVEN** the bot asked for the user's name
- **WHEN** the user replies
- **THEN** the bot MUST ask for the surname ("Qual sobrenome devo usar?")
- **WHEN** the user replies with surname
- **THEN** the bot MUST save the names as facts

### Requirement: Personality Adaptation
The system MUST remember the user's interaction preferences.

#### Scenario: Remembering Traits
- **GIVEN** the system detects a preference
- **THEN** the system MUST store this as a fact

### Requirement: Personalization Prompting
The system MUST inject profile data into the prompt.

#### Scenario: Using User Name
- **GIVEN** the user has completed onboarding
- **WHEN** the bot generates a response
- **THEN** it MUST use the proper surname in the answer context
