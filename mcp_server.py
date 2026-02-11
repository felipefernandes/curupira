import asyncio
import os
import httpx
from mcp.server.fastmcp import FastMCP

import sys

# Initialize FastMCP server

import re
from typing import Optional

# Initialize FastMCP server
mcp = FastMCP("GitHub")

GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "CurupiraBot-MCP"
} if GITHUB_TOKEN else {}

# Shared HTTP client for performance (connection pooling)
# We initialize it globally. It will be closed when process terminates.
http_client = httpx.AsyncClient(headers=HEADERS, timeout=30.0)

def validate_repo_format(repo_name: str):
    """Validates if repo_name is in 'owner/repo' format."""
    if not re.match(r"^[\w.-]+/[\w.-]+$", repo_name):
        raise ValueError(f"Invalid repository format: '{repo_name}'. Expected 'owner/repo'.")

def check_auth():
    """Checks if GITHUB_TOKEN is available."""
    if not GITHUB_TOKEN:
        raise ValueError("GitHub Token not configured (GITHUB_PERSONAL_ACCESS_TOKEN missing).")

@mcp.tool()
async def github_list_repos(limit: int = 10) -> str:
    """
    List repositories for the authenticated user.
    Args:
        limit: Number of repositories to return (default: 10).
    """
    check_auth()
    url = "https://api.github.com/user/repos"
    params = {"sort": "updated", "per_page": limit}
    
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        repos = resp.json()
        
        if not repos:
            return "No repositories found."
            
        result = []
        for repo in repos:
            result.append(f"- {repo['full_name']} (⭐ {repo['stargazers_count']})")
            
        return "\n".join(result)
    except httpx.HTTPStatusError as e:
        return f"GitHub API Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error listing repos: {str(e)}"

@mcp.tool()
async def github_list_issues(repo_name: str, state: str = "open", limit: int = 10) -> str:
    """
    List issues for a specific repository.
    Args:
        repo_name: Full repository name (e.g., "owner/repo").
        state: Issue state ("open", "closed", "all"). Default: "open".
        limit: Number of issues to return.
    """
    check_auth()
    try:
        validate_repo_format(repo_name)
    except ValueError as e:
        return str(e)

    url = f"https://api.github.com/repos/{repo_name}/issues"
    params = {"state": state, "per_page": limit}
    
    try:
        resp = await http_client.get(url, params=params)
        resp.raise_for_status()
        issues = resp.json()
        
        if not issues:
            return f"No {state} issues found in {repo_name}."
            
        result = []
        for issue in issues:
            # Skip Pull Requests (they are also listed as issues in API v3)
            if "pull_request" in issue:
                continue
                
            result.append(f"- #{issue['number']} {issue['title']} (by @{issue['user']['login']})")
            
        return "\n".join(result)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Repository '{repo_name}' not found."
        return f"GitHub API Error: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error listing issues: {str(e)}"

@mcp.tool()
async def github_create_issue(repo_name: str, title: str, body: str = "") -> str:
    """
    Create a new issue in a repository.
    Args:
        repo_name: Full repository name (e.g., "owner/repo").
        title: Issue title.
        body: Issue description/body.
    """
    check_auth()
    try:
        validate_repo_format(repo_name)
    except ValueError as e:
        return str(e)

    url = f"https://api.github.com/repos/{repo_name}/issues"
    data = {"title": title, "body": body}
    
    try:
        resp = await http_client.post(url, json=data)
        resp.raise_for_status()
        issue = resp.json()
        return f"✅ Issue created successfully: {issue['html_url']}"
    except httpx.HTTPStatusError as e:
        return f"Failed to create issue: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Error creating issue: {str(e)}"

if __name__ == "__main__":
    mcp.run()

