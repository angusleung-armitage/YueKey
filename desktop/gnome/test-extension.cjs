// SPDX-License-Identifier: MIT
// Isolated behavior checks. Native Shell/app integration still needs desktop QA.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let code = fs.readFileSync(path.join(__dirname, 'quick-hk@quick-hk.local/extension.js'), 'utf8')
    .replace(/^import .*;\n/gm, '').replace('export default class QuickHkExtension', 'class QuickHkExtension');
code += '\nglobalThis.QuickHkExtension = QuickHkExtension;';
class SignalEmitter {
    connections = new Map(); next = 1;
    connect(name, callback) { const id = this.next++; this.connections.set(id, [name,callback]); return id; }
    disconnect(id) { assert(this.connections.delete(id)); }
    emit(name,...args) { for (const [signal,cb] of [...this.connections.values()]) if (name === signal) cb(this,...args); }
}
const popup = {classes: new Set(['candidate-popup-boxpointer']), style: 'color: red;',
    add_style_class_name(c){this.classes.add(c)}, remove_style_class_name(c){this.classes.delete(c)},
    get_style(){return this.style}, set_style(s){this.style=s}};
const sources = new SignalEmitter();
const manager = new SignalEmitter();manager._candidatePopup=popup;
let monitor;
let presentation = {theme:'light',font_size:18};
const configFile = {load_contents:()=>[true,new TextEncoder().encode(JSON.stringify(presentation))],
    equal(other){return other === this},get_parent(){return {monitor_directory:()=>{monitor = new SignalEmitter();monitor.cancel=()=>{monitor.cancelled=true};return monitor}}}};
function source(label, id='rime', type='ibus') { return {type,id,properties:{get(i){return i === 0 ? {get_key:()=> 'InputMode', get_label:()=>({get_text:()=>label})}:null}}}; }
sources.currentSource = source('港式速成');
const context = {DictationUI:class{setEnabled(){}invalidate(){}destroy(){}},Extension:class{},TextDecoder,console,Gio:{File:{new_for_path:()=>configFile},FileMonitorFlags:{NONE:0},IOErrorEnum:{NOT_FOUND:1}},
    GLib:{build_filenamev:parts=>parts.join('/'),get_user_config_dir:()=>'/tmp/config'},IBusManager:{getIBusManager:()=>manager},Keyboard:{getInputSourceManager:()=>sources}};
vm.createContext(context);vm.runInContext(code,context);
const ext = new context.QuickHkExtension();
ext.enable();
assert(popup.classes.has('quick-hk-light'));assert(popup.style.includes('font-size: 18pt'));
sources.currentSource = source('倉頡');sources.emit('current-source-changed');
assert(!popup.classes.has('quick-hk'));assert.equal(popup.style,'color: red;');
for (const other of [source('Abc'), source('港式速成','other'),source('港式速成','rime','xkb'),null]) {
    sources.currentSource = other;sources.emit('current-source-changed');assert(!popup.classes.has('quick-hk'));
}
sources.currentSource = source('港式速成');sources.emit('current-source-changed');
presentation={theme:'dark',font_size:1000};monitor.emit('changed',configFile,null);
assert(popup.classes.has('quick-hk-dark'));assert(!popup.classes.has('quick-hk-light'));assert(popup.style.includes('36pt'));
manager.emit('ready',false);assert(!popup.classes.has('quick-hk'));assert.equal(popup.style,'color: red;');
manager.emit('ready',true);assert(popup.classes.has('quick-hk'));
ext.disable();assert.equal(manager.connections.size,0);assert.equal(sources.connections.size,0);assert.equal(monitor.connections.size,0);assert(monitor.cancelled);
assert.deepEqual([...popup.classes],['candidate-popup-boxpointer']);assert.equal(popup.style,'color: red;');
ext.enable();popup.style='font-family: Other;';ext.disable();assert.equal(popup.style,'font-family: Other;');
ext.enable();ext.disable();assert.equal(popup.style,'font-family: Other;');
console.log('PASS GNOME schema scoping, style changes, settings clamp, IBus readiness, disable/re-enable cleanup, preserving later external styles');
