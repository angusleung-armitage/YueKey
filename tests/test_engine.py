"""Acceptance tests against librime and the compiled prediction plugin."""
import json
import os
from pathlib import Path
import select
import shutil
import statistics
import subprocess
import time

import pytest
import yaml

from quick_hk.rime_config import configure_schema_list

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "build/native"
DATA = ROOT / "build/data"
SHARED = Path(os.environ.get("QUICK_HK_RIME_SHARED_DIR", "/usr/share/rime-data"))


@pytest.fixture(scope="session")
def seed(tmp_path_factory):
    if not (NATIVE / "quick-hk-probe").exists() or not SHARED.exists():
        pytest.skip("Real engine tests require make native and Ubuntu librime (Dockerfile.dev)")
    assert (DATA / "quick_hk.predict.db").exists(), "Build the prediction database first"
    path = tmp_path_factory.mktemp("rime-seed")
    shutil.copytree(DATA, path, dirs_exist_ok=True)
    config = path / "default.custom.yaml"
    config.write_bytes(configure_schema_list(None, config))
    subprocess.run([str(NATIVE / "quick-hk-deployer"), "--build", str(path), str(SHARED), str(path / "build")],
                   check=True, capture_output=True, text=True)
    return path


class Probe:
    def __init__(self, directory):
        self.log = (directory / "probe-stderr.log").open("w+")
        self.process = subprocess.Popen(
            [str(NATIVE / "quick-hk-probe"), str(directory), str(SHARED), str(NATIVE / "librime-quick-hk-predict.so")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, bufsize=1)

    def send(self, command):
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        if not select.select([self.process.stdout], [], [], 10)[0]:
            self.log.flush(); self.log.seek(0)
            raise AssertionError(f"Probe timed out: {self.log.read()}")
        line = self.process.stdout.readline()
        if not line:
            self.log.flush(); self.log.seek(0)
            raise AssertionError(f"Probe exited: {self.log.read()}")
        return json.loads(line)

    def key(self, code, modifiers=0):
        return self.send(f"key {ord(code) if isinstance(code, str) else code} {modifiers}")

    def type(self, code):
        result = None
        for letter in code:
            result = self.key(letter)
        return result

    def close(self):
        if self.process.poll() is None:
            self.process.communicate("quit\n", timeout=10)
        self.log.close()


@pytest.fixture
def user_dir(seed, tmp_path):
    shutil.copytree(seed, tmp_path, dirs_exist_ok=True)
    return tmp_path


@pytest.fixture
def probe(user_dir):
    instance = Probe(user_dir)
    instance.send("option prediction 0")
    yield instance
    instance.close()


@pytest.mark.parametrize("previous", [None, "luna_pinyin", "cangjie5"])
def test_quick_is_the_only_schema_and_starts_without_selection(user_dir, previous):
    default = yaml.safe_load((user_dir / "build/default.yaml").read_text())
    assert default["schema_list"] == [{"schema": "quick_hk"}]
    if previous:
        (user_dir / "user.yaml").write_text(yaml.safe_dump({
            "var": {"previously_selected_schema": previous},
        }))
    instance = Probe(user_dir)
    try:
        assert instance.send("snapshot")["schema_id"] == "quick_hk"
        assert instance.type("hi1")["commit"] == "我"
        assert instance.type("zb1")["commit"] == "，"
        assert instance.send("new")["schema_id"] == "quick_hk"
    finally:
        instance.close()


def test_radicals_and_single_code(probe):
    result = probe.type("a")
    assert "日" in result["preedit"]
    assert "日" in result["candidates"]
    assert probe.key(" ")["commit"]


@pytest.mark.parametrize("char,code", [("蘋", "tc"), ("果", "wd"), ("公", "ci"), ("司", "sr"),
                                          ("嘅", "ru"), ("喺", "rf"), ("唔", "rr"), ("冇", "kb"),
                                          ("咗", "rm"), ("啲", "ri"), ("嚟", "re"), ("㗎", "rd"), ("𨋢", "jt")])
def test_required_characters_reachable(probe, char, code):
    result = probe.type(code)
    assert result["input"] == code
    for _ in range(100):
        if char in result["candidates"]:
            index = result["candidates"].index(char)
            assert probe.key(str(index + 1))["commit"] == char
            return
        previous = result["page"]
        result = probe.key("]")
        if result["page"] == previous:
            break
    pytest.fail(f"{char} not reachable for {code}")


def test_third_letter_commits_selection_and_starts_next_code(probe):
    first = probe.type("of")["candidates"][0]
    result = probe.key("v")
    assert result["commit"] == first
    assert result["input"] == "v"


def test_paging_arrows_selection_and_editing(probe):
    initial = probe.type("ru")
    assert len(initial["candidates"]) == 9
    assert probe.key("]")["page"] == 1
    assert probe.key("[")["page"] == 0
    assert probe.key(0xff53)["selected"] == 1  # Right
    assert probe.key(" ")["commit"] == initial["candidates"][1]
    probe.type("of")
    assert probe.key(0xff08)["input"] == "o"
    assert probe.key(0xff1b)["input"] == ""


def test_shortcuts_and_ascii_mode(probe):
    assert not probe.key("c", 4)["handled"]  # Control+C
    probe.send("option ascii_mode 1")
    assert not probe.key("a")["handled"]
    probe.send("option ascii_mode 0")
    assert probe.key(",")["commit"] == "，"
    probe.send("option ascii_punct 1")
    assert not probe.key(",")["handled"]


def test_invalid_code_kept_editable(probe):
    codes = set()
    for line in (DATA / "quick_hk.dict.yaml").read_text().splitlines():
        if "\t" in line:
            codes.add(line.split("\t")[1])
    invalid = next(a+b for a in "abcdefghijklmnopqrstuvwxy" for b in "abcdefghijklmnopqrstuvwxy" if a+b not in codes)
    result = probe.type(invalid)
    assert result["input"] == invalid
    assert probe.key(" ")["commit"] == ""
    assert probe.key("a")["input"] == invalid
    assert probe.key(0xff08)["input"] == invalid[0]


@pytest.mark.parametrize("code,char", [("zb", "，"), ("zc", "、"), ("zd", "。"),
                                     ("zg", "；"), ("zh", "："), ("zi", "？"),
                                     ("zj", "！"), ("zl", "…"), ("zy", "—")])
def test_punctuation_codes(probe, code, char):
    result = probe.type(code)
    assert result["input"] == code
    assert "符" in result["preedit"]
    assert result["candidates"][0] == char
    assert probe.key("1")["commit"] == char


def test_z_continuation_and_prediction_dismissal(probe):
    probe.send("option prediction 1")
    first = probe.type("hi")["candidates"][0]
    result = probe.key("z")
    assert result["commit"] == first and result["input"] == "z"
    assert probe.key("b")["candidates"][0] == "，"
    assert probe.key("1")["commit"] == "，"
    probe.send("clear")
    candidates = probe.type("of")["candidates"]
    result = probe.key(str(candidates.index("你") + 1))
    assert result["candidates"]  # A related-word menu is open.
    result = probe.key("z")
    assert result["commit"] == "" and result["input"] == "z"
    probe.key("b")
    assert probe.key(" ")["commit"] == "，"
    probe.type("zb")
    result = probe.key("h")
    assert result["commit"] == "，" and result["input"] == "h"
    probe.key("i")
    assert probe.key("1")["commit"] == "我"


def test_space_to_open_candidates(user_dir):
    (user_dir / "quick_hk.custom.yaml").write_text("patch:\n  quick_hk/show_candidates: false\n")
    subprocess.run([str(NATIVE / "quick-hk-deployer"), "--build", str(user_dir), str(SHARED), str(user_dir / "build")], check=True, capture_output=True)
    instance = Probe(user_dir)
    try:
        instance.send("option prediction 0")
        assert not instance.type("of")["candidates"]
        shown = instance.key(" ")
        assert not shown["commit"] and shown["candidates"]
        assert instance.key(" ")["commit"] == shown["candidates"][0]
    finally:
        instance.close()


def test_predictions_are_suffixes_and_sessions_are_isolated(probe):
    probe.send("option prediction 1")
    result = probe.type("of")
    index = result["candidates"].index("你")
    predicted = probe.key(str(index + 1))
    assert predicted["commit"] == "你"
    assert "好" in predicted["candidates"]
    assert predicted["preview"] == predicted["candidates"][0]
    assert predicted["input"] == "", "A continuation is a preview, not a typed code"
    first_predictions = predicted["candidates"]
    probe.send("new")
    second = probe.type("vd")
    second = probe.key(str(second["candidates"].index("好") + 1))
    assert second["commit"] == "好"
    assert probe.send("use 0")["candidates"] == first_predictions
    result = probe.key(str(first_predictions.index("好") + 1))
    assert result["commit"] == "好", "Prediction must not duplicate 你"


def test_typing_dismisses_prediction(probe):
    probe.send("option prediction 1")
    result = probe.type("of")
    probe.key(str(result["candidates"].index("你") + 1))
    result = probe.key("v")
    assert result["commit"] == "" and result["input"] == "v"


@pytest.mark.parametrize("cancel", ["clear", "key 65307 0", "key 65288 0"])
def test_cancel_does_not_recreate_predictions(probe, cancel):
    probe.send("option prediction 1")
    result = probe.type("of")
    predicted = probe.key(str(result["candidates"].index("你") + 1))
    assert predicted["candidates"]
    cleared = probe.send(cancel)
    assert not cleared["input"] and not cleared["candidates"]
    assert not cleared["preview"] and not cleared["commit"]
    assert not probe.send("clear")["candidates"]


@pytest.mark.parametrize("code,modifiers", [(0xff1b, 1 << 30), (0xff08, 4)])
def test_predictions_preserve_shortcuts_and_key_releases(probe, code, modifiers):
    probe.send("option prediction 1")
    result = probe.type("of")
    predicted = probe.key(str(result["candidates"].index("你") + 1))
    result = probe.key(code, modifiers)
    assert not result["handled"]
    assert result["candidates"] == predicted["candidates"]


def test_learning_persists(user_dir):
    instance = Probe(user_dir)
    try:
        instance.send("option prediction 0")
        original = instance.type("ru")["candidates"]
        chosen = original[5]
        assert instance.key("6")["commit"] == chosen
    finally:
        instance.close()
    instance = Probe(user_dir)
    try:
        instance.send("option prediction 0")
        new = instance.type("ru")["candidates"]
        assert new.index(chosen) < original.index(chosen)
    finally:
        instance.close()


def test_warm_generation_latency(probe):
    timings = []
    for _ in range(100):
        probe.send("clear")
        start = time.perf_counter()
        probe.type("ru")
        timings.append((time.perf_counter() - start) * 1000)
    p95 = statistics.quantiles(timings, n=100)[94]
    assert p95 < 20, f"Warm two-key roundtrip p95 {p95:.2f} ms"
