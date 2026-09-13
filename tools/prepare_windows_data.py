#!/usr/bin/env python3
"""Prepare a Weasel-compatible schema from the verified shared dictionary."""
from pathlib import Path
import shutil
import yaml

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    target = ROOT / 'build/windows-data'
    target.mkdir(parents=True, exist_ok=True)
    schema = yaml.safe_load((ROOT / 'rime/quick_hk.schema.yaml').read_text(encoding='utf-8'))
    # Ubuntu's native modules use a different ABI. Never install them in Weasel.
    schema['engine']['processors'].remove('quick_hk_predictor')
    schema['engine']['translators'].remove('quick_hk_predict_translator')
    schema['switches'] = [s for s in schema['switches'] if s['name'] != 'prediction']
    schema.pop('predictor')
    schema['schema']['description'] = '粵鍵 YueKey · 香港用字、速成首尾碼、個人詞頻'
    # Windows has its own optional per-schema customization, isolated from Ubuntu.
    schema['__patch'] = ['quick_hk.windows.custom:/patch?']
    (target / 'quick_hk.schema.yaml').write_text(
        yaml.safe_dump(schema, allow_unicode=True, sort_keys=False), encoding='utf-8')
    shutil.copyfile(ROOT / 'build/data/quick_hk.dict.yaml', target / 'quick_hk.dict.yaml')
    (target / 'lua').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'rime/lua/quick_hk.lua', target / 'lua/quick_hk.lua')
    print(target)


if __name__ == '__main__':
    prepare()
