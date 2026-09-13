"""Validated, human-readable per-user preferences."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path


class SettingsError(ValueError):
    """A settings file or value cannot be used."""


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def settings_path() -> Path:
    override = os.environ.get("QUICK_HK_CONFIG")
    if override:
        return Path(override).expanduser()
    if sys.platform == 'win32':
        return Path(os.environ['LOCALAPPDATA']) / 'YueKey/settings.toml'
    return config_home() / "quick-hk/settings.toml"


@dataclass(frozen=True)
class Settings:
    horizontal: bool = True
    page_size: int = 9
    font_size: int = 18
    learning: bool = True
    prediction: bool = True
    show_candidates: bool = True
    ascii_punctuation: bool = False
    theme: str = "light"
    switch_key: str = "Shift_L"
    dictation_enabled: bool = False
    dictation_key: str = "Control_L"
    dictation_microphone: str = "default"
    dictation_punctuation: bool = True

    def __post_init__(self) -> None:
        for name in (
            "horizontal", "learning", "prediction", "show_candidates", "ascii_punctuation",
            "dictation_enabled", "dictation_punctuation"
        ):
            if type(getattr(self, name)) is not bool:
                raise SettingsError(f"{name} must be true or false")
        for name, minimum, maximum in (("page_size", 1, 9), ("font_size", 10, 36)):
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise SettingsError(f"{name} must be an integer from {minimum} to {maximum}")
        if self.theme not in ("light", "dark"):
            raise SettingsError("theme must be 'light' or 'dark'")
        if self.switch_key not in ("Shift_L", "Shift_R", "Control_L", "none"):
            raise SettingsError("switch_key must be Shift_L, Shift_R, Control_L, or none")
        if self.dictation_key not in ("Control_L", "Control_R"):
            raise SettingsError("dictation_key must be Control_L or Control_R")
        if not isinstance(self.dictation_microphone, str) or not self.dictation_microphone or len(self.dictation_microphone) > 512 or any(ord(c) < 32 for c in self.dictation_microphone):
            raise SettingsError("dictation_microphone must be a microphone name or default")

    @property
    def effective_dictation_key(self) -> str:
        return "Control_R" if self.dictation_key == self.switch_key else self.dictation_key


def load_settings(path: Path | None = None) -> Settings:
    path = Path(path) if path is not None else settings_path()
    try:
        with path.open("rb") as stream:
            values = tomllib.load(stream)
    except FileNotFoundError:
        return Settings()
    except tomllib.TOMLDecodeError as error:
        raise SettingsError(f"Invalid TOML in {path}: {error}") from error
    unknown = values.keys() - {field.name for field in fields(Settings)}
    if unknown:
        raise SettingsError(f"Unknown setting(s) in {path}: {', '.join(sorted(unknown))}")
    return Settings(**values)


def settings_text(settings: Settings) -> str:
    lines = ["# 粵鍵 YueKey settings. Run quick-hk deploy after editing."]
    for key, value in asdict(settings).items():
        lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def save_settings(settings: Settings, path: Path | None = None) -> None:
    # Validate even if a caller has constructed an instance unconventionally.
    settings.__post_init__()
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise SettingsError(f"Refusing to replace a symlink: {path}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(settings_text(settings))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
