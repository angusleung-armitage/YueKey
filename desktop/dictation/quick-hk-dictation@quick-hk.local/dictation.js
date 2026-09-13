// SPDX-License-Identifier: MIT
// Optional dictation overlay, independent of the candidate styling extension.
import Clutter from 'gi://Clutter';
import Atspi from 'gi://Atspi';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import IBus from 'gi://IBus';
import St from 'gi://St';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';
import {FocusCaretTracker} from 'resource:///org/gnome/shell/ui/focusCaretTracker.js';
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

export function indicatorPosition(rect, area, width, height, gap = 6) {
    // Centre beneath the caret. A whole-field fallback uses its text-start
    // edge instead of placing the badge beyond the far end of the field.
    const x = rect.x + (rect.width > 4 * gap ? gap : 0) - width / 2;
    let y = rect.y + rect.height + gap;
    if (y + height > area.y + area.height - gap)
        y = rect.y - height - gap;
    return [Math.round(Math.max(area.x + gap, Math.min(x, area.x + area.width - width - gap))),
        Math.round(Math.max(area.y + gap, Math.min(y, area.y + area.height - height - gap)))];
}

export class DictationUI {
    constructor(isQuickHk, extensionPath) {
        this._isQuickHk = isQuickHk;
        this._enabled = false;
        this._generation = 1;
        this._connections = [];
        this._controller = null;
        this._ibus = IBus.Bus.new_async();
        this._purpose = null;
        this._hints = 0;
        this._cursor = null;
        this._accessible = null;
        this._keyboard = Clutter.get_default_backend().get_default_seat()
            .create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
        this._actor = new St.BoxLayout({style_class: 'quick-hk-dictation',
            orientation: Clutter.Orientation.HORIZONTAL, reactive: false,
            can_focus: false, visible: false});
        this._microphone = new Gio.FileIcon({file: Gio.File.new_for_path(
            GLib.build_filenamev([extensionPath, 'microphone-symbolic.svg']))});
        this._busy = new Gio.FileIcon({file: Gio.File.new_for_path(
            GLib.build_filenamev([extensionPath, 'busy-symbolic.svg']))});
        this._icon = new St.Icon({gicon: this._microphone, icon_size: 18});
        this._actor.add_child(this._icon);
        Main.layoutManager.addChrome(this._actor);
        this._object = Gio.DBusExportedObject.wrapJSObject(XML, this);
        this._object.export(Gio.DBus.session, PATH);
        this._owner = Gio.bus_own_name_on_connection(Gio.DBus.session, NAME,
            Gio.BusNameOwnerFlags.NONE, null, null);
        this._watch = Gio.bus_watch_name(Gio.BusType.SESSION, CONTROLLER,
            Gio.BusNameWatcherFlags.NONE,
            (_connection, _name, owner) => { this._controller = owner; },
            () => { this._controller = null; this._actor.hide(); });
        this._connect(global.display, 'notify::focus-window', () => this.invalidate(true));
        this._connect(global.stage, 'notify::key-focus', () => this.invalidate(true));
        this._connect(Main.sessionMode, 'updated', () => this.invalidate());
        this._connect(Main.layoutManager, 'monitors-changed', () => this.invalidate(true));
        // The panel receives content type for direct IBus clients too; those
        // fields do not populate Main.inputMethod.currentFocus on Wayland.
        const manager = IBusManager.getIBusManager();
        // Some direct IBus clients only publish panel geometry while composing.
        // GNOME's accessibility tracker also covers empty editable fields.
        this._tracker = new FocusCaretTracker();
        for (const signal of ['focus-changed', 'caret-moved']) {
            this._connect(this._tracker, signal, (_tracker, event) => {
                if (signal === 'focus-changed' && event.detail1 !== 1)
                    return;
                this._accessible = {source: event.source,
                    window: global.display.focus_window?.get_id()};
                if (this._actor.visible) {
                    this._cursor = null;
                    this._place();
                }
            });
        }
        this._connect(manager, 'set-content-type', (_manager, purpose, hints) => {
            this._purpose = purpose;
            this._hints = hints;
            this.invalidate();
        });
        this._connect(manager, 'focus-in', () => this.invalidate(true));
        this._connect(manager, 'focus-out', () => this.invalidate(true));
        this._connect(Main.inputMethod, 'surrounding-text-set', () => {
            const value = Main.inputMethod.getSurroundingText();
            if (this._surrounding && value.some((part, i) => part !== this._surrounding[i]))
                this.invalidate();
            this._surrounding = value;
        });
        // GNOME 50's supported injection helper reconnects GObject vfuncs.
        this._injections = new InjectionManager();
        const ui = this;
        // Observe the same stage coordinates as GNOME's candidate panel. Shell
        // has already converted Wayland-relative and mixed-scale coordinates.
        // Keep the original handler and its return value intact.
        const popup = manager._candidatePopup;
        if (typeof popup?._setDummyCursorGeometry === 'function') {
            this._injections.overrideMethod(Object.getPrototypeOf(popup),
                '_setDummyCursorGeometry', original => function (x, y, width, height) {
                    const result = original.call(this, x, y, width, height);
                    if ([x, y, width, height].every(Number.isFinite) && width >= 0 && height > 0) {
                        ui._cursor = {x, y, width, height,
                            window: global.display.focus_window?.get_id()};
                        if (ui._actor.visible)
                            ui._place();
                    }
                    return result;
                });
        }
        const prototype = Object.getPrototypeOf(Main.inputMethod);
        for (const method of ['vfunc_focus_in', 'vfunc_focus_out', 'vfunc_reset',
            'vfunc_update_content_purpose', 'vfunc_update_content_hints']) {
            this._injections.overrideMethod(prototype, method, original => function (...args) {
                ui.invalidate(method === 'vfunc_focus_in' || method === 'vfunc_focus_out');
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
            if (value) {
                this._tracker.registerFocusListener();
                this._tracker.registerCaretListener();
            } else {
                this._tracker.deregisterFocusListener();
                this._tracker.deregisterCaretListener();
                this._accessible = null;
            }
        }
    }

    invalidate(clearCursor = false) {
        if (clearCursor)
            this._cursor = null;
        this._generation = (this._generation + 1) >>> 0;
        if (this._actor.visible) {
            this._actor.hide();
            this._object.emit_signal('Invalidated', null);
        }
    }

    _place() {
        const window = global.display.focus_window;
        if (!window)
            return;
        const area = window.get_work_area_current_monitor();
        const frame = window.get_frame_rect();
        if (!this._cursor)
            this._cursor = this._accessibleCursor(window);
        const rect = this._cursor?.window === window.get_id() ? this._cursor :
            {x: frame.x + 16, y: frame.y + frame.height - 64, width: 0, height: 0};
        const [, width] = this._actor.get_preferred_width(-1);
        const [, height] = this._actor.get_preferred_height(width);
        const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
        this._actor.set_position(...indicatorPosition(rect, area, width, height, 6 * scale));
    }

    _accessibleCursor(window) {
        const focused = this._accessible;
        if (!focused || focused.window !== window.get_id())
            return null;
        try {
            const source = focused.source;
            const states = source.get_state_set();
            if (!states.contains(Atspi.StateType.FOCUSED) ||
                !states.contains(Atspi.StateType.SHOWING) ||
                source.get_role() === Atspi.Role.PASSWORD_TEXT ||
                source.get_process_id() !== window.get_pid())
                return null;
            const text = source.get_text_iface();
            let bounds = null;
            try {
                bounds = text?.get_character_extents(text.get_caret_offset(), Atspi.CoordType.WINDOW);
            } catch {
                // Empty text and end-of-text carets can be outside the range
                // accepted by a provider. The field rectangle is still useful.
            }
            if (!bounds || bounds.height <= 0)
                bounds = source.get_component_iface()?.get_extents(Atspi.CoordType.WINDOW);
            if (!bounds || ![bounds.x, bounds.y, bounds.width, bounds.height].every(Number.isFinite) ||
                bounds.width < 0 || bounds.height <= 0)
                return null;
            // Accessibility WINDOW coordinates are relative to client content;
            // no document contents or surrounding text are requested here.
            const client = window.get_client_content_rect();
            const scale = St.ThemeContext.get_for_stage(global.stage).scale_factor;
            return {x: client.x + bounds.x * scale, y: client.y + bounds.y * scale,
                width: bounds.width * scale, height: bounds.height * scale, window: window.get_id()};
        } catch {
            return null;
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
                this._actor.accessible_name = `${titles[state]} · ${seconds}s · Ctrl × 2 停止 · Esc 取消`;
                this._icon.gicon = state === 'recording' ? this._microphone : this._busy;
                const opacity = state === 'recording' ?
                    0.22 + Math.max(0, Math.min(1, level)) * 0.25 : 0.18;
                this._actor.set_style(`box-shadow: 0 2px 8px rgba(0, 120, 55, ${opacity});`);
                this._actor.show();
                this._place();
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
        this._tracker.deregisterFocusListener();
        this._tracker.deregisterCaretListener();
        this._accessible = null;
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
