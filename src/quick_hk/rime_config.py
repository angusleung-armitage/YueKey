"""Lossless validation before patching Rime configuration. SPDX-License-Identifier: MIT."""
from pathlib import Path

import yaml

from .settings import Settings


class DeploymentError(RuntimeError):
    """A deployment could not safely complete."""


class _UniqueLoader(yaml.SafeLoader):
    """Do not silently discard duplicate YAML keys in a user's configuration."""


def _unique_mapping(loader: _UniqueLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise DeploymentError("Rime configuration mapping keys must be strings")
        if key in result:
            raise DeploymentError(f"Duplicate YAML configuration key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def _yaml(raw: bytes, path: Path) -> dict:
    try:
        value = yaml.load(raw.decode("utf-8"), Loader=_UniqueLoader)
    except (yaml.YAMLError, UnicodeError) as error:
        raise DeploymentError(f"Cannot parse {path}: {error}") from error
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise DeploymentError(f"Expected a YAML mapping in {path}")
    return value


def _dump_yaml(value: dict) -> bytes:
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode("utf-8")


def configure_schema_list(raw: bytes | None, path: Path) -> bytes:
    """Make Quick the only selectable schema; deployment backs up the original."""
    document = _yaml(raw or b"", path)
    patch = document.setdefault("patch", {})
    if not isinstance(patch, dict):
        raise DeploymentError(f"{path}: patch must be a mapping")
    schema_keys = [key for key in patch if key == "schema_list" or key.startswith("schema_list/")]
    unsupported = set(schema_keys) - {"schema_list", "schema_list/+"}
    if unsupported or len(schema_keys) > 1:
        raise DeploymentError(
            f"{path}: ambiguous schema_list patches; combine them into one "
            "schema_list or schema_list/+ list before setup"
        )
    key = schema_keys[0] if schema_keys else "schema_list"
    entries = patch.get(key, [])
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) or not isinstance(entry.get("schema"), str)
        for entry in entries
    ):
        raise DeploymentError(f"{path}: {key} must be a list of schema mappings")
    if key == "schema_list" and entries == [{"schema": "quick_hk"}]:
        return raw if raw is not None else _dump_yaml(document)
    patch.pop("schema_list/+", None)
    patch["schema_list"] = [{"schema": "quick_hk"}]
    return _dump_yaml(document)



def schema_custom(settings: Settings, frontend: str = "ibus") -> bytes:
    patch = {
        "menu/page_size": settings.page_size,
        "translator/enable_user_dict": settings.learning,
        "translator/enable_sentence": False,
        "translator/enable_encoder": False,
        "quick_hk/learning": settings.learning,
        "quick_hk/show_candidates": settings.show_candidates,
        "quick_hk/switch_key": settings.switch_key,
        "quick_hk/dictation_enabled": settings.dictation_enabled and frontend == "ibus",
        "quick_hk/dictation_key": settings.effective_dictation_key,
        "ascii_composer/switch_key": {
            key: "commit_code" if key == settings.switch_key else "noop"
            for key in ("Shift_L", "Shift_R", "Control_L", "Control_R")
        },
        "switches/@1/reset": int(settings.prediction),
        "switches/@2/reset": int(settings.ascii_punctuation),
        "style/horizontal": settings.horizontal,
    }
    if settings.dictation_enabled and frontend == "ibus":
        patch["engine/processors/@before 0"] = "quick_hk_dictation"
    if frontend == "windows":
        colors = {"light": (0xFFFFFF, 0x242120, 0xD86607),
                  "dark": (0x302C29, 0xF7F5F5, 0xD86607)}
        for theme, (background, foreground, highlight) in colors.items():
            patch[f"preset_color_schemes/yuekey_{theme}"] = {
                "name": f"YueKey {theme}", "author": "YueKey contributors",
                "back_color": background, "border_color": background,
                "text_color": foreground, "candidate_text_color": foreground,
                "label_color": foreground, "comment_text_color": foreground,
                "hilited_text_color": 0xFFFFFF, "hilited_back_color": highlight,
                "hilited_candidate_text_color": 0xFFFFFF,
                "hilited_candidate_back_color": highlight,
                "hilited_label_color": 0xFFFFFF, "hilited_comment_text_color": 0xFFFFFF,
            }
        patch.update({"style/font_face": "Microsoft JhengHei",
                      "style/font_point": settings.font_size,
                      "style/label_font_point": settings.font_size,
                      "style/comment_font_point": settings.font_size,
                      "style/color_scheme": f"yuekey_{settings.theme}",
                      "style/color_scheme_dark": f"yuekey_{settings.theme}",
                      "style/inline_preedit": True,
                      # Predictions have empty composition text but a nonempty
                      # commit preview. Match IBus's default preview display.
                      "style/preedit_type": "preview",
                      # Weasel reads layout/type after the legacy horizontal
                      # flag, so keep both in agreement for this schema.
                      "style/layout/type": "horizontal" if settings.horizontal else "vertical",
                      "style/vertical_text": False,
                      "style/fullscreen": False,
                      "style/layout/corner_radius": 8})
    return _dump_yaml({"patch": patch})
