from __future__ import annotations

from dataclasses import dataclass

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "powershell": ["powershell", "ps1", "cmdlet", "executionpolicy", "backtick", "windows shell"],
    "python-environment": ["python", "venv", "virtualenv", "typer", "sqlalchemy", "pymysql", "import", "interpreter"],
    "memory-backend": ["mariadb", "sqlite", "fallback", "backend", "open_context", "context api"],
    "validation": ["pytest", "test", "tests", "lint", "check", "hook", "build", "compile"],
    "database": ["sql", "schema", "migration", "foreign key", "index", "alter table"],
    "git-workflow": ["git", "branch", "merge", "commit", "tag", "release"],
    "npm-publishing": ["npm", "package", "publish", "version", "registry"],
    "openlag-cli": ["openlag", "cli", "command", "export", "check", "lint"],
    "documentation": ["readme", "api.md", "specification", "documentation", "docs"],
    "agent-policy": ["agent", "policy", "memory rule", "orchestrator", "context-manager"],
    "security": ["secret", "token", "password", ".env", "sanitize", "redact"],
    "shell-compatibility": ["bash", "wsl", "cmd", "shell", "quoting"],
}


@dataclass(frozen=True)
class CategorySuggestion:
    key_name: str
    score: int
    reason: str


def suggest_categories(text: str, limit: int = 5) -> list[CategorySuggestion]:
    source = text.lower()
    scored: list[CategorySuggestion] = []
    for key_name, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in source:
                score += 2 if f" {keyword} " in f" {source} " else 1
        if score > 0:
            scored.append(CategorySuggestion(key_name=key_name, score=score, reason=f"matched keywords for {key_name}"))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]
