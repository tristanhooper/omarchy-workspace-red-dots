.pragma library

function readBlocks(text) {
  var blocks = {}
  var lines = String(text || "").split("\n")
  for (var i = 0; i < lines.length; i++) {
    var fields = lines[i].split("\t")
    if (fields.length >= 3 && /^\d+$/.test(fields[0]) && fields[1])
      blocks[fields[1]] = Number(fields[0])
  }
  return blocks
}

function blockOf(id) { return Math.floor((id - 1) / 10) }
function slotOf(id) { return (id - 1) % 10 + 1 }

function blockFor(blocks, monitorName, activeId) {
  if (blocks[monitorName] !== undefined) return blocks[monitorName]
  return activeId > 0 ? blockOf(activeId) : 0
}

function workspaceIds(values, modern, block, monitorName) {
  var base = modern ? block * 10 : 0
  var ids = [base + 1, base + 2, base + 3, base + 4, base + 5, base + 6]
  var guests = []
  for (var i = 0; i < values.length; i++) {
    var workspace = values[i], id = workspace.id
    if (id <= 0) continue
    if ((!modern && id <= 10) || (modern && blockOf(id) === block)) {
      if (ids.indexOf(id) === -1) ids.push(id)
    } else if (modern && workspace.monitor && workspace.monitor.name === monitorName) {
      guests.push(id)
    }
  }
  ids.sort(function(a, b) { return a - b })
  guests.sort(function(a, b) { return a - b })
  return ids.concat(guests)
}

function focusCommand(id, modern, block, monitorName) {
  if (modern && blockOf(id) === block)
    return "o.workspaces.focus(" + slotOf(id) + ", " + JSON.stringify(monitorName) + ")"
  return 'hl.dsp.focus({ workspace = "' + id + '" })'
}
