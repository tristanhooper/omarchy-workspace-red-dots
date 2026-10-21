import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "omarchy.workspaces"

  property var notificationWorkspaces: []
  property string dotPosition: "top-right"
  property string dotColor: "#ff4545"

  function loadConfig(raw) {
    root.dotPosition = "top-right"
    root.dotColor = "#ff4545"

    try {
      var config = JSON.parse(raw)
      var positions = ["top-left", "top-right", "bottom-left", "bottom-right", "center"]

      if (positions.indexOf(config.dotPosition) !== -1) {
        root.dotPosition = config.dotPosition
      } else if (config.dotPosition !== undefined) {
        console.warn("Workspace notification dots: invalid dotPosition; using top-right")
      }

      if (typeof config.dotColor === "string" && /^#[0-9a-fA-F]{6}$/.test(config.dotColor)) {
        root.dotColor = config.dotColor
      } else if (config.dotColor !== undefined) {
        console.warn("Workspace notification dots: dotColor must be a #RRGGBB hex value; using #ff4545")
      }
    } catch (error) {
      console.warn("Workspace notification dots: could not read config.json:", error)
    }
  }

  FileView {
    id: configFile
    path: Quickshell.env("HOME") + "/.config/omarchy/plugins/thooper.workspace-red-dots/config.json"
    watchChanges: true
    printErrors: false
    onLoaded: root.loadConfig(text())
    onFileChanged: reload()
  }

  Process {
    id: notificationWatcher
    command: ["python3", decodeURIComponent(Qt.resolvedUrl("workspace-notifications.py").toString().replace(/^file:\/\//, ""))]
    running: true
    stdout: SplitParser {
      onRead: function(line) {
        try { root.notificationWorkspaces = JSON.parse(line) }
        catch (error) { console.warn("Workspace notification dots:", error) }
      }
    }
    onExited: watcherRetry.start()
  }

  Timer {
    id: watcherRetry
    interval: 5000
    onTriggered: notificationWatcher.running = true
  }

  function workspaceById(id) {
    var values = Hyprland.workspaces.values
    for (var i = 0; i < values.length; i++) {
      if (values[i].id === id) return values[i]
    }

    return null
  }

  function workspaceIds() {
    var ids = [1, 2, 3, 4, 5, 6]
    var values = Hyprland.workspaces.values

    for (var i = 0; i < values.length; i++) {
      var id = values[i].id
      if (id > 0 && id <= 10 && ids.indexOf(id) === -1) ids.push(id)
    }

    ids.sort(function(left, right) { return left - right })
    return ids
  }

  function focusWorkspace(id) {
    if (!root.bar) return
    root.bar.run("hyprctl dispatch " + Util.shellQuote("hl.dsp.focus({ workspace = \"" + id + "\" })"))
  }

  readonly property real trailingGap: root.vertical ? 0 : Style.spaceReal(1.5)

  implicitWidth: grid.implicitWidth + trailingGap
  implicitHeight: grid.implicitHeight

  GridLayout {
    id: grid
    anchors.fill: parent
    anchors.rightMargin: root.trailingGap
    columns: root.vertical ? 1 : root.workspaceIds().length
    columnSpacing: root.vertical ? 0 : Style.space(1)
    rowSpacing: root.vertical ? Style.space(2) : 0

    Repeater {
      model: root.workspaceIds()

      WidgetButton {
        id: workspaceButton
        required property int modelData

        readonly property var workspace: root.workspaceById(modelData)
        readonly property bool occupied: workspace !== null && workspace.toplevels.values.length > 0
        readonly property bool focused: Hyprland.focusedWorkspace !== null && Hyprland.focusedWorkspace.id === modelData

        bar: root.bar
        text: focused ? "\uDB85\uDCFB" : (modelData === 10 ? "0" : String(modelData))
        opacity: occupied || focused || notificationDot.visible ? 1 : 0.5
        horizontalMargin: 6
        verticalPadding: 6
        fixedWidth: root.vertical ? root.barSize : Style.space(20)
        fixedHeight: root.barSize
        onPressed: function() { root.focusWorkspace(modelData) }

        Rectangle {
          id: notificationDot
          visible: root.notificationWorkspaces.indexOf(workspaceButton.modelData) !== -1
          width: 6
          height: 6
          radius: 3
          color: root.dotColor
          anchors.top: root.dotPosition === "top-left" || root.dotPosition === "top-right" ? parent.top : undefined
          anchors.bottom: root.dotPosition === "bottom-left" || root.dotPosition === "bottom-right" ? parent.bottom : undefined
          anchors.left: root.dotPosition === "top-left" || root.dotPosition === "bottom-left" ? parent.left : undefined
          anchors.right: root.dotPosition === "top-right" || root.dotPosition === "bottom-right" ? parent.right : undefined
          anchors.centerIn: root.dotPosition === "center" ? parent : undefined
          anchors.topMargin: 3
          anchors.bottomMargin: 3
          anchors.leftMargin: 1
          anchors.rightMargin: 1
        }
      }
    }
  }
}
