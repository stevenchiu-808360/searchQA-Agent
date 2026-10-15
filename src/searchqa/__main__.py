"""
searchqa CLI entry point.

Usage: python -m searchqa <command> [--env dev|stage|prod] [--pretty] ...
"""
import argparse
import json
import sys

from searchqa.client import ESClientError, ReadOnlyESClient
from searchqa.commands.analyze import AnalyzeCommand
from searchqa.commands.base import BaseCommand
from searchqa.commands.index import DocCommand, MappingCommand, SettingsCommand
from searchqa.commands.ltr import LtrCommand
from searchqa.commands.repo import RepoSyncCommand
from searchqa.commands.template import RenderCommand, ScriptCommand, SearchCommand
from searchqa.config import DEFAULT_ENV, ConfigLoader, Environment

COMMANDS: tuple[BaseCommand, ...] = (
    RepoSyncCommand(),
    AnalyzeCommand(),
    RenderCommand(),
    SearchCommand(),
    ScriptCommand(),
    DocCommand(),
    MappingCommand(),
    SettingsCommand(),
    LtrCommand(),
)


class CLI:
    """Builds the argument parser and dispatches to commands."""

    def __init__(self, commands: tuple[BaseCommand, ...] = COMMANDS):
        self.commands = {command.name: command for command in commands}
        self.parser = self._build_parser()

    def run(self, argv: list[str] | None = None) -> int:
        """
        Parse arguments, run the command and print JSON.

        Args:
            argv: CLI arguments (defaults to sys.argv[1:]).

        Returns:
            Process exit code.
        """
        args = self.parser.parse_args(argv)
        command = self.commands[args.command]
        try:
            if command.needs_es:
                config = ConfigLoader().es_config(Environment.from_string(args.env))
                with ReadOnlyESClient(config) as client:
                    result = command.run(args, client)
            else:
                result = command.run(args, None)
        except (ESClientError, ValueError, RuntimeError) as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
            return 1

        print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
        return 0

    def _build_parser(self) -> argparse.ArgumentParser:
        common = argparse.ArgumentParser(add_help=False)
        common.add_argument("--env", default=DEFAULT_ENV.value,
                            choices=[e.value for e in Environment],
                            help=f"Target environment (default: {DEFAULT_ENV.value})")
        common.add_argument("--pretty", action="store_true", help="Indent JSON output")

        parser = argparse.ArgumentParser(prog="searchqa",
                                         description="Read-only Elasticsearch diagnostics")
        subparsers = parser.add_subparsers(dest="command", required=True)
        for command in self.commands.values():
            subparser = subparsers.add_parser(command.name, help=command.help, parents=[common])
            command.add_arguments(subparser)
        return parser


def main() -> None:
    sys.exit(CLI().run())


if __name__ == "__main__":
    main()
