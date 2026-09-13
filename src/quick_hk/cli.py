"""Command-line entry point. No command silently restarts an input daemon."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from dataclasses import asdict, replace
from pathlib import Path

from . import __version__
from .deployment import deploy, doctor, reset_learning, uninstall
from .settings import SettingsError, load_settings, save_settings, settings_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quick-hk", description="粵鍵 YueKey — Cantonese Quick input and offline dictation")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    speech = subparsers.add_parser("dictation", help="Set up or inspect CPU-only Cantonese dictation")
    speech.add_argument("action", choices=("setup", "status", "serve"))
    speech.add_argument("--json", action="store_true")
    for name, help_text in (
        ("setup", "Stage, compile, and install per-user Rime configuration"),
        ("deploy", "Recompile and deploy current preferences"),
        ("configure", "Open settings, or edit preferences with --set"),
        ("doctor", "Check dependencies and deployment status"),
        ("uninstall", "Restore unchanged managed files; preserve user data"),
        ("reset-learning", "Back up and reset learning while input daemons are stopped"),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--frontend", choices=("auto", "ibus", "fcitx5", "both"), default="auto")
        command.add_argument("--config", type=Path, help="Use a specific settings.toml")
        command.add_argument("--home", type=Path, help="Use isolated HOME and XDG directories (testing)")
        if name == "doctor":
            command.add_argument("--json", action="store_true", help="Print machine-readable status")
        if name == "configure":
            command.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
            command.add_argument("--show", action="store_true", help="Print current preferences")
            command.add_argument("--no-deploy", action="store_true", help="Save preferences without applying them")
    return parser


def _configured_settings(settings, assignments: list[str]):
    changes = {}
    for assignment in assignments:
        key, separator, value = assignment.partition("=")
        if not separator or key not in asdict(settings):
            raise SettingsError(f"Expected a known setting as KEY=VALUE, got: {assignment}")
        if isinstance(getattr(settings, key), str):
            changes[key] = value.strip('"')
        else:
            try:
                changes[key] = tomllib.loads(f"value = {value}")["value"]
            except (tomllib.TOMLDecodeError, KeyError) as error:
                raise SettingsError(f"Invalid value for {key}: {value}") from error
    return replace(settings, **changes)


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "dictation":
        from . import dictation_setup
        try:
            if args.action == "setup":
                for message in dictation_setup.setup():
                    print(message)
                return 0
            if args.action == "serve":
                from .dictation_service import serve
                return serve()
            from .dictation_service import live_status
            status = dictation_setup.status(verify=True)
            status["service"] = live_status()
            if args.json:
                print(json.dumps(status, ensure_ascii=False, indent=2))
            else:
                print(f"{status['model']} — CPU only")
                print("Models: " + ("ready" if status["ready"] else "run quick-hk dictation setup"))
                print("Service: " + status["service"]["state"])
                if status["service"].get("desktop_ready") is False:
                    print("Desktop: sign out and back in, then enable YueKey Dictation in Extensions.")
                if status["service"].get("error"):
                    print(status["service"]["error"])
            return 0 if status["ready"] else 1
        except (RuntimeError, OSError, ValueError) as error:
            print(f"quick-hk: {error}", file=sys.stderr)
            return 1
    if args.command == "configure" and args.no_deploy and not args.set:
        parser.error("--no-deploy requires --set")
    if args.home:
        home = args.home.expanduser().absolute()
        os.environ.update({
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_STATE_HOME": str(home / ".local/state"),
        })
        if args.config is None:
            os.environ.pop("QUICK_HK_CONFIG", None)
    if args.config:
        os.environ["QUICK_HK_CONFIG"] = str(args.config)
    try:
        if args.command == "doctor":
            status = doctor(args.frontend)
            if args.json:
                print(json.dumps(status, indent=2, ensure_ascii=False))
            else:
                for name, check in status["checks"].items():
                    print(f"{'OK' if check['ok'] else 'MISSING'} {name}: {check['detail']}")
                for name, target in status["frontends"].items():
                    print(f"{name}: managed={target['managed']}, compiled={target['compiled']} ({target['directory']})")
            return 0 if status["ok"] else 1
        if args.command == "uninstall":
            messages = uninstall(args.frontend)
        elif args.command == "reset-learning":
            messages = reset_learning(args.frontend)
        elif args.command == "configure":
            if args.show:
                settings = load_settings(args.config)
                print(settings_text(settings), end="")
                return 0
            if not args.set:
                from .gui import run_gui

                return run_gui(config_path=args.config, frontend=args.frontend) or 0
            settings = load_settings(args.config)
            settings = _configured_settings(settings, args.set)
            messages = [] if args.no_deploy else deploy(args.frontend, settings)
            save_settings(settings, args.config)
            messages.append("Saved preferences." + (" Run quick-hk deploy to apply." if args.no_deploy else ""))
        else:
            settings = load_settings(args.config)
            messages = deploy(args.frontend, settings)
            if args.command == "setup":
                save_settings(settings, args.config)
        for message in messages:
            print(message)
        return 0
    except (RuntimeError, SettingsError, OSError, ImportError) as error:
        print(f"quick-hk: {error}", file=sys.stderr)
        return 1
