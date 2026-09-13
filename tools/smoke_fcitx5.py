#!/usr/bin/python3
"""Exercise installed Fcitx5-Rime on a disposable private D-Bus session."""
import os
from pathlib import Path
import subprocess
import time

from gi.repository import Gio, GLib

from smoke_ibus import drain

SERVICE = "org.fcitx.Fcitx5"
INTERFACE = "org.fcitx.Fcitx.InputContext1"


def main():
    if not Path("/.dockerenv").exists() or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        raise SystemExit("Run only in a disposable Docker container with dbus-run-session")
    profile = Path.home() / ".config/fcitx5/profile"
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_text("[Groups/0]\nName=Default\nDefault Layout=us\nDefaultIM=rime\n\n"
                       "[Groups/0/Items/0]\nName=keyboard-us\nLayout=\n\n"
                       "[Groups/0/Items/1]\nName=rime\nLayout=\n\n[GroupOrder]\n0=Default\n")
    log = Path("/tmp/quick-hk-fcitx5-smoke.log").open("w+")
    daemon = subprocess.Popen(["fcitx5", "--disable=wayland,waylandim,xim,kimpanel", "--keep"],
                              stdout=log, stderr=log,
                              env=dict(os.environ, FCITX_X11_USE_CLIENT_SIDE_UI="1"))
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        def call(path, interface, method, signature=None, args=()):
            params = GLib.Variant(signature, args) if signature else None
            return bus.call_sync(SERVICE, path, interface, method, params, None,
                                 Gio.DBusCallFlags.NO_AUTO_START, 10000, None).unpack()

        for _ in range(100):
            try:
                path, _uuid = call("/org/freedesktop/portal/inputmethod", "org.fcitx.Fcitx.InputMethod1",
                                   "CreateInputContext", "(a(ss))", ([("program", "quick-hk-package-smoke"),
                                                                        ("display", "x11:" + os.environ["DISPLAY"])],))
                break
            except GLib.Error:
                time.sleep(0.1)
        else:
            raise AssertionError("Fcitx5 D-Bus frontend did not start")
        commits, menus, events = [], [], []
        def signal(_bus, _sender, _path, _interface, name, parameters, _data):
            values = parameters.unpack()
            events.append((name, values))
            if name == "CommitString":
                commits.append(values[0])
            elif name == "UpdateClientSideUI":
                menus.append([text for _label, text in values[4]])
        token = bus.signal_subscribe(SERVICE, INTERFACE, None, path, None,
                                     Gio.DBusSignalFlags.NONE, signal, None)
        def context(method, signature=None, args=()):
            result = call(path, INTERFACE, method, signature, args)
            drain()
            return result

        context("SetCapability", "(t)", ((1 << 1) | (1 << 4) | (1 << 39),))
        context("FocusIn")
        call("/controller", "org.fcitx.Fcitx.Controller1", "Activate")
        call("/controller", "org.fcitx.Fcitx.Controller1", "SetCurrentIM", "(s)", ("rime",))
        drain(0.5)
        def key(character):
            return context("ProcessKeyEvent", "(uuubu)", (ord(character), 0, 0, False, 0))[0]

        # Fcitx5-Rime deploys asynchronously on first activation.
        for _ in range(100):
            context("Reset")
            for character in "of":
                key(character)
            if menus and "你" in menus[-1]:
                break
            drain(0.1)
        assert menus and "你" in menus[-1], events[-10:]
        key(str(menus[-1].index("你") + 1))
        assert commits == ["你"], commits
        assert "好" in menus[-1], "Native prediction plugin did not load"
        context("Reset")
        assert not menus[-1], "Reset resurrected suggestions"
        context("FocusOut")
        context("FocusIn")
        for character in "vd":
            key(character)
        key(str(menus[-1].index("好") + 1))
        assert commits == ["你", "好"], commits
        for code, punctuation in (("zb", "，"), ("zd", "。")):
            context("Reset")
            for character in code + "1":
                key(character)
            assert commits[-1] == punctuation, commits
        print("PASS Fcitx5: 你好, native prediction, reset, focus out/in, zb1/zd1 punctuation")
        context("DestroyIC")
        bus.signal_unsubscribe(token)
    except BaseException:
        log.flush()
        log.seek(0)
        print(log.read()[-6000:])
        raise
    finally:
        daemon.terminate()
        daemon.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
