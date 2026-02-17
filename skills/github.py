"""
Skill: GitHub Integration (MCP)

Configura o servidor MCP do GitHub para integração com o AgentBrain.
O servidor expõe ferramentas como: github_list_repos, github_list_issues, github_create_issue.

Uso:
    from skills.github import configure
    configure()  # Antes de brain.start_mcp_clients()

Nota: O token é lido de GITHUB_PERSONAL_ACCESS_TOKEN no ambiente (.env).
Se a variável estiver definida tanto no .env quanto no sistema, o valor
explícito do ambiente do sistema tem prioridade.
"""

import os
import sys
import logging
from pathlib import Path
from core.config import MCP_SERVERS

logger = logging.getLogger(__name__)

# Path to the GitHub MCP server script (co-located in skills/)
_SERVER_SCRIPT = str(Path(__file__).parent / "github_server.py")


def configure() -> bool:
    """
    Registers the GitHub MCP server configuration programmatically.

    This injects the server definition into MCP_SERVERS so that
    AgentBrain.start_mcp_clients() can discover and connect to it.

    Returns:
        True if the server is configured (or was already configured).
        False if configuration was skipped due to missing token or script.
    """
    if "github" in MCP_SERVERS:
        logger.debug("GitHub MCP server already configured, skipping.")
        return True

    if not os.path.exists(_SERVER_SCRIPT):
        logger.error(f"GitHub server script not found: {_SERVER_SCRIPT}")
        return False

    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        logger.warning(
            "GITHUB_PERSONAL_ACCESS_TOKEN not set. "
            "GitHub skill will not be available."
        )
        return False

    # Sanity check on token format
    if not token.startswith("ghp_") and not token.startswith("github_pat_"):
        logger.warning(
            "GITHUB_PERSONAL_ACCESS_TOKEN has unexpected format. "
            "Expected 'ghp_...' or 'github_pat_...'. Proceeding anyway."
        )

    MCP_SERVERS["github"] = {
        "command": sys.executable,
        "args": [_SERVER_SCRIPT],
    }
    logger.info("GitHub MCP server configured via skills/github.py")
    return True
