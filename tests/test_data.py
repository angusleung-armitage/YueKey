import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_generated_mappings_and_prediction_integrity():
    data = ROOT / "build/data"
    if not (data / "quick_hk.dict.yaml").exists():
        pytest.skip("run make data")
    mappings = []
    characters = set()
    for line in (data / "quick_hk.dict.yaml").read_text().splitlines():
        if "\t" not in line:
            continue
        char, code, weight = line.split("\t")
        assert len(char) == 1
        assert 1 <= len(code) <= 2 and all("a" <= c <= "z" for c in code)
        assert int(weight) >= 1
        mappings.append((char, code))
        characters.add(char)
    assert len(mappings) == len(set(mappings))
    assert len(characters) > 29000
    assert ("𨋢", "jt") in mappings
    for char, code in [("，", "zb"), ("、", "zc"), ("。", "zd"), ("？", "zi"),
                       ("！", "zj"), ("「", "zd"), ("」", "ze"), ("…", "zl"),
                       ("‧", "zf"), ("︰", "zk"), ("﹖", "zt"), ("﹗", "zu"),
                       ("╴", "zb"), ("﹁", "zf"), ("︱", "zx"), ("﹑", "zo")]:
        assert (char, code) in mappings
    symbols = [(char, code) for char, code in mappings if code.startswith('z')]
    assert len(symbols) == 75
    assert len({code for _, code in symbols}) == 25
    assert ("﹏", "zb") not in symbols  # ZXBB is U+2574, not the wavy low line.
    assert ("ⅰ", "zb") not in mappings  # Different upstream Z-category convention.
    for line in (data / "quick_hk.predict.tsv").read_text().splitlines():
        prefix, suffix, weight = line.split("\t")
        assert prefix and suffix
        assert int(weight) >= 1
        assert all(char in characters for char in prefix + suffix)


def test_generation_is_reproducible():
    output = ROOT / "build/data/quick_hk.dict.yaml"
    if not output.exists():
        pytest.skip("run make data")
    import subprocess
    before = hashlib.sha256(output.read_bytes()).hexdigest()
    subprocess.run(["python3", str(ROOT / "tools/build_data.py")], check=True, capture_output=True)
    assert hashlib.sha256(output.read_bytes()).hexdigest() == before
