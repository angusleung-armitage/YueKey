"""Lossless validation before patching Rime configuration. SPDX-License-Identifier: MIT."""
from pathlib import Path

import yaml


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


def merge_schema_list(raw: bytes | None, path: Path) -> bytes:
    """Add our schema without replacing a user's list or unrelated patches."""
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
    key = schema_keys[0] if schema_keys else "schema_list/+"
    entries = patch.setdefault(key, [])
    if not isinstance(entries, list) or any(
        not isinstance(entry, dict) or not isinstance(entry.get("schema"), str)
        for entry in entries
    ):
        raise DeploymentError(f"{path}: {key} must be a list of schema mappings")
    if any(entry["schema"] == "quick_hk" for entry in entries):
        return raw if raw is not None else _dump_yaml(document)
    entries.append({"schema": "quick_hk"})
    return _dump_yaml(document)


