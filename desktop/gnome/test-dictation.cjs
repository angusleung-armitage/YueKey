const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let code = fs.readFileSync(`${__dirname}/../dictation/quick-hk-dictation@quick-hk.local/dictation.js`, 'utf8')
    .replace(/^import .*;\n/gm, '').replace(/export /g, '');
code += '\nglobalThis.allowedTarget = allowedTarget; globalThis.indicatorPosition = indicatorPosition; globalThis.DictationUI = DictationUI;';
const context = {Atspi: {StateType: {FOCUSED: 1, SHOWING: 2}, Role: {PASSWORD_TEXT: 3}, CoordType: {WINDOW: 1}},
    St: {ThemeContext: {get_for_stage: () => ({scale_factor: 2})}}, global: {stage: {}}};
vm.createContext(context); vm.runInContext(code, context);
const allowed = context.allowedTarget;
assert(allowed(true, true, false, 1, 0, 0));
for (const args of [[false,true,false,1,0,0], [true,false,false,1,0,0],
    [true,true,true,1,0,0], [true,true,false,null,0,0],
    [true,true,false,1,8,0], [true,true,false,1,9,0],
    [true,true,false,1,0,2048], [true,true,false,1,0,4096],
    [true,true,false,1,null,0], [true,true,false,1,undefined,0]])
    assert(!allowed(...args));
console.log('PASS dictation disabled, other schema, lock, no window, password, PIN, private/hidden text');

const place = (...args) => Array.from(context.indicatorPosition(...args));
const area = {x: 0, y: 0, width: 1920, height: 1040};
assert.deepEqual(place({x: 400, y: 300, width: 1, height: 20}, area, 64, 24), [368, 326]);
assert.deepEqual(place({x: 1900, y: 1020, width: 1, height: 20}, area, 64, 24), [1850, 990]);
assert.deepEqual(place({x: -1300, y: -100, width: 1, height: 20},
    {x: -1920, y: -200, width: 1920, height: 1080}, 64, 24), [-1332, -74]);
assert.deepEqual(place({x: -4000, y: -4000, width: 1, height: 20}, area, 64, 24), [6, 6]);
assert.deepEqual(place({x: 400, y: 300, width: 600, height: 32}, area, 64, 24), [374, 338]);
console.log('PASS caret placement, bottom/right edge, negative monitor coordinates, off-screen clamp');

// Empty fields may reject GetCharacterExtents(0). Their component bounds must
// still anchor the badge, and another process/field must not supply geometry.
let queried = 0;
const source = {get_state_set: () => ({contains: () => true}), get_role: () => 61,
    get_process_id: () => 42,
    get_text_iface: () => ({get_caret_offset: () => 0, get_character_extents: () => {throw Error('empty')}}),
    get_component_iface: () => ({get_extents: () => {queried++; return {x: 5, y: 10, width: 200, height: 30}}})};
const window = {get_id: () => 1, get_pid: () => 42, get_client_content_rect: () => ({x: -1000, y: 50})};
const ui = Object.create(context.DictationUI.prototype);
ui._accessible = {source, window: 1};
assert.deepEqual(JSON.parse(JSON.stringify(ui._accessibleCursor(window))),
    {x: -990, y: 70, width: 400, height: 60, window: 1});
assert.equal(queried, 1);
for (const wrong of [{...window, get_id: () => 2}, {...window, get_pid: () => 43}])
    assert.equal(ui._accessibleCursor(wrong), null);
source.get_role = () => 3;
assert.equal(ui._accessibleCursor(window), null);
assert.equal(queried, 1);
console.log('PASS empty accessible field fallback, scaling, wrong window/process and password exclusion');
