// SPDX-License-Identifier: MIT
// Optional dictation overlay, independent of the candidate styling extension.
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import IBus from 'gi://IBus';
import St from 'gi://St';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as IBusManager from 'resource:///org/gnome/shell/misc/ibusManager.js';

const NAME = 'org.quick_hk.DictationDesktop';
const PATH = '/org/quick_hk/DictationDesktop';
const CONTROLLER = 'org.quick_hk.Dictation';
const XML = `<node><interface name="${NAME}">
<method name="Snapshot"><arg type="s" direction="out"/></method>
<method name="Show"><arg type="s" direction="in"/><arg type="d" direction="in"/><arg type="d" direction="in"/></method>
<method name="Wake"><arg type="u" direction="in"/><arg type="u" direction="in"/><arg type="s" direction="in"/><arg type="b" direction="out"/></method>
<signal name="Invalidated"/>
</interface></node>`;

export function allowedTarget(enabled, quickHk, locked, window, purpose, hints) {
    // IBus PASSWORD=8, PIN=9; PRIVATE=2048, HIDDEN_TEXT=4096.
    return Boolean(enabled && quickHk && !locked && window && typeof purpose === 'number' &&
        purpose !== 8 && purpose !== 9 && !(hints & (2048 | 4096)));
}

export class DictationUI {
    constructor(isQuickHk) {
        this._isQuickHk = isQuickHk;
        this._enabled = false;
        this._generation = 1;
        this._connections = [];
        this._controller = null;
        this._ibus = IBus.Bus.new_async();
        this._purpose = null;
        this._hints = 0;
        this._keyboard = Clutter.get_default_backend().get_default_seat()
            .create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        this._actor = new St.BoxLayout({style_class: 'quick-hk-dictation',
            orientation: Clutter.Orientation.VERTICAL, reactive: false,
            can_focus: false, visible: false});
        this._label = new St.Label({text: '準備中…'});
        this._level = new St.Label({text: '○ ○ ○ ○ ○ ○ ○ ○'});
        this._actor.add_child(this._label);
        this._actor.add_child(this._level);
        Main.layoutManager.addChrome(this._actor);
        this._object = Gio.DBusExportedObject.wrapJSObject(XML, this);
        this._object.export(Gio.DBus.session, PATH);
        this._owner = Gio.bus_own_name_on_connection(Gio.DBus.session, NAME,
            Gio.BusNameOwnerFlags.NONE, null, null);
        this._watch = Gio.bus_watch_name(Gio.BusType.SESSION, CONTROLLER,
            Gio.BusNameWatcherFlags.NONE,
            (_connection, _name, owner) => { this._controller = owner; },
            () => { this._controller = null; this._actor.hide(); });
        this._connect(global.display, 'notify::focus-window', () => this.invalidate());
        this._connect(global.stage, 'notify::key-focus', () => this.invalidate());
        this._connect(Main.sessionMode, 'updated', () => this.invalidate());
        this._connect(Main.layoutManager, 'monitors-changed', () => this.invalidate());
        // The panel receives content type for direct IBus clients too; those
        // fields do not populate Main.inputMethod.currentFocus on Wayland.
        const manager = IBusManager.getIBusManager();
        this._connect(manager, 'set-content-type', (_manager, purpose, hints) => {
            this._purpose = purpose;
            this._hints = hints;
            this.invalidate();
        });
        this._connect(manager, 'focus-in', () => this.invalidate());
        this._connect(manager, 'focus-out', () => this.invalidate());
        this._connect(Main.inputMethod, 'surrounding-text-set', () => {
            const value = Main.inputMethod.getSurroundingText();
            if (this._surrounding && value.some((part, i) => part !== this._surrounding[i]))
                this.invalidate();
            this._surrounding = value;
        });
        // GNOME 50's supported injection helper reconnects GObject vfuncs.
        this._injections = new InjectionManager();
        const ui = this;
        const prototype = Object.getPrototypeOf(Main.inputMethod);
        for (const method of ['vfunc_focus_in', 'vfunc_focus_out', 'vfunc_reset',
            'vfunc_update_content_purpose', 'vfunc_update_content_hints']) {
            this._injections.overrideMethod(prototype, method, original => function (...args) {
                ui.invalidate();
                return original.call(this, ...args);
            });
        }
    }

