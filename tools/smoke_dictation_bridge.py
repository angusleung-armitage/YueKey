#!/usr/bin/python3
"""Exercise real librime + GDBus in an isolated dbus-run-session; no desktop input."""
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import tempfile
import time

from gi.repository import Gio, GLib

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'build/native'
CONTROLLER = 'org.quick_hk.Dictation'
BRIDGE = 'org.quick_hk.RimeDictation'


def main():
    if not os.environ.get('QUICK_HK_ISOLATED_BUS'):
        raise SystemExit('Run with QUICK_HK_ISOLATED_BUS=1 dbus-run-session -- python3 tools/smoke_dictation_bridge.py')
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                  'RequestName', GLib.Variant('(su)', (CONTROLLER, 0)), None,
                  Gio.DBusCallFlags.NONE, 1000, None)
    requests = []
    commits = []
    xml = f'''<node><interface name="{CONTROLLER}">
    <method name="Toggle"><arg type="s" direction="in"/></method>
    <method name="Cancel"><arg type="s" direction="in"/></method>
    <method name="Committed"><arg type="s" direction="in"/></method></interface></node>'''

    def method(_bus, _sender, _path, _interface, name, args, invocation):
        if name == 'Toggle':
            requests.append(args.unpack()[0])
        elif name == 'Committed':
            commits.append(args.unpack()[0])
        invocation.return_value(None)

    registration = bus.register_object('/org/quick_hk/Dictation', Gio.DBusNodeInfo.new_for_xml(xml).interfaces[0], method, None, None)
    context = GLib.MainContext.default()

    def drain(duration=.05):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            while context.pending(): context.iteration(False)
            time.sleep(.002)

    with tempfile.TemporaryDirectory(prefix='quick-hk-dictation-test-') as temporary:
        root = Path(temporary)
        shutil.copytree(ROOT / 'build/data', root, dirs_exist_ok=True)
        (root / 'default.custom.yaml').write_text('patch:\n  schema_list:\n    - schema: quick_hk\n')
        (root / 'quick_hk.custom.yaml').write_text('''patch:
  engine/processors/@before 0: quick_hk_dictation
  quick_hk/dictation_enabled: true
  quick_hk/dictation_key: Control_L
''')
        subprocess.run([str(NATIVE / 'quick-hk-deployer'), '--build', str(root), '/usr/share/rime-data', str(root / 'build')], check=True, capture_output=True)
        with (root / 'stderr.log').open('w+') as log:
            probe = subprocess.Popen([str(NATIVE / 'quick-hk-probe'), str(root), '/usr/share/rime-data',
                str(NATIVE / 'librime-quick-hk-predict.so'), str(NATIVE / 'librime-quick-hk-dictation.so')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, bufsize=1)
            def send(command):
                probe.stdin.write(command + '\n'); probe.stdin.flush()
                if not select.select([probe.stdout], [], [], 5)[0]:
                    log.seek(0); raise AssertionError(log.read())
                line = probe.stdout.readline()
                if not line:
                    log.seek(0); raise AssertionError(log.read())
                return json.loads(line)
            def key(code, modifiers=0): return send(f'key {code} {modifiers}')
            def double_ctrl():
                before = len(requests)
                for _ in range(2): key(0xffe3); key(0xffe3, 1 << 30)
                drain()
                assert len(requests) == before + 1, ('double Ctrl not detected', requests)
                return requests[-1]
            def queue_result(request, text):
                return bus.call_sync(BRIDGE, '/org/quick_hk/RimeDictation', BRIDGE, 'QueueResult',
                    GLib.Variant('(ss)', (request, text)), GLib.VariantType.new('(b)'),
                    Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
            try:
                send('option prediction 0'); drain()
                request = double_ctrl()
                assert double_ctrl() == request, 'second double tap must stop the same request'
                assert not queue_result('stale', 'wrong')
                assert queue_result(request, '我哋喺呢度測試。')
                assert not queue_result(request, 'duplicate')
                assert key(0xffe4)['commit'] == '我哋喺呢度測試。'
                drain()
                assert commits == [request], 'Rime must acknowledge the matching commit'
                assert key(0xffe4)['commit'] == ''
                request = double_ctrl()
                assert queue_result(request, 'must not appear')
                send('clear')  # Same operation used on focus/reset
                assert key(0xffe4)['commit'] == ''
                assert not queue_result(request, 'stale after reset')
                request = double_ctrl()
                key(0xff1b)  # Escape cancels
                assert not queue_result(request, 'stale after Escape')
                count = len(requests)
                key(0xffe3); key(ord('c'), 4); key(0xffe3, 1 << 30)
                key(0xffe3); key(0xffe3, 1 << 30); drain()
                assert len(requests) == count, 'Ctrl+C must not trigger recording'
                send('option ascii_mode 1')
                for _ in range(2): key(0xffe3); key(0xffe3, 1 << 30)
                drain(); assert len(requests) == count, 'English mode must not trigger recording'
                print('PASS native bridge: double Ctrl, stop, Unicode commit once, stale IDs, reset/focus, Escape, Ctrl+C, English mode')
            finally:
                probe.communicate('quit\n', timeout=5)
    bus.unregister_object(registration)


if __name__ == '__main__':
    main()
