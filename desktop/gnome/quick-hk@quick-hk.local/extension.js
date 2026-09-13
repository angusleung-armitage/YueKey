// SPDX-License-Identifier: MIT
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as IBusManager from 'resource:///org/gnome/shell/misc/ibusManager.js';
import * as Keyboard from 'resource:///org/gnome/shell/ui/status/keyboard.js';

const SCHEMA_NAME = '港式速成';
const STYLE_CLASSES = ['quick-hk', 'quick-hk-light', 'quick-hk-dark'];

// ibus-rime exposes the current Chinese schema name as InputMode's label.
// A missing label, maintenance mode, Abc, and other Rime schemas fail closed.
function isQuickHk(source) {
    if (source?.type !== 'ibus' || source.id !== 'rime' || !source.properties)
        return false;
    for (let i = 0; ; i++) {
        const property = source.properties.get(i);
        if (!property)
            return false;
        if (property.get_key() === 'InputMode')
            return property.get_label()?.get_text() === SCHEMA_NAME;
    }
}

export default class QuickHkExtension extends Extension {
    enable() {
        this._connections = [];
        this._originalStyle = null;
        this._appliedStyle = null;
        this._manager = IBusManager.getIBusManager();
        this._sources = Keyboard.getInputSourceManager();
        // GNOME 50 owns this actor for the lifetime of its IBus manager.
        this._popup = this._manager._candidatePopup;
        if (!this._popup?.add_style_class_name)
            throw new Error('YueKey: GNOME 50 candidate popup is unavailable');

        this._connect(this._sources, 'current-source-changed', () => this._sync());
        this._connect(this._manager, 'ready', (_manager, ready) => {
            if (ready)
                this._sync();
            else
                this._restore();
        });
        this._configFile = Gio.File.new_for_path(GLib.build_filenamev([
            GLib.get_user_config_dir(), 'quick-hk', 'presentation.json',
        ]));
        // Watching the directory also detects settings saved by atomic rename.
        try {
            this._monitor = this._configFile.get_parent().monitor_directory(
                Gio.FileMonitorFlags.NONE, null);
            this._connect(this._monitor, 'changed', (_monitor, file, otherFile) => {
                if (file?.equal(this._configFile) || otherFile?.equal(this._configFile))
                    this._sync();
            });
        } catch (error) {
            // Setup creates this directory. Styling still works with defaults
            // when the extension is installed independently.
            console.debug(`YueKey: settings monitor unavailable: ${error.message}`);
        }
        this._sync();
    }

    _connect(object, signal, callback) {
        this._connections.push([object, object.connect(signal, callback)]);
    }

    _readPresentation() {
        try {
            const [ok, bytes] = this._configFile.load_contents(null);
            if (ok) {
                const settings = JSON.parse(new TextDecoder().decode(bytes));
                return {
                    theme: settings.theme === 'dark' ? 'dark' : 'light',
                    fontSize: Number.isInteger(settings.font_size)
                        ? Math.max(10, Math.min(36, settings.font_size)) : 18,
                };
            }
        } catch (error) {
            if (!error.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.NOT_FOUND))
                console.debug(`YueKey: cannot read presentation settings: ${error.message}`);
        }
        return {theme: 'light', fontSize: 18};
    }

    _sync() {
        if (!isQuickHk(this._sources.currentSource)) {
            this._restore();
            return;
        }
        const {theme, fontSize} = this._readPresentation();
        this._popup.add_style_class_name('quick-hk');
        this._popup.remove_style_class_name(`quick-hk-${theme === 'dark' ? 'light' : 'dark'}`);
        this._popup.add_style_class_name(`quick-hk-${theme}`);
        if (this._appliedStyle === null)
            this._originalStyle = this._popup.get_style();
        this._appliedStyle = `${this._originalStyle ?? ''}; font-family: "Noto Sans CJK HK"; font-size: ${fontSize}pt;`;
        this._popup.set_style(this._appliedStyle);
    }

    _restore() {
        if (!this._popup)
            return;
        for (const styleClass of STYLE_CLASSES)
            this._popup.remove_style_class_name(styleClass);
        // Do not clobber a style set by another extension after ours.
        if (this._appliedStyle !== null && this._popup.get_style() === this._appliedStyle)
            this._popup.set_style(this._originalStyle);
        this._originalStyle = null;
        this._appliedStyle = null;
    }

    disable() {
        for (const [object, id] of this._connections ?? [])
            object.disconnect(id);
        this._connections = [];
        this._monitor?.cancel();
        this._monitor = null;
        this._restore();
        this._popup = null;
        this._sources = null;
        this._manager = null;
        this._configFile = null;
    }
}
