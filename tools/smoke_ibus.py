#!/usr/bin/python3
"""Exercise the installed IBus frontend on a disposable private D-Bus session."""
import os
from pathlib import Path
import subprocess
import time

import gi

gi.require_version("IBus", "1.0")
from gi.repository import GLib, IBus


def drain(seconds=0.1):
    deadline = time.monotonic() + seconds
    context = GLib.MainContext.default()
    while time.monotonic() < deadline:
        while context.pending():
            context.iteration(False)
        time.sleep(0.005)


def main():
    if not Path("/.dockerenv").exists() or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        raise SystemExit("Run only in a disposable Docker container with dbus-run-session")
    IBus.init()
    daemon = subprocess.Popen(["ibus-daemon", "--replace", "--xim", "--panel=disable", "--config=disable"])
    try:
        for _ in range(100):
            bus = IBus.Bus.new()
            if bus.is_connected():
                break
            drain(0.1)
        assert bus.is_connected(), "IBus daemon did not become available"
        assert bus.set_global_engine("rime"), "Could not activate Rime"
        context = bus.create_input_context("quick-hk-package-smoke")
        commits = []
        menus = []
        preedits = []
        context.connect("commit-text", lambda _, text: commits.append(text.get_text()))
        context.connect("update-preedit-text", lambda _, text, cursor, visible: preedits.append(text.get_text() if visible else ''))
        context.connect("hide-preedit-text", lambda _: preedits.append(''))
        context.connect("update-lookup-table", lambda _, table, visible: menus.append(
            [table.get_candidate(i).get_text() for i in range(table.get_number_of_candidates())] if visible else []))
        context.connect("hide-lookup-table", lambda _: menus.append([]))
        context.set_capabilities(int(IBus.Capabilite.PREEDIT_TEXT | IBus.Capabilite.LOOKUP_TABLE | IBus.Capabilite.FOCUS))
        context.focus_in()
        context.set_engine("rime")
        for _ in range(100):
            drain(0.1)
            engine = context.get_engine()
            if engine and engine.get_name() == "rime":
                break
        assert engine and engine.get_name() == "rime", "Rime frontend did not load"
        # Fresh package profile has only Quick HK selected in user.yaml below.
        for code in "of":
            assert context.process_key_event(ord(code), 0, 0)
            drain()
        assert menus and "你" in menus[-1], menus
        choice = menus[-1].index("你") + 1
        assert context.process_key_event(ord(str(choice)), 0, 0)
        drain()
        assert commits == ["你"], commits
        assert menus[-1] and "好" in menus[-1], "Native plugin failed to provide suggestions"
        assert not preedits or not preedits[-1], (preedits, menus[-1])
        assert ''.join(commits) + (preedits[-1] if preedits else '') == '你'
        context.process_key_event(0xff53, 0, 0)  # Browse without previewing in the field.
        drain()
        assert commits == ['你'] and (not preedits or not preedits[-1])
        context.process_key_event(0xff51, 0, 0)  # IBus may page horizontally; return first.
        drain()
        assert commits == ['你'] and (not preedits or not preedits[-1])
        assert '好' in menus[-1], (menus[-3:], commits, preedits)
        choice = menus[-1].index('好') + 1
        context.process_key_event(ord(str(choice)), 0, 0)
        drain()
        assert commits == ['你', '好'], commits
        for code in 'of':
            context.process_key_event(ord(code), 0, 0)
            drain()
        context.process_key_event(ord(str(menus[-1].index('你') + 1)), 0, 0)
        drain()
        assert commits == ['你', '好', '你'] and menus[-1], (commits, menus[-1])
        context.reset()
        drain()
        assert not menus[-1], "Reset resurrected suggestions"
        assert not preedits or not preedits[-1], "Reset left the continuation in the text field"
        context.focus_out()
        drain()
        context.focus_in()
        for code in "vd":
            context.process_key_event(ord(code), 0, 0)
            drain()
        choice = menus[-1].index("好") + 1
        context.process_key_event(ord(str(choice)), 0, 0)
        drain()
        assert commits == ["你", "好", "你", "好"], commits
        for code, punctuation in (("zb", "，"), ("zd", "。"), ("zf", "‧"),
                                  ("zk", "︰"), ("zt", "﹖"), ("zu", "﹗")):
            context.reset()
            drain()
            for character in code + "1":
                context.process_key_event(ord(character), 0, 0)
                drain()
            assert commits[-1] == punctuation, commits
        for letters, modifiers in (('HI', 0), ('HI', 2), ('HI', 1), ('hi', 3)):
            context.reset()
            for character in letters:
                assert context.process_key_event(ord(character), 0, modifiers)
                drain()
            assert menus[-1][0] == '我', (letters, modifiers, menus[-1])
            context.process_key_event(ord('1'), 0, modifiers & 2)
            drain()
            assert commits[-1] == '我', commits
        print("PASS IBus: 你好, predictions, reset, focus, punctuation, uppercase/Caps Lock/Shift codes")
        context.destroy()
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)


if __name__ == "__main__":
    main()
