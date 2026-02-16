"""
Skill: GitHub Integration (MCP)

Configura o servidor MCP do GitHub para integração com o AgentBrain.
O servidor expõe ferramentas como: github_list_repos, github_list_issues, github_create_issue.

Uso:
    import skills.github
    skills.github.configure()  # Antes de brain.start_mcp_clients()
"""

import os
import sys
import logging
from pathlib import Path
from core.config import MCP_SERVERS

logger = logging.getLogger(__name__)

# Path to the GitHub MCP server script (co-located in skills/)
_SERVER_SCRIPT = str(Path(__file__).parent / "github_server.py")


def configure():
    """
    Registers the GitHub MCP server configuration programmatically.
    
    This injects the server definition into MCP_SERVERS so that
    AgentBrain.start_mcp_clients() can discover and connect to it.
    
    If the server is already configured (e.g., via mcp.json), this is a no-op.
    Requires GITHUB_PERSONAL_ACCESS_TOKEN in the environment.
    """
    if "github" in MCP_SERVERS:
        logger.debug("GitHub MCP server already configured, skipping.")
        return

    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        logger.warning(
            "GITHUB_PERSONAL_ACCESS_TOKEN not set. "
            "GitHub skill will not be available."
        )
        return

    MCP_SERVERS["github"] = {
        "command": sys.executable,
        "args": [_SERVER_SCRIPT],
    }
    logger.info("GitHub MCP server configured via skills/github.py")
