#!/usr/bin/env python3
"""Prepare a Weasel-compatible schema from the verified shared dictionary."""
from pathlib import Path
from collections import defaultdict
import shutil
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from quick_hk.rime_config import schema_custom
from quick_hk.settings import Settings


def prepare():
    target = ROOT / 'build/windows-data'
    target.mkdir(parents=True, exist_ok=True)
    schema = yaml.safe_load((ROOT / 'rime/quick_hk.schema.yaml').read_text(encoding='utf-8'))
    # Ubuntu's native modules use a different ABI. Never install them in Weasel.
    processors = schema['engine']['processors']
    processors[processors.index('quick_hk_predictor')] = 'lua_processor@*yuekey_predict'
    schema['engine']['translators'].remove('quick_hk_predict_translator')
    schema.pop('predictor')
    schema['schema']['description'] = '粵鍵 YueKey · 香港用字、速成首尾碼、個人詞頻及關聯字'
    # Windows has its own optional per-schema customization, isolated from Ubuntu.
    schema['__patch'] = ['quick_hk.windows.custom:/patch?']
    (target / 'quick_hk.schema.yaml').write_text(
        yaml.safe_dump(schema, allow_unicode=True, sort_keys=False), encoding='utf-8')
    (target / 'quick_hk.windows.custom.yaml').write_bytes(schema_custom(Settings(), 'windows'))
    shutil.copyfile(ROOT / 'build/data/quick_hk.dict.yaml', target / 'quick_hk.dict.yaml')
    (target / 'lua').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'rime/lua/quick_hk.lua', target / 'lua/quick_hk.lua')
    shutil.copyfile(ROOT / 'rime/lua/yuekey_predict.lua', target / 'lua/yuekey_predict.lua')
    shards = defaultdict(list)
    for line in (ROOT / 'build/data/quick_hk.predict.tsv').read_text(encoding='utf-8').splitlines(keepends=True):
        shards[f'{ord(line[0]) // 256:x}'].append(line)
    directory = target / 'yuekey-predict'
    shutil.rmtree(directory, ignore_errors=True)
    directory.mkdir()
    for name, lines in shards.items():
        (directory / f'{name}.tsv').write_text(''.join(lines), encoding='utf-8')
    print(target)


if __name__ == '__main__':
    prepare()