    _connect(object, signal, callback) {
        this._connections.push([object, object.connect(signal, callback)]);
    }

    setEnabled(value) {
        if (this._enabled !== value) {
            this._enabled = value;
            this.invalidate();
        }
    }

    invalidate() {
        this._generation = (this._generation + 1) >>> 0;
        if (this._actor.visible) {
            this._actor.hide();
            this._object.emit_signal('Invalidated', null);
        }
    }

    Snapshot() {
        const im = Main.inputMethod;
        const window = global.display.focus_window;
        return JSON.stringify({generation: this._generation,
            window: window?.get_id() ?? 0,
            allowed: allowedTarget(this._enabled, this._isQuickHk(),
                Main.sessionMode.isLocked || Main.sessionMode.isGreeter,
                window, im.currentFocus ? im._purpose : this._purpose,
                im.currentFocus ? im._hints : this._hints)});
    }

    _authorized(invocation) {
        if (invocation.get_sender() === this._controller)
            return true;
        invocation.return_dbus_error('org.quick_hk.Error.Unauthorized', 'Dictation controller required');
        return false;
    }

    ShowAsync([state, level, elapsed], invocation) {
        if (!this._authorized(invocation))
            return;
        if (state === 'idle' || !JSON.parse(this.Snapshot()).allowed) {
            this._actor.hide();
        } else {
            const titles = {preparing: '準備中…', recording: '正在聆聽', finishing: '正在辨識…'};
            if (Object.hasOwn(titles, state)) {
                const seconds = Math.max(0, Math.floor(elapsed));
                this._label.text = `🎙 ${titles[state]}  ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
                const count = Math.max(0, Math.min(8, Math.round(level * 8)));
                this._level.text = state === 'recording'
                    ? `${'● '.repeat(count)}${'○ '.repeat(8 - count)}  ·  Ctrl × 2 停止`
                    : 'Esc 取消';
                this._actor.show();
                const monitor = Main.layoutManager.focusMonitor ?? Main.layoutManager.primaryMonitor;
                if (monitor)
                    this._actor.set_position(Math.round(monitor.x + monitor.width / 2 - 155),
                        monitor.y + monitor.height - 140);
            }
        }
        invocation.return_value(null);
    }

    WakeAsync([generation, window, path], invocation) {
        if (!this._authorized(invocation))
            return;
        const snapshot = JSON.parse(this.Snapshot());
        if (!snapshot.allowed || generation !== snapshot.generation || window !== snapshot.window ||
            !this._ibus.is_connected() || this._ibus.current_input_context() !== path) {
            invocation.return_value(new GLib.Variant('(b)', [false]));
            return;
        }
        try {
            // IBus permits ProcessKeyEvent only from the context's owning app.
            // A Right Ctrl tap reaches Rime through the owning application.
            // It inserts no character if focus changes before delivery. Rime
            // consumes it only with a queued result and acknowledges the commit.
            // F13–F35 are not consistently mapped by Ubuntu's XKB keymaps.
            const now = GLib.get_monotonic_time();
            this._keyboard.notify_keyval(now, 0xffe4, Clutter.KeyState.PRESSED);
            this._keyboard.notify_keyval(now + 1, 0xffe4, Clutter.KeyState.RELEASED);
            invocation.return_value(new GLib.Variant('(b)', [true]));
        } catch {
            invocation.return_value(new GLib.Variant('(b)', [false]));
        }
    }

    destroy() {
        this.invalidate();
        this._injections.clear();
        for (const [object, id] of this._connections)
            object.disconnect(id);
        Gio.bus_unwatch_name(this._watch);
        Gio.bus_unown_name(this._owner);
        this._object.unexport();
        this._keyboard = null;
        this._actor.destroy();
    }
}
