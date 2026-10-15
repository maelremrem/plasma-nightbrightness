import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import QtLocation
import QtPositioning
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCMUtils

KCMUtils.SimpleKCM {
    id: root

    property string locationStatus: ""
    property double clockTick: Date.now()

    Timer { interval: 60000; repeat: true; running: true; onTriggered: root.clockTick = Date.now() }

    function solarPreview() {
        var refresh = root.clockTick
        if (!kcm.values.sun_location_set) return "Choisissez votre emplacement."
        var now = new Date()
        var year = now.getFullYear(), month = now.getMonth(), date = now.getDate()
        var n = Math.round((Date.UTC(year, month, date) - Date.UTC(year, 0, 0)) / 86400000)
        var days = new Date(year, 1, 29).getMonth() === 1 ? 366 : 365
        var angle = 2 * Math.PI / days * (n - 1)
        var eot = 229.18 * (0.000075 + 0.001868*Math.cos(angle)
            -0.032077*Math.sin(angle) -0.014615*Math.cos(2*angle)
            -0.040849*Math.sin(2*angle))
        var decl = 0.006918 -0.399912*Math.cos(angle) +0.070257*Math.sin(angle)
            -0.006758*Math.cos(2*angle)+0.000907*Math.sin(2*angle)
            -0.002697*Math.cos(3*angle)+0.00148*Math.sin(3*angle)
        var lat = Number(kcm.values.latitude) * Math.PI / 180
        var denominator = Math.cos(lat) * Math.cos(decl)
        if (Math.abs(denominator) < 1e-8) return "Soleil polaire : pas de lever/coucher aujourd'hui."
        var cosH = Math.cos(90.833*Math.PI/180)/denominator-Math.tan(lat)*Math.tan(decl)
        if (cosH < -1 || cosH > 1) return "Pas de lever ou de coucher aujourd'hui (zone polaire)."
        var hour = Math.acos(cosH) * 180 / Math.PI
        var offset = -new Date(year, month, date, 12).getTimezoneOffset()
        function fmt(minutes) {
            var m = Math.round((minutes % 1440 + 1440) % 1440)
            return String(Math.floor(m/60)).padStart(2,"0") + ":" + String(m%60).padStart(2,"0")
        }
        var base = 720 - 4*Number(kcm.values.longitude) - eot + offset
        return "Lever : " + fmt(base-4*hour) + "    •    Coucher : " + fmt(base+4*hour)
    }

    Plugin { id: osmPlugin; name: "osm" }

    Controls.Dialog {
        id: mapDialog
        parent: Controls.Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(650, parent ? parent.width - 30 : 650)
        height: Math.min(470, parent ? parent.height - 30 : 470)
        modal: true
        title: "Choisir la position sur la carte"
        standardButtons: Controls.Dialog.Close
        ColumnLayout {
            anchors.fill: parent
            Controls.Label {
                text: "Cliquez sur la carte pour placer le repère (position manuelle)."
                wrapMode: Text.WordWrap
            }
            Map {
                id: worldMap
                Layout.fillWidth: true
                Layout.fillHeight: true
                plugin: osmPlugin
                center: QtPositioning.coordinate(Number(kcm.values.latitude), Number(kcm.values.longitude))
                zoomLevel: 2
                MapQuickItem {
                    coordinate: QtPositioning.coordinate(Number(kcm.values.latitude), Number(kcm.values.longitude))
                    anchorPoint.x: 7
                    anchorPoint.y: 7
                    sourceItem: Rectangle {
                        width: 14; height: 14; radius: 7
                        color: "#eb762b"; border.color: "white"; border.width: 2
                    }
                }
                TapHandler {
                    onTapped: function(point) {
                        var pos = worldMap.toCoordinate(point.position, false)
                        if (!pos.isValid) return
                        kcm.updateValue("latitude", Math.round(pos.latitude * 1000000)/1000000)
                        kcm.updateValue("longitude", Math.round(pos.longitude * 1000000)/1000000)
                        kcm.updateValue("sun_location_set", true)
                        kcm.updateValue("location_auto", false)
                        root.locationStatus = "Position choisie sur la carte. Cliquez sur Appliquer."
                    }
                }
                DragHandler {
                    target: null
                    onTranslationChanged: function(delta) { worldMap.pan(-delta.x, -delta.y) }
                }
            }
            Controls.Label {
                text: worldMap.errorString ? "Carte : " + worldMap.errorString :
                      "Fond de carte © OpenStreetMap ; une connexion Internet est nécessaire."
                wrapMode: Text.WordWrap
            }
        }
    }

    function modeIndex(mode) {
        return ["fixed", "sun", "follow", "always"].indexOf(mode)
    }

    function minutes(value) {
        var parts = value.split(":")
        return Number(parts[0]) * 60 + Number(parts[1])
    }

    function nightFactor(minute) {
        var morning = minutes(kcm.values.morning_time)
        var evening = minutes(kcm.values.evening_time)
        var duration = kcm.values.transition_minutes
        var latest = -Infinity
        var toNight = false
        for (var shift = -2; shift <= 1; ++shift) {
            var events = [{time: morning + shift * 1440, night: false},
                          {time: evening + shift * 1440, night: true}]
            for (var n = 0; n < events.length; ++n) {
                if (events[n].time <= minute && events[n].time > latest) {
                    latest = events[n].time
                    toNight = events[n].night
                }
            }
        }
        var progress = duration === 0 ? 1 : Math.min(1, (minute - latest) / duration)
        return toNight ? progress : 1 - progress
    }

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: Kirigami.Units.largeSpacing * 1.5

        Controls.Label {
            Layout.fillWidth: true
            text: "Adaptez automatiquement la luminosité de votre écran selon l'heure."
            wrapMode: Text.WordWrap
        }

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.Switch {
                Kirigami.FormData.label: "Luminosité automatique :"
                text: checked ? "Activée" : "Désactivée"
                checked: kcm.values.enabled
                onToggled: kcm.updateValue("enabled", checked)
            }

            RowLayout {
                Kirigami.FormData.label: "Luminosité de jour :"
                enabled: kcm.values.enabled
                Controls.Slider {
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 17
                    from: 5
                    to: 100
                    stepSize: 1
                    value: kcm.values.day_brightness
                    onMoved: kcm.updateValue("day_brightness", Math.round(value))
                }
                Controls.Label {
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 3
                    horizontalAlignment: Text.AlignRight
                    text: kcm.values.day_brightness + " %"
                }
            }

            RowLayout {
                Kirigami.FormData.label: "Luminosité de nuit :"
                enabled: kcm.values.enabled
                Controls.Slider {
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 17
                    from: 5
                    to: 100
                    stepSize: 1
                    value: kcm.values.night_brightness
                    onMoved: kcm.updateValue("night_brightness", Math.round(value))
                }
                Controls.Label {
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 3
                    horizontalAlignment: Text.AlignRight
                    text: kcm.values.night_brightness + " %"
                }
            }

            Controls.ComboBox {
                id: schedule
                Kirigami.FormData.label: "Heures d'activation :"
                enabled: kcm.values.enabled
                Layout.preferredWidth: Kirigami.Units.gridUnit * 22
                model: [
                    "Heures personnalisées",
                    "Lever et coucher du soleil",
                    "Suivre Lumière nocturne de KDE",
                    "Toujours en mode nuit"
                ]
                currentIndex: root.modeIndex(kcm.values.schedule_mode)
                onActivated: function(index) { kcm.updateValue("schedule_mode", ["fixed", "sun", "follow", "always"][index]) }
            }

            RowLayout {
                Kirigami.FormData.label: "Début de journée :"
                visible: kcm.values.schedule_mode === "fixed"
                enabled: kcm.values.enabled
                Controls.TextField {
                    id: morningField
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                    text: kcm.values.morning_time
                    placeholderText: "08:00"
                    inputMask: "99:99"
                    validator: RegularExpressionValidator { regularExpression: /^([01]\d|2[0-3]):[0-5]\d$/ }
                    onEditingFinished: {
                        if (acceptableInput) kcm.updateValue("morning_time", text)
                    }
                }
                Controls.Label { text: "HH:MM"; opacity: 0.6 }
            }

            RowLayout {
                Kirigami.FormData.label: "Début de nuit :"
                visible: kcm.values.schedule_mode === "fixed"
                enabled: kcm.values.enabled
                Controls.TextField {
                    id: eveningField
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                    text: kcm.values.evening_time
                    placeholderText: "20:00"
                    inputMask: "99:99"
                    validator: RegularExpressionValidator { regularExpression: /^([01]\d|2[0-3]):[0-5]\d$/ }
                    onEditingFinished: {
                        if (acceptableInput) kcm.updateValue("evening_time", text)
                    }
                }
                Controls.Label { text: "HH:MM"; opacity: 0.6 }
            }

            RowLayout {
                Kirigami.FormData.label: "Coordonnées GPS :"
                visible: kcm.values.schedule_mode === "sun"
                enabled: kcm.values.enabled
                Controls.TextField {
                    id: latitudeField
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                    text: String(kcm.values.latitude)
                    placeholderText: "Latitude"
                    validator: DoubleValidator { bottom: -90; top: 90; decimals: 6; locale: "C" }
                }
                Controls.TextField {
                    id: longitudeField
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                    text: String(kcm.values.longitude)
                    placeholderText: "Longitude"
                    validator: DoubleValidator { bottom: -180; top: 180; decimals: 6; locale: "C" }
                }
                Controls.Button {
                    text: "Valider"
                    enabled: latitudeField.acceptableInput && longitudeField.acceptableInput
                    onClicked: {
                        kcm.updateValue("latitude", Number(latitudeField.text))
                        kcm.updateValue("longitude", Number(longitudeField.text))
                        kcm.updateValue("sun_location_set", true)
                    }
                }
            }

            RowLayout {
                Kirigami.FormData.label: "Carte :"
                visible: kcm.values.schedule_mode === "sun"
                Controls.Button {
                    text: "Choisir sur la carte…"
                    icon.name: "map-globe"
                    onClicked: mapDialog.open()
                }
            }

            Controls.Switch {
                Kirigami.FormData.label: "Localisation automatique :"
                visible: kcm.values.schedule_mode === "sun"
                text: checked ? "Activée (GeoClue2)" : "Désactivée"
                checked: kcm.values.location_auto
                onToggled: kcm.updateValue("location_auto", checked)
            }

            Controls.SpinBox {
                Kirigami.FormData.label: "Actualiser toutes les :"
                visible: kcm.values.schedule_mode === "sun" && kcm.values.location_auto
                from: 1; to: 24; value: kcm.values.location_refresh_hours
                editable: true
                onValueModified: kcm.updateValue("location_refresh_hours", value)
                textFromValue: function(value) { return value + " h" }
                valueFromText: function(text) { return Number(text.replace(/[^0-9]/g, "")) }
            }

            Controls.Label {
                Kirigami.FormData.label: "Aujourd'hui :"
                visible: kcm.values.schedule_mode === "sun"
                text: root.solarPreview()
                font.bold: true
            }

            Controls.Label {
                Kirigami.FormData.label: ""
                visible: kcm.values.schedule_mode === "sun" && kcm.values.location_auto
                text: kcm.values.location_updated_at > 0
                    ? "Dernière mise à jour : " + new Date(kcm.values.location_updated_at * 1000).toLocaleString(Qt.locale())
                    : "En attente de la première mise à jour par le service."
                wrapMode: Text.WordWrap
                opacity: 0.7
            }

            Controls.Label {
                Kirigami.FormData.label: ""
                visible: kcm.values.schedule_mode === "sun"
                text: kcm.values.sun_location_set ? "Horaires solaires calculés localement." : "Renseignez vos coordonnées puis cliquez sur Valider."
                wrapMode: Text.WordWrap
                opacity: 0.7
            }

            Controls.Label {
                Kirigami.FormData.label: ""
                visible: kcm.values.schedule_mode === "follow"
                Layout.preferredWidth: Kirigami.Units.gridUnit * 23
                text: "Reprend les périodes de jour et de nuit de KDE. Nécessite que « Lumière nocturne » soit activée."
                wrapMode: Text.WordWrap
                opacity: 0.7
            }

            Controls.SpinBox {
                Kirigami.FormData.label: "Durée de transition :"
                enabled: kcm.values.enabled
                from: 0
                to: 120
                stepSize: 5
                editable: true
                value: kcm.values.transition_minutes
                onValueModified: kcm.updateValue("transition_minutes", value)
                textFromValue: function(value) { return value + " min" }
                valueFromText: function(text) { return Number(text.replace(/[^0-9]/g, "")) }
            }

            Controls.SpinBox {
                Kirigami.FormData.label: "Pause après réglage manuel :"
                enabled: kcm.values.enabled
                from: 0
                to: 240
                stepSize: 15
                editable: true
                value: kcm.values.manual_pause_minutes
                onValueModified: kcm.updateValue("manual_pause_minutes", value)
                textFromValue: function(value) { return value + " min" }
                valueFromText: function(text) { return Number(text.replace(/[^0-9]/g, "")) }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Controls.Label {
                text: "Aperçu de la journée"
                font.bold: true
            }

            Canvas {
                id: timeline
                Layout.fillWidth: true
                Layout.preferredHeight: Kirigami.Units.gridUnit * 4
                visible: kcm.values.schedule_mode === "fixed"
                onWidthChanged: requestPaint()
                onPaint: {
                    var c = getContext("2d")
                    c.clearRect(0, 0, width, height)
                    var left = 12
                    var barWidth = Math.max(1, width - left * 2)
                    var top = 6
                    var barHeight = 23
                    for (var i = 0; i < 144; ++i) {
                        var factor = root.nightFactor(i * 10)
                        c.fillStyle = Qt.rgba(0.95 - factor * 0.25, 0.85 - factor * 0.18,
                                              0.60 + factor * 0.23, 1)
                        c.fillRect(left + i * barWidth / 144, top, barWidth / 144 + 1, barHeight)
                    }
                    c.fillStyle = Kirigami.Theme.textColor
                    c.font = "11px sans-serif"
                    for (var h = 0; h <= 24; h += 2) {
                        var x = left + h / 24 * barWidth
                        c.fillRect(x, top + barHeight + 3, 1, 5)
                        c.fillText(String(h), x - (h === 0 ? 0 : 6), top + barHeight + 19)
                    }
                }
                Connections {
                    target: kcm
                    function onValuesChanged() { timeline.requestPaint() }
                }
            }

            Controls.Label {
                visible: kcm.values.schedule_mode !== "fixed"
                text: kcm.values.schedule_mode === "follow"
                      ? "Les heures seront celles de Lumière nocturne."
                      : kcm.values.schedule_mode === "sun"
                        ? "Les horaires évoluent automatiquement avec les saisons."
                        : "La luminosité nocturne reste constante."
                opacity: 0.7
                wrapMode: Text.WordWrap
            }
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: true
            type: Kirigami.MessageType.Information
            text: "Utilise le contrôle natif de Plasma pour « display0 ». Cliquez sur Appliquer pour enregistrer."
        }
    }
}
