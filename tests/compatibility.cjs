const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict'), path = require('node:path')
const context = vm.createContext({})
vm.runInContext(fs.readFileSync(path.join(__dirname, '../WorkspaceLogic.js'), 'utf8').replace(/^\.pragma.*$/mg, ''), context)
const plain = value => JSON.parse(JSON.stringify(value))
const blocks = context.readBlocks('0\tDP-1\tfirst\n1\tHDMI-A-1\tsecond\nbad\tbad\tx\n')
assert.deepEqual(plain(blocks), {'DP-1':0, 'HDMI-A-1':1})
assert.equal(context.blockFor(blocks,'HDMI-A-1',12),1)
assert.equal(context.blockFor({},'DP-2',23),2)
const workspaces = [
  {id:2,monitor:{name:'DP-1'}}, {id:12,monitor:{name:'HDMI-A-1'}},
  {id:19,monitor:{name:'HDMI-A-1'}}, {id:23,monitor:{name:'HDMI-A-1'}}, {id:-99}
]
assert.deepEqual(plain(context.workspaceIds(workspaces,false,0,'DP-1')),[1,2,3,4,5,6])
assert.deepEqual(plain(context.workspaceIds(workspaces,true,1,'HDMI-A-1')),[11,12,13,14,15,16,19,23])
assert.equal(context.slotOf(12),2)
assert.equal(context.slotOf(20),10)
assert.equal(context.focusCommand(12,true,1,'HDMI-A-1'),'o.workspaces.focus(2, "HDMI-A-1")')
assert.equal(context.focusCommand(23,true,1,'HDMI-A-1'),'hl.dsp.focus({ workspace = "23" })')
assert.equal(context.focusCommand(2,false,0,'DP-1'),'hl.dsp.focus({ workspace = "2" })')
console.log('Workspace compatibility checks passed')
