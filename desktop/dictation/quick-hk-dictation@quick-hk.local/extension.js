// SPDX-License-Identifier: MIT
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Keyboard from 'resource:///org/gnome/shell/ui/status/keyboard.js';
import {DictationUI} from './dictation.js';

export default class QuickHkDictationExtension extends Extension {
    enable() {
        this._sources = Keyboard.getInputSourceManager();
        this._ui = new DictationUI(() => {
            const source = this._sources.currentSource;
            if (source?.type !== 'ibus' || source.id !== 'rime' || !source.properties)
                return false;
            for (let i = 0; ; i++) {
                const property = source.properties.get(i);
                if (!property)
                    return false;
                if (property.get_key() === 'InputMode')
                    return property.get_label()?.get_text() === '港式速成';
            }
        }, this.path);
        this._sourceSignal = this._sources.connect('current-source-changed', () => this._ui.invalidate());
        this._file = Gio.File.new_for_path(GLib.build_filenamev([
            GLib.get_user_config_dir(), 'quick-hk', 'presentation.json']));
        this._monitor = this._file.get_parent().monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitorSignal = this._monitor.connect('changed', (_monitor, file, other) => {
            if (file?.equal(this._file) || other?.equal(this._file))
                this._sync();
        });
        this._sync();
    }

    _sync() {
        try {
            const [ok, bytes] = this._file.load_contents(null);
            this._ui.setEnabled(ok && JSON.parse(new TextDecoder().decode(bytes)).dictation_enabled === true);
        } catch {
            this._ui.setEnabled(false);
        }
    }

    disable() {
        if (this._sourceSignal)
            this._sources.disconnect(this._sourceSignal);
        if (this._monitorSignal)
            this._monitor.disconnect(this._monitorSignal);
        this._monitor?.cancel();
        this._ui?.destroy();
        this._sourceSignal = this._monitorSignal = 0;
        this._sources = this._monitor = this._ui = null;
    }
}
