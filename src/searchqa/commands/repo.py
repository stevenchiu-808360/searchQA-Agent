"""
Local clone management for the bigdata_elasticsearch repo.
"""

import argparse
import subprocess
from typing import Any

from searchqa.client import ReadOnlyESClient
from searchqa.commands.base import BaseCommand
from searchqa.config import REPO_DIR, ConfigLoader

BRANCH = "main"
# Directories the agent must not read; excluded from the checkout entirely.
EXCLUDED_DIRS = ("plugins", "infra", "tools")


class RepoSyncCommand(BaseCommand):
    """Clone or update the bigdata_elasticsearch repo (sparse, branch main)."""

    name = "repo-sync"
    help = "Clone or pull bigdata_elasticsearch (main, excluding plugins/infra/tools)"
    needs_es = False

    def run(self, args: argparse.Namespace, client: ReadOnlyESClient | None) -> Any:
        if not (REPO_DIR / ".git").exists():
            REPO_DIR.parent.mkdir(parents=True, exist_ok=True)
            self._git(
                "clone",
                "--filter=blob:none",
                "--no-checkout",
                "--branch",
                BRANCH,
                ConfigLoader.repo_url(),
                str(REPO_DIR),
                cwd=None,
            )
            patterns = ["/*", *(f"!/{d}/" for d in EXCLUDED_DIRS)]
            self._git("sparse-checkout", "set", "--no-cone", *patterns)
            self._git("checkout", BRANCH)
            action = "cloned"
        else:
            self._git("pull", "--ff-only", "origin", BRANCH)
            action = "pulled"

        commit = self._git("log", "-1", "--format=%h %cs %s")
        return {"action": action, "path": str(REPO_DIR), "branch": BRANCH, "head": commit}

    @staticmethod
    def _git(*git_args: str, cwd: object = REPO_DIR) -> str:
        result = subprocess.run(["git", *git_args], cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"git {git_args[0]} failed: {result.stderr.strip()}")
        return result.stdout.strip()
