"""GNOME/IBus controller; recognition and audio capture live in a CPU worker."""
from __future__ import annotations

import json
import signal
import subprocess
import threading
import time

from .dictation_setup import status, worker_command, worker_environment
from .dictation_state import Session, Target
from .settings import load_settings

NAME = 'org.quick_hk.Dictation'
PATH = '/org/quick_hk/Dictation'
BRIDGE = 'org.quick_hk.RimeDictation'
BRIDGE_PATH = '/org/quick_hk/RimeDictation'
DESKTOP = 'org.quick_hk.DictationDesktop'
DESKTOP_PATH = '/org/quick_hk/DictationDesktop'
XML = '''<node><interface name="org.quick_hk.Dictation">
<method name="Toggle"><arg type="s" direction="in"/></method>
<method name="Cancel"><arg type="s" direction="in"/></method>
<method name="Committed"><arg type="s" direction="in"/></method>
<method name="GetStatus"><arg type="s" direction="out"/></method>
</interface></node>'''


def serve() -> int:
    import gi
    gi.require_version('IBus', '1.0')
    from gi.repository import Gio, GLib, IBus

    class Controller:
        def __init__(self):
            IBus.init()
            self.ibus = IBus.Bus()
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.loop = GLib.MainLoop()
            self.session = None
            self.worker = None
            self.ready = False
            self.worker_started = 0
            self.session_started = 0
            self.error = ''
            info = Gio.DBusNodeInfo.new_for_xml(XML)
            self.registration = self.bus.register_object(PATH, info.interfaces[0], self.method, None, None)
            self.owner = Gio.bus_own_name_on_connection(
                self.bus, NAME, Gio.BusNameOwnerFlags.NONE, self.acquired, self.lost)
            self.timer = GLib.timeout_add(150, self.tick)
            self.desktop_watch = self.bus.signal_subscribe(
                DESKTOP, DESKTOP, 'Invalidated', DESKTOP_PATH, None,
                Gio.DBusSignalFlags.NONE, lambda *_: self.cancel())

        def call(self, name, path, method, arguments=None, reply=None):
            return self.bus.call_sync(name, path, name, method, arguments,
                                      GLib.VariantType.new(reply) if reply else None,
                                      Gio.DBusCallFlags.NO_AUTO_START, 1000, None)

        def name_owner(self, name):
            try:
                result = self.bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                    'org.freedesktop.DBus', 'GetNameOwner', GLib.Variant('(s)', (name,)),
                    GLib.VariantType.new('(s)'), Gio.DBusCallFlags.NONE, 500, None)
                return result.unpack()[0]
            except GLib.Error:
                return None

        def acquired(self, *_):
            try:
                if load_settings().dictation_enabled and status()['ready']:
                    self.start_worker()
            except (RuntimeError, ValueError, OSError):
                self.fail('Could not load CPU speech models. Run quick-hk dictation setup.')

        def lost(self, *_):
            self.loop.quit()

        def method(self, _connection, sender, _path, _interface, method, args, invocation):
            if method == 'GetStatus':
                invocation.return_value(GLib.Variant('(s)', (json.dumps({
                    'ready': self.ready, 'state': self.session.state if self.session else 'idle',
                    'provider': 'cpu', 'error': self.error,
                    'desktop_ready': bool(self.name_owner(DESKTOP)),
                    'rime_ready': bool(self.name_owner(BRIDGE)),
                }),)))
                return
            if sender != self.name_owner(BRIDGE):
                invocation.return_dbus_error('org.quick_hk.Error.Unauthorized', 'Rime bridge required')
                return
            request_id = args.unpack()[0]
            if method == 'Cancel':
                if self.session and request_id == self.session.request_id:
                    self.cancel()
            elif method == 'Committed':
                if (self.session and request_id == self.session.request_id
                        and self.session.state == 'committing'):
                    self.cancel()
            else:
                self.toggle(request_id)
            invocation.return_value(None)

        def desktop(self):
            value = self.call(DESKTOP, DESKTOP_PATH, 'Snapshot', reply='(s)')
            snapshot = json.loads(value.unpack()[0])
            if not snapshot['allowed']:
                raise RuntimeError('Focus a text field with 港式速成 selected.')
            path = self.ibus.current_input_context()
            if not path or path == '/':
                raise RuntimeError('No active IBus text field.')
            return Target(path, snapshot['generation'], snapshot['window'])

        def show(self, state, level=0.0, elapsed=0.0):
            self.bus.call(DESKTOP, DESKTOP_PATH, DESKTOP, 'Show',
                GLib.Variant('(sdd)', (state, float(level), float(elapsed))),
                None, Gio.DBusCallFlags.NO_AUTO_START, 500, None, None, None)

        def notify(self, message):
            # Display only a fixed error message, never recognized speech.
            try:
                subprocess.Popen(['notify-send', '粵鍵 YueKey · 語音輸入', message],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass

        def fail(self, message):
            self.error = message
            self.cancel()
            self.notify(message)

        def start_worker(self):
            if self.worker and self.worker.poll() is None:
                return
            if not status(verify=True)['ready']:
                raise RuntimeError('Run quick-hk dictation setup to prepare the CPU models.')
            self.ready = False
            self.worker_started = time.monotonic()
            self.worker = subprocess.Popen(worker_command(), env=worker_environment(),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, bufsize=1)
            process = self.worker

            def read():
                try:
                    for line in process.stdout:
                        if len(line) > 131072:
                            break
                        try:
                            event = json.loads(line)
                        except ValueError:
                            break
                        GLib.idle_add(self.event, process, event)
                finally:
                    GLib.idle_add(self.exited, process)
            threading.Thread(target=read, daemon=True).start()

        def send(self, action, **values):
            if self.worker is None or self.worker.poll() is not None:
                raise RuntimeError('Speech worker is unavailable. Try again.')
            try:
                self.worker.stdin.write(json.dumps({'action': action, **values}) + '\n')
                self.worker.stdin.flush()
            except (OSError, ValueError) as error:
                raise RuntimeError('Speech worker stopped. Try again.') from error

        def start_recording(self):
            if not self.session or self.desktop() != self.session.target:
                self.cancel()
                return
            settings = load_settings()
            if not settings.dictation_enabled:
                self.cancel()
                return
            self.send('start', id=self.session.request_id,
                      microphone=settings.dictation_microphone,
                      punctuation=settings.dictation_punctuation)

        def toggle(self, request_id):
            try:
                if self.session and self.session.request_id == request_id:
                    if self.session.state == 'recording':
                        self.session.state = 'finishing'
                        self.show('finishing')
                        self.send('stop', id=request_id)
                    elif self.session.state == 'preparing':
                        self.cancel()
                    return
                self.cancel()
                if not load_settings().dictation_enabled:
                    self.clear_bridge(request_id)
                    return
                self.session = Session(request_id, self.desktop())
                self.session_started = time.monotonic()
                self.error = ''
                self.show('preparing')
                self.start_worker()
                if self.ready:
                    self.start_recording()
            except (GLib.Error, RuntimeError, ValueError, OSError):
                self.clear_bridge(request_id)
                self.fail('Dictation is unavailable. Check quick-hk dictation status and enable YueKey Dictation in Extensions.')

        def clear_bridge(self, request_id):
            self.bus.call(BRIDGE, BRIDGE_PATH, BRIDGE, 'Cancel',
                GLib.Variant('(s)', (request_id,)), None,
                Gio.DBusCallFlags.NO_AUTO_START, 500, None, None, None)

        def cancel(self):
            session, self.session = self.session, None
            if session:
                session.consumed = True
                try:
                    self.send('cancel', id=session.request_id)
                except RuntimeError:
                    pass
                self.clear_bridge(session.request_id)
            self.show('idle')

        def event(self, process, event):
            if process is not self.worker:
                return GLib.SOURCE_REMOVE
            try:
                kind = event.get('event')
                if kind == 'ready':
                    self.ready = True
                    if self.session:
                        self.start_recording()
                    return GLib.SOURCE_REMOVE
                if not self.session or event.get('id') != self.session.request_id:
                    return GLib.SOURCE_REMOVE
                if kind == 'error':
                    self.fail(event.get('message', 'Dictation failed.'))
                elif kind == 'recording':
                    self.session.state = 'recording'
                    self.show('recording')
                elif kind == 'level':
                    self.show(self.session.state, event['level'], event['elapsed'])
                elif kind == 'finishing':
                    self.session.state = 'finishing'
                    self.show('finishing')
                elif kind == 'result':
                    target = self.desktop()
                    text = event.get('text', '')
                    if not text or not self.session.consume(event['id'], target):
                        self.cancel()
                        return GLib.SOURCE_REMOVE
                    accepted = self.call(BRIDGE, BRIDGE_PATH, 'QueueResult',
                        GLib.Variant('(ss)', (event['id'], text)), '(b)').unpack()[0]
                    if not accepted or self.desktop() != target:
                        self.cancel()
                        return GLib.SOURCE_REMOVE
                    # The desktop rechecks focus immediately before the IBus event.
                    self.session.state = 'committing'
                    self.session_started = time.monotonic()
                    sent = self.call(DESKTOP, DESKTOP_PATH, 'Wake', GLib.Variant('(uus)',
                        (target.generation, target.window, target.context)), '(b)').unpack()[0]
                    if not sent:
                        self.cancel()
            except (GLib.Error, RuntimeError, ValueError, KeyError):
                self.fail('Dictation stopped because the text field or input service changed.')
            return GLib.SOURCE_REMOVE

        def exited(self, process):
            if process is self.worker:
                self.ready = False
                self.worker = None
                if self.session:
                    self.fail('Speech worker stopped. Double-tap Ctrl to try again.')
            process.stdout.close()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return GLib.SOURCE_REMOVE

        def tick(self):
            try:
                enabled = load_settings().dictation_enabled
                if not enabled:
                    self.cancel()
                    if self.worker:
                        self.worker.terminate()
                    self.loop.quit()
                    return GLib.SOURCE_CONTINUE
                if self.session:
                    if (self.desktop() != self.session.target or
                            time.monotonic() - self.session_started >
                            (5 if self.session.state == 'committing' else 180)):
                        self.cancel()
                if self.worker and not self.ready and time.monotonic() - self.worker_started > 30:
                    self.worker.terminate()
                    self.fail('CPU models took too long to start. Check dictation setup.')
            except (GLib.Error, RuntimeError, ValueError, OSError):
                self.cancel()
            return GLib.SOURCE_CONTINUE

        def close(self):
            self.cancel()
            if self.worker:
                self.worker.terminate()
                try:
                    self.worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.worker.kill()
                    self.worker.wait()
            if self.registration:
                self.bus.unregister_object(self.registration)
            self.bus.signal_unsubscribe(self.desktop_watch)
            GLib.source_remove(self.timer)
            Gio.bus_unown_name(self.owner)

    controller = Controller()
    for signum in (signal.SIGINT, signal.SIGTERM):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signum, lambda: (controller.loop.quit(), False)[1])
    try:
        controller.loop.run()
    finally:
        controller.close()
    return 0


def live_status() -> dict:
    try:
        from gi.repository import Gio, GLib
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = bus.call_sync(NAME, PATH, NAME, 'GetStatus', None,
            GLib.VariantType.new('(s)'), Gio.DBusCallFlags.NO_AUTO_START, 1000, None)
        return json.loads(result.unpack()[0])
    except (ImportError, ValueError, RuntimeError) as error:
        return {'ready': False, 'state': 'unavailable', 'error': str(error)}
    except Exception:
        return {'ready': False, 'state': 'not running'}
