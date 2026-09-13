const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let code = fs.readFileSync(`${__dirname}/../dictation/quick-hk-dictation@quick-hk.local/dictation.js`, 'utf8')
    .replace(/^import .*;\n/gm, '').replace(/export /g, '');
code += '\nglobalThis.allowedTarget = allowedTarget;';
const context = {};
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
