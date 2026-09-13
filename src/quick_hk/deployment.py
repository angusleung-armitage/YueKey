"""Stage, compile, and reversibly deploy 港式速成 without restarting input daemons."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .rime_config import DeploymentError, _yaml, _dump_yaml, configure_schema_list

from .settings import Settings, config_home, load_settings

FRONTENDS = ("ibus", "fcitx5")
REQUIRED_DATA = ("quick_hk.schema.yaml", "quick_hk.dict.yaml", "quick_hk.predict.db", "lua/quick_hk.lua")
EXTENSION_UUID = "quick-hk@quick-hk.local"
DICTATION_EXTENSION_UUID = "quick-hk-dictation@quick-hk.local"


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))


def state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "quick-hk"


def frontend_directory(frontend: str) -> Path:
    if frontend == "ibus":
        # ibus-rime currently hardcodes HOME rather than g_get_user_config_dir().
        return Path.home() / ".config/ibus/rime"
    if frontend == "fcitx5":
        return data_home() / "fcitx5/rime"
    raise DeploymentError(f"Unknown frontend: {frontend}")


def resolve_frontends(frontend: str = "auto") -> list[str]:
    if frontend == "both":
        return list(FRONTENDS)
    if frontend in FRONTENDS:
        return [frontend]
    if frontend != "auto":
        raise DeploymentError(f"Unknown frontend: {frontend}")
    configured = [name for name in FRONTENDS if (state_home() / f"{name}.json").exists()]
    if configured:
        return configured
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    return ["fcitx5" if any(name in desktop for name in ("kde", "plasma")) else "ibus"]


def payload_directory() -> Path:
    override = os.environ.get("QUICK_HK_DATA_DIR")
    if override:
        return Path(override).expanduser()
    checkout = Path(__file__).resolve().parents[2] / "build/data"
    return checkout if checkout.is_dir() else Path("/usr/share/quick-hk/rime")


def desktop_directory() -> Path:
    override = os.environ.get("QUICK_HK_DESKTOP_DIR")
    if override:
        return Path(override).expanduser()
    checkout = Path(__file__).resolve().parents[2] / "desktop"
    return checkout if checkout.is_dir() else Path("/usr/share/quick-hk/desktop")


def _read(path: Path) -> bytes | None:
    if path.is_symlink():
        raise DeploymentError(f"Refusing to replace a symlink: {path}")
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def _schema_custom(settings: Settings, frontend: str = "ibus") -> bytes:
    from .rime_config import schema_custom
    return schema_custom(settings, frontend)


def _merge_yaml_patch(path: Path, updates: dict) -> bytes:
    document = _yaml(_read(path) or b"", path)
    patch = document.setdefault("patch", {})
    if not isinstance(patch, dict):
        raise DeploymentError(f"{path}: patch must be a mapping")
    patch.update(updates)
    return _dump_yaml(document)


def _deployer_command() -> list[str]:
    override = os.environ.get("QUICK_HK_DEPLOYER")
    if override:
        command = shlex.split(override)
        if not command:
            raise DeploymentError("QUICK_HK_DEPLOYER must not be empty")
        return command
    for name in ("quick-hk-deployer", "rime_deployer"):
        command = shutil.which(name)
        if command:
            return [command]
    raise DeploymentError("Rime deployer missing. Install yuekey (or librime-bin).")


def _compile(stage: Path) -> None:
    shared = Path(os.environ.get("QUICK_HK_RIME_SHARED_DIR", "/usr/share/rime-data"))
    if not (shared / "default.yaml").is_file():
        raise DeploymentError(f"Shared Rime data missing: {shared}/default.yaml (install rime-data)")
    command = _deployer_command() + ["--build", str(stage), str(shared), str(stage / "build")]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DeploymentError(f"Rime compilation could not finish: {error}") from error
    if result.returncode:
        details = (result.stderr + "\n" + result.stdout).strip()[-6000:]
        raise DeploymentError(f"Rime compilation failed; live files were not changed.\n{details}")
    for name in ("quick_hk.schema.yaml", "quick_hk.table.bin"):
        if not (stage / "build" / name).is_file():
            raise DeploymentError(f"Rime compilation did not produce build/{name}; live files were not changed")


def _copy_config_to_stage(source: Path, stage: Path) -> None:
    if not source.exists():
        return
    # User dictionaries are runtime databases; never copy or open their live files.
    for path in source.glob("*.yaml"):
        if path.is_file() and not path.name.startswith(("user.", "installation.")):
            shutil.copyfile(path, stage / path.name)
    for name in ("lua", "opencc"):
        directory = source / name
        if directory.is_dir():
            shutil.copytree(directory, stage / name, dirs_exist_ok=True)


def _managed_assets(frontend: str, settings: Settings) -> dict[Path, bytes]:
    assets = desktop_directory()
    changes: dict[Path, bytes] = {}
    icons = assets / "icons/hicolor"
    if icons.is_dir():
        for path in sorted(icons.rglob("*.png")):
            changes[data_home() / "icons/hicolor" / path.relative_to(icons)] = path.read_bytes()
    if frontend == "ibus":
        # GNOME finds engine preferences by this desktop ID, not the Rime XML.
        launcher = assets / "gnome/ibus-setup-rime.desktop"
        if launcher.is_file():
            changes[data_home() / "applications" / launcher.name] = launcher.read_bytes()
        source = assets / "gnome" / EXTENSION_UUID
        if source.is_dir():
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    changes[data_home() / "gnome-shell/extensions" / EXTENSION_UUID / path.relative_to(source)] = path.read_bytes()
        changes[config_home() / "quick-hk/presentation.json"] = (
            json.dumps({"theme": settings.theme, "font_size": settings.font_size,
                        "dictation_enabled": settings.dictation_enabled}, indent=2) + "\n"
        ).encode()
        # IBus Rime recognizes horizontal mode here; GNOME owns the font rendering.
        changes[frontend_directory(frontend) / "ibus_rime.custom.yaml"] = _merge_yaml_patch(
            frontend_directory(frontend) / "ibus_rime.custom.yaml", {"style/horizontal": settings.horizontal}
        )
    else:
        for theme in ("light", "dark"):
            source = assets / "fcitx5" / f"quick-hk-{theme}"
            if source.is_dir():
                for path in sorted(source.rglob("*")):
                    if path.is_file():
                        changes[data_home() / "fcitx5/themes" / source.name / path.relative_to(source)] = path.read_bytes()
        classicui = config_home() / "fcitx5/conf/classicui.conf"
        changes[classicui] = _merge_classicui(_read(classicui), settings)
    speech = assets / "dictation"
    if speech.is_dir():
        extension = speech / DICTATION_EXTENSION_UUID
        if frontend == "ibus" and extension.is_dir():
            for path in sorted(extension.rglob("*")):
                if path.is_file():
                    changes[data_home() / "gnome-shell/extensions" / DICTATION_EXTENSION_UUID / path.relative_to(extension)] = path.read_bytes()
        changes[data_home() / "dbus-1/services/org.quick_hk.Dictation.service"] = (
            speech / "org.quick_hk.Dictation.service").read_bytes()
        changes[config_home() / "autostart/quick-hk-dictation.desktop"] = (
            (speech / "quick-hk-dictation.desktop").read_text()
            + f"Hidden={'false' if settings.dictation_enabled else 'true'}\n"
            + f"X-GNOME-Autostart-enabled={'true' if settings.dictation_enabled else 'false'}\n"
        ).encode()
    return changes


def _merge_classicui(raw: bytes | None, settings: Settings) -> bytes:
    """Edit only root options, retaining comments, sections, and unrelated values."""
    try:
        text = (raw or b"").decode("utf-8")
    except UnicodeError as error:
        raise DeploymentError("Fcitx5 classicui.conf must be UTF-8") from error
    values = {
        "Theme": f"quick-hk-{settings.theme}",
        "Font": f"Noto Sans CJK HK {settings.font_size}",
        "UseDarkTheme": "False",
        "Vertical Candidate List": "False" if settings.horizontal else "True",
    }
    lines = text.splitlines(keepends=True)
    first_section = next((index for index, line in enumerate(lines) if line.lstrip().startswith("[")), len(lines))
    found = set()
    for index in range(first_section):
        match = re.match(r"\s*([^#;=\s][^=]*?)\s*=", lines[index])
        if match and match.group(1) in values:
            key = match.group(1)
            if key in found:
                raise DeploymentError(f"Duplicate Fcitx5 ClassicUI option: {key}")
            found.add(key)
            lines[index] = f"{key}={values[key]}\n"
    additions = [f"{key}={value}\n" for key, value in values.items() if key not in found]
    if first_section and not lines[first_section - 1].endswith("\n"):
        lines[first_section - 1] += "\n"
    lines[first_section:first_section] = additions
    return "".join(lines).encode("utf-8")


def _hash(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _atomic_write(path: Path, contents: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def _state_lock() -> Iterator[None]:
    directory = state_home()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "lock").open("a+b") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise DeploymentError("Another quick-hk operation is running") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _manifest(frontend: str) -> dict:
    path = state_home() / f"{frontend}.json"
    raw = _read(path)
    if raw is None:
        return {"version": 1, "frontend": frontend, "files": {}}
    try:
        value = json.loads(raw)
        if value["version"] != 1 or value["frontend"] != frontend or not isinstance(value["files"], dict):
            raise ValueError("unsupported manifest")
        return value
    except (KeyError, TypeError, ValueError) as error:
        raise DeploymentError(f"Invalid deployment manifest {path}: {error}") from error


def _commit(plans: dict[str, dict[Path, bytes]]) -> None:
    """Write all frontends as one transaction, keeping original files for uninstall."""
    replacements: dict[Path, bytes] = {}
    previous: dict[Path, tuple[bytes | None, int]] = {}
    backup_dir = state_home() / "backups" / uuid.uuid4().hex
    manifests = {name: copy.deepcopy(_manifest(name)) for name in ("ibus", "fcitx5")}
    for frontend, changes in plans.items():
        manifest = manifests[frontend]
        for path, contents in changes.items():
            current = _read(path)
            mode = stat.S_IMODE(path.stat().st_mode) if current is not None else 0o600
            record = manifest["files"].get(str(path))
            if record is None:
                record = next((other["files"][str(path)] for other in manifests.values()
                               if str(path) in other["files"]), None)
                if record is not None:
                    manifest["files"][str(path)] = record
            if path in replacements:
                if replacements[path] != contents:
                    raise DeploymentError(f"Conflicting shared frontend settings: {path}")
                continue
            generated = path.parent == frontend_directory(frontend) / "build"
            if record and not generated and current != contents and (
                current is None or _hash(current) != record["last_hash"]
            ):
                raise DeploymentError(
                    f"Managed file changed outside quick-hk: {path}. "
                    "Keep your edits, or restore the previous deployed version before retrying."
                )
            if record is None:
                backup = None
                if current is not None:
                    backup = backup_dir / f"{len(replacements):04d}-{path.name}"
                    _atomic_write(backup, current, mode)
                record = {"backup": str(backup) if backup else None, "mode": mode}
                manifest["files"][str(path)] = record
            # If a user edited a shared file, and it already needs no change, retain
            # the old hash so uninstall will leave their edited file untouched.
            if current != contents or "last_hash" not in record:
                record["last_hash"] = _hash(contents)
            previous[path] = (current, mode)
            replacements[path] = contents
            # Shared launchers have one original backup and one current hash.
            for other in manifests.values():
                if str(path) in other["files"]:
                    other["files"][str(path)] = record
    for frontend, manifest in manifests.items():
        if frontend not in plans and manifest == _manifest(frontend):
            continue
        manifest_path = state_home() / f"{frontend}.json"
        previous[manifest_path] = (_read(manifest_path), 0o600)
        replacements[manifest_path] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    written: list[Path] = []
    try:
        for path, contents in replacements.items():
            if previous[path][0] != contents:
                _atomic_write(path, contents, previous[path][1])
                written.append(path)
    except BaseException as error:
        failures = []
        for path in reversed(written):
            old, mode = previous[path]
            try:
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, old, mode)
            except OSError as rollback_error:
                failures.append(f"{path}: {rollback_error}")
        if failures:
            raise DeploymentError(
                f"Deployment failed ({error}); rollback needs attention: {'; '.join(failures)}. "
                f"Original backups remain in {state_home() / 'backups'}"
            ) from error
        raise DeploymentError(f"Deployment failed and was rolled back: {error}") from error


def deploy(frontend: str = "auto", settings: Settings | None = None) -> list[str]:
    settings = settings or load_settings()
    settings.__post_init__()
    source = payload_directory()
    missing = [name for name in REQUIRED_DATA if not (source / name).is_file()]
    if missing:
        raise DeploymentError(f"Incomplete Rime data in {source}: {', '.join(missing)}. Build or install yuekey first.")
    targets = resolve_frontends(frontend)
    if settings.dictation_enabled:
        from .dictation_setup import status as dictation_status
        if not dictation_status()["ready"]:
            raise DeploymentError("Run quick-hk dictation setup before enabling dictation.")
        if "ibus" in targets and not list(Path("/usr/lib").glob("*/rime-plugins/librime-quick-hk-dictation.so")):
            raise DeploymentError("Install yuekey before enabling dictation.")
        if "fcitx5" in targets and not list(Path("/usr/lib").glob("*/fcitx5/yuekey-dictation.so")):
            raise DeploymentError("Install yuekey before enabling dictation.")
    with _state_lock(), tempfile.TemporaryDirectory(prefix="quick-hk-deploy-") as temporary:
        plans = {}
        for name in targets:
            directory = frontend_directory(name)
            stage = Path(temporary) / name
            stage.mkdir()
            _copy_config_to_stage(directory, stage)
            changes = {directory / item: (source / item).read_bytes() for item in REQUIRED_DATA}
            changes[directory / "quick_hk.custom.yaml"] = _schema_custom(settings, name)
            changes[directory / "default.custom.yaml"] = configure_schema_list(
                _read(directory / "default.custom.yaml"), directory / "default.custom.yaml"
            )
            changes.update(_managed_assets(name, settings))
            for path, contents in changes.items():
                if path.is_relative_to(directory):
                    target = stage / path.relative_to(directory)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(contents)
            _compile(stage)
            for path in sorted((stage / "build").glob("quick_hk*")):
                if path.is_file():
                    changes[directory / "build" / path.name] = path.read_bytes()
            for filename in ("default.yaml", "ibus_rime.yaml"):
                compiled = stage / "build" / filename
                if compiled.is_file():
                    changes[directory / "build" / filename] = compiled.read_bytes()
            plans[name] = changes
        _commit(plans)
    return [f"Deployed 港式速成 for {name}: {frontend_directory(name)}" for name in targets] + activation_instructions(targets, settings)


def activation_instructions(frontends: list[str], settings: Settings | None = None) -> list[str]:
    messages = ["Input daemons were not restarted. Finish current composition, then reload Rime or sign out and back in."]
    if "ibus" in frontends:
        messages += [
            "GNOME: add Chinese (Rime) in Settings → Keyboard → Input Sources. Switch to Rime to type with 港式速成, the default and only scheme.",
            "Configure YueKey with quick-hk configure or Rime's Preferences in GNOME Settings.",
            f"GNOME 50 appearance: enable {EXTENSION_UUID} in Extensions after signing in again.",
        ]
        if settings and settings.dictation_enabled:
            messages.append(f"Dictation: sign out and back in after first installation, then enable {DICTATION_EXTENSION_UUID} in Extensions. Double Ctrl starts/stops recording.")
    if "fcitx5" in frontends:
        messages += [
            "KDE: open Fcitx 5 Configuration, add Rime; 港式速成 is the default and only scheme.",
            "For the supplied appearance, use Fcitx5 Classic User Interface and select a quick-hk theme; disable Kimpanel if it owns your candidate window.",
        ]
        if settings and settings.dictation_enabled:
            messages.append("KDE dictation: restart Fcitx5 after first installation, then run quick-hk dictation serve --frontend fcitx5. Double Ctrl starts/stops; Esc cancels.")
    return messages


def uninstall(frontend: str = "auto") -> list[str]:
    messages = []
    with _state_lock():
        plans = []
        targets = resolve_frontends(frontend)
        retained = {filename for name in ("ibus", "fcitx5") if name not in targets
                    for filename in _manifest(name)["files"]}
        handled = set()
        for name in targets:
            manifest = _manifest(name)
            changes = []
            for filename, record in list(manifest["files"].items()):
                if filename in retained or filename in handled:
                    del manifest["files"][filename]
                    continue
                path = Path(filename)
                if path.is_symlink():
                    messages.append(f"Preserved user symlink: {path}")
                    continue
                current = _read(path)
                if current is None or _hash(current) != record["last_hash"]:
                    messages.append(f"Preserved changed or missing file: {path}")
                    continue
                if record["backup"]:
                    backup = Path(record["backup"])
                    if not backup.is_file():
                        raise DeploymentError(f"Original backup missing: {backup}; leaving {path} untouched")
                    changes.append((path, backup.read_bytes(), record["mode"]))
                else:
                    changes.append((path, None, record["mode"]))
                del manifest["files"][filename]
                handled.add(filename)
            plans.append((name, manifest, changes))
        # Read all required backups, including the second frontend, before
        # deleting any live file. A damaged backup must leave typing usable.
        for name, manifest, changes in plans:
            for path, previous, mode in changes:
                if previous is None:
                    path.unlink()
                else:
                    _atomic_write(path, previous, mode)
            manifest_path = state_home() / f"{name}.json"
            if manifest["files"]:
                _atomic_write(manifest_path, (json.dumps(manifest, indent=2) + "\n").encode())
            else:
                manifest_path.unlink(missing_ok=True)
            messages.append(f"Removed unchanged managed files for {name}; learning databases and settings were preserved.")
    return messages + ["Reload Rime or sign out and back in to finish. Disable the GNOME extension if it was enabled."]


def _active_frontends() -> set[str]:
    result = set()
    uid = os.getuid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            command = (entry / "cmdline").read_bytes().split(b"\0", 1)[0].decode(errors="replace")
            name = Path(command).name
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if name in ("ibus-daemon", "ibus-engine-rime"):
            result.add("ibus")
        if name == "fcitx5":
            result.add("fcitx5")
    return result


def reset_learning(frontend: str = "auto") -> list[str]:
    targets = resolve_frontends(frontend)
    active = _active_frontends().intersection(targets)
    if active:
        raise DeploymentError(
            f"Stop {' and '.join(sorted(active))} before resetting learning, then rerun this command. "
            "Live learning databases are not safe to move or copy."
        )
    messages = []
    with _state_lock():
        backup_root = state_home() / "learning-backups" / uuid.uuid4().hex
        for name in targets:
            database = frontend_directory(name) / "quick_hk.userdb"
            if not database.exists():
                messages.append(f"No learned dictionary found for {name}.")
                continue
            if database.is_symlink() or not database.is_dir():
                raise DeploymentError(f"Expected a regular LevelDB directory: {database}")
            with (database / "LOCK").open("a+b") as stream:
                try:
                    fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise DeploymentError(f"Learning dictionary is locked: {database}. Stop its input frontend first.") from error
                destination = backup_root / name / database.name
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    database.rename(destination)
                except OSError as error:
                    raise DeploymentError(f"Could not atomically move learning database: {error}") from error
            messages.append(f"Reset learning for {name}; original database saved at {destination}.")
    return messages


def doctor(frontend: str = "auto") -> dict:
    targets = resolve_frontends(frontend)
    source = payload_directory()
    plugin_locations = list(Path("/usr/lib").glob("*/rime-plugins/librime-quick-hk-predict.so"))
    plugin_locations += list(Path("/usr/lib/rime-plugins").glob("librime-quick-hk-predict.so"))
    try:
        command = _deployer_command()
        deployer = bool(shutil.which(command[0]))
    except DeploymentError:
        command, deployer = [], False
    checks = {
        "deployer": {"ok": deployer, "detail": " ".join(command) or "Install yuekey"},
        "rime_data": {"ok": all((source / name).is_file() for name in REQUIRED_DATA), "detail": str(source)},
        "shared_data": {
            "ok": (Path(os.environ.get("QUICK_HK_RIME_SHARED_DIR", "/usr/share/rime-data")) / "default.yaml").is_file(),
            "detail": os.environ.get("QUICK_HK_RIME_SHARED_DIR", "/usr/share/rime-data"),
        },
        "prediction_plugin": {"ok": bool(plugin_locations), "detail": ", ".join(map(str, plugin_locations)) or "Install yuekey"},
    }
    settings = None
    try:
        settings = load_settings()
        checks["preferences"] = {"ok": True, "detail": "Settings are valid"}
        if settings.dictation_enabled:
            from .dictation_setup import status as dictation_status
            speech = dictation_status(verify=True)
            checks["dictation_models"] = {"ok": speech["ready"], "detail": speech["model"] + " — CPU only"}
            checks["dictation_microphone"] = {"ok": bool(shutil.which("pw-record")), "detail": settings.dictation_microphone}
            locations = [path for pattern in
                         (["*/rime-plugins/librime-quick-hk-dictation.so"] if "ibus" in targets else []) +
                         (["*/fcitx5/yuekey-dictation.so"] if "fcitx5" in targets else [])
                         for path in Path("/usr/lib").glob(pattern)]
            checks["dictation_bridge"] = {"ok": bool(locations), "detail": ", ".join(map(str, locations)) or "Install yuekey"}
    except (ValueError, OSError) as error:
        checks["preferences"] = {"ok": False, "detail": str(error)}
    status = {}
    for name in targets:
        directory = frontend_directory(name)
        executable = "ibus" if name == "ibus" else "fcitx5"
        registration = Path("/usr/share/ibus/component/rime.xml") if name == "ibus" else Path("/usr/share/fcitx5/inputmethod/rime.conf")
        checks[name] = {
            "ok": bool(shutil.which(executable)) and registration.is_file(),
            "detail": f"{registration}; install {name}-rime if absent",
        }
        status[name] = {
            "directory": str(directory),
            "managed": (state_home() / f"{name}.json").is_file(),
            "compiled": (directory / "build/quick_hk.schema.yaml").is_file(),
        }
    return {
        "ok": all(check["ok"] for check in checks.values()),
        "checks": checks,
        "frontends": status,
        "active_frontends": sorted(_active_frontends()),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "notes": activation_instructions(targets, settings),
    }
