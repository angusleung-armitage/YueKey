#!/usr/bin/python3
"""Exercise installed Fcitx5-Rime on a disposable private D-Bus session."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
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
        commits, menus, events, preedits = [], [], [], []
        def signal(_bus, _sender, _path, _interface, name, parameters, _data):
            values = parameters.unpack()
            events.append((name, values))
            if name == "CommitString":
                commits.append(values[0])
            elif name == "UpdateClientSideUI":
                menus.append([text for _label, text in values[4]])
            elif name == "UpdateFormattedPreedit":
                preedits.append(''.join(text for text, _format in values[0]))
        token = bus.signal_subscribe(SERVICE, INTERFACE, None, path, None,
                                     Gio.DBusSignalFlags.NONE, signal, None)
        def context(method, signature=None, args=()):
            result = call(path, INTERFACE, method, signature, args)
            drain()
            return result

        context("SetSupportedCapability", "(t)", ((1 << 42) - 1,))
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
        assert not preedits or not preedits[-1], (preedits, menus[-1])
        assert ''.join(commits) + (preedits[-1] if preedits else '') == '你'
        context('ProcessKeyEvent', '(uuubu)', (0xff54, 0, 0, False, 0))
        assert commits == ['你'] and (not preedits or not preedits[-1])
        key(str(menus[-1].index('好') + 1))
        assert commits == ['你', '好'], commits
        for character in 'of':
            key(character)
        key(str(menus[-1].index('你') + 1))
        assert commits == ['你', '好', '你'] and menus[-1], (commits, menus[-1])
        context("Reset")
        assert not menus[-1], "Reset resurrected suggestions"
        assert not preedits or not preedits[-1], "Reset left the continuation in the text field"
        context("FocusOut")
        context("FocusIn")
        for character in "vd":
            key(character)
        key(str(menus[-1].index("好") + 1))
        assert commits == ["你", "好", "你", "好"], commits
        for code, punctuation in (("zb", "，"), ("zd", "。")):
            context("Reset")
            for character in code + "1":
                key(character)
            assert commits[-1] == punctuation, commits
        print("PASS Fcitx5: 你好, native prediction, reset, focus out/in, zb1/zd1 punctuation")
        check_dictation(bus, context, commits, call)
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


def check_dictation(bus, context, commits, fcitx):
    """Real Fcitx event loop, simulated audio producer; never opens a microphone."""
    name, path = 'org.quick_hk.FcitxDictation', '/org/quick_hk/FcitxDictation'
    controller = 'org.quick_hk.Dictation'
    # A second connection verifies that normal desktop clients cannot submit text.
    producer = Gio.DBusConnection.new_for_address_sync(os.environ['DBUS_SESSION_BUS_ADDRESS'],
        Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
        None, None)
    toggles, cancelled = [], []
    xml = Gio.DBusNodeInfo.new_for_xml('''<node><interface name="org.quick_hk.Dictation">
      <method name="Toggle"><arg type="s" direction="in"/></method>
      <method name="Cancel"><arg type="s" direction="in"/></method></interface></node>''')
    def method(_c, _sender, _p, _i, method, args, invocation):
        (toggles if method == 'Toggle' else cancelled).append(args.unpack()[0])
        invocation.return_value(None)
    registration = producer.register_object('/org/quick_hk/Dictation', xml.interfaces[0], method, None, None)
    producer.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
        'RequestName', GLib.Variant('(su)', (controller, 0)), None, Gio.DBusCallFlags.NONE, 1000, None)
    drain()
    def bridge(method, signature=None, args=(), connection=producer):
        value = connection.call_sync(name, path, name, method,
            GLib.Variant(signature, args) if signature else None, None, Gio.DBusCallFlags.NO_AUTO_START, 1000, None)
        drain(.01)
        return value.unpack()
    def key(sym, release=False):
        context('ProcessKeyEvent', '(uuubu)', (sym, 0, 0, release, 0))
    def double(sym=0xffe3):
        for release in (False, True, False, True):
            key(sym, release)
    def start():
        context('Reset')
        before = len(toggles)
        double()
        assert len(toggles) == before + 1, ('Double Ctrl did not start', bridge('Snapshot'))
        return toggles[-1]
    try:
        assert not bridge('Configure', '(bs)', (True, 'Control_L'), bus)[0]
        assert bridge('Configure', '(bs)', (True, 'Control_L'))[0]
        identifier = start()
        assert json.loads(bridge('Snapshot')[0])['allowed']
        assert not bridge('QueueResult', '(ss)', (identifier, 'premature'))[0]
        double()
        assert toggles[-2:] == [identifier, identifier]
        assert not bridge('QueueResult', '(ss)', (identifier, 'unauthorized'), bus)[0]
        before = list(commits)
        assert bridge('QueueResult', '(ss)', (identifier, '我，𨋢'))[0]
        assert commits == before + ['我，𨋢'], commits
        assert not bridge('QueueResult', '(ss)', (identifier, 'duplicate'))[0]
        for invalidate in (lambda: context('Reset'), lambda: context('FocusOut'),
                           lambda: context('SetCursorRect', '(iiii)', (10, 20, 5, 20)),
                           lambda: key(0xff1b), lambda: key(ord('a'))):
            identifier = start()
            invalidate()
            assert identifier in cancelled
            assert not bridge('QueueResult', '(ss)', (identifier, 'stale'))[0]
            context('FocusIn')
        capabilities = (1 << 1) | (1 << 4) | (1 << 39)
        for flag in (1 << 3, 1 << 36, 1 << 40):
            identifier = start()
            context('SetCapability', '(t)', (capabilities | flag,))
            assert identifier in cancelled
            assert not json.loads(bridge('Snapshot')[0])['allowed']
            count = len(toggles)
            double()
            assert len(toggles) == count, 'Secure field started dictation'
            assert not bridge('QueueResult', '(ss)', (identifier, 'secure'))[0]
            context('SetCapability', '(t)', (capabilities,))
        context('Reset')
        key(0xffe1); key(0xffe1, True)  # Left Shift switches to English.
        assert not json.loads(bridge('Snapshot')[0])['allowed'], 'ASCII mode allowed dictation'
        key(0xffe1); key(0xffe1, True)
        assert bridge('Configure', '(bs)', (True, 'Control_R'))[0]
        count = len(toggles)
        double()
        assert len(toggles) == count
        double(0xffe4)
        assert len(toggles) == count + 1
        producer.close_sync(None)
        drain()
        assert not json.loads(bridge('Snapshot', connection=bus)[0])['allowed'], 'Controller loss remained enabled'
        print('PASS Fcitx dictation: double Ctrl, Unicode once, authorization, secure fields, focus/reset/cursor/keys, ASCII mode, right Ctrl, owner loss')
        check_controller(context, commits, double, bus)
    finally:
        if not producer.is_closed():
            producer.unregister_object(registration)
            producer.close_sync(None)


def check_controller(context, commits, double, bus):
    """Exercise the production KDE controller with a deterministic audio worker."""
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='yuekey-controller-') as tmp:
        folder = Path(tmp)
        settings = folder / 'settings.toml'
        settings.write_text('dictation_enabled = true\n', encoding='utf-8')
        worker = folder / 'worker.py'
        worker.write_text('''import json, sys
print(json.dumps({'event': 'ready'}), flush=True)
for line in sys.stdin:
    value = json.loads(line)
    action = value['action']
    if action == 'start':
        print(json.dumps({'event': 'recording', 'id': value['id']}), flush=True)
    elif action == 'stop':
        print(json.dumps({'event': 'finishing', 'id': value['id']}), flush=True)
        print(json.dumps({'event': 'result', 'id': value['id'], 'text': '廣東話，測試。'}), flush=True)
''', encoding='utf-8')
        launch = '''import os, sys
from quick_hk import dictation_service as service
service.status = lambda **_: {'ready': True}
service.worker_command = lambda: [sys.executable, sys.argv[1]]
service.worker_environment = lambda: dict(os.environ)
raise SystemExit(service.serve())
'''
        env = dict(os.environ, PYTHONPATH=str(root / 'src'), QUICK_HK_CONFIG=str(settings), XDG_CURRENT_DESKTOP='KDE')
        process = subprocess.Popen([sys.executable, '-c', launch, str(worker)], env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        def status():
            value = bus.call_sync('org.quick_hk.Dictation', '/org/quick_hk/Dictation',
                'org.quick_hk.Dictation', 'GetStatus', None, None, Gio.DBusCallFlags.NO_AUTO_START, 1000, None)
            return json.loads(value.unpack()[0])
        try:
            for _ in range(100):
                drain(.05)
                try:
                    ready = status()
                    if ready['ready']:
                        break
                except GLib.Error:
                    pass
            else:
                raise AssertionError('KDE controller did not become ready')
            assert ready['frontend'] == 'fcitx5' and ready['provider'] == 'cpu'
            context('Reset')
            before = list(commits)
            double()
            assert status()['state'] == 'recording', status()
            double()
            for _ in range(40):
                drain(.05)
                if status()['state'] == 'idle':
                    break
            assert commits == before + ['廣東話，測試。'], (commits, status())
            print('PASS KDE controller: automatic frontend selection, worker protocol, start/stop, exactly-once commit')
        finally:
            process.terminate()
            _, errors = process.communicate(timeout=10)
            if process.returncode:
                print(errors[-3000:])


if __name__ == "__main__":
    main()
