#include "nightbrightness.h"

#include <KPluginFactory>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QSaveFile>
#include <QStandardPaths>
#include <QDebug>

K_PLUGIN_CLASS_WITH_JSON(NightBrightness, "kcm_nightbrightness.json")

NightBrightness::NightBrightness(QObject *parent, const KPluginMetaData &metadata)
    : KQuickConfigModule(parent, metadata)
{
    setButtons(Apply | Default);
    load();
}

QVariantMap NightBrightness::defaultValues()
{
    return {
        {QStringLiteral("enabled"), false},
        {QStringLiteral("day_brightness"), 70},
        {QStringLiteral("night_brightness"), 25},
        {QStringLiteral("schedule_mode"), QStringLiteral("fixed")},
        {QStringLiteral("morning_time"), QStringLiteral("08:00")},
        {QStringLiteral("evening_time"), QStringLiteral("20:00")},
        {QStringLiteral("transition_minutes"), 30},
        {QStringLiteral("manual_pause_minutes"), 60},
        {QStringLiteral("latitude"), 0.0},
        {QStringLiteral("longitude"), 0.0},
        {QStringLiteral("sun_location_set"), false},
        {QStringLiteral("location_auto"), false},
        {QStringLiteral("location_refresh_hours"), 6},
        {QStringLiteral("location_updated_at"), 0},
        {QStringLiteral("display_id"), QStringLiteral("display0")},
    };
}

static QString validTime(const QVariant &value, const QString &fallback)
{
    const QString time = value.toString();
    static const QRegularExpression regex(QStringLiteral("^([01]\\d|2[0-3]):[0-5]\\d$"));
    return regex.match(time).hasMatch() ? time : fallback;
}

QVariantMap NightBrightness::normalized(const QVariantMap &incoming)
{
    QVariantMap data = defaultValues();
    for (auto it = incoming.cbegin(); it != incoming.cend(); ++it) {
        if (data.contains(it.key())) {
            data[it.key()] = it.value();
        }
    }
    data[QStringLiteral("enabled")] = data.value(QStringLiteral("enabled")).toBool();
    data[QStringLiteral("sun_location_set")] = data.value(QStringLiteral("sun_location_set")).toBool();
    data[QStringLiteral("location_auto")] = data.value(QStringLiteral("location_auto")).toBool();
    data[QStringLiteral("location_refresh_hours")] = qBound(1, data.value(QStringLiteral("location_refresh_hours")).toInt(), 24);
    data[QStringLiteral("location_updated_at")] = qMax(0LL, data.value(QStringLiteral("location_updated_at")).toLongLong());
    for (const QString &key : {QStringLiteral("day_brightness"), QStringLiteral("night_brightness")}) {
        data[key] = qBound(5, data.value(key).toInt(), 100);
    }
    data[QStringLiteral("transition_minutes")] = qBound(0, data.value(QStringLiteral("transition_minutes")).toInt(), 120);
    data[QStringLiteral("manual_pause_minutes")] = qBound(0, data.value(QStringLiteral("manual_pause_minutes")).toInt(), 240);
    data[QStringLiteral("latitude")] = qBound(-90.0, data.value(QStringLiteral("latitude")).toDouble(), 90.0);
    data[QStringLiteral("longitude")] = qBound(-180.0, data.value(QStringLiteral("longitude")).toDouble(), 180.0);
    data[QStringLiteral("morning_time")] = validTime(data.value(QStringLiteral("morning_time")), QStringLiteral("08:00"));
    data[QStringLiteral("evening_time")] = validTime(data.value(QStringLiteral("evening_time")), QStringLiteral("20:00"));
    const QString mode = data.value(QStringLiteral("schedule_mode")).toString();
    if (mode != QLatin1String("fixed") && mode != QLatin1String("sun")
        && mode != QLatin1String("follow") && mode != QLatin1String("always")) {
        data[QStringLiteral("schedule_mode")] = QStringLiteral("fixed");
    }
    const QString display = data.value(QStringLiteral("display_id")).toString();
    static const QRegularExpression displayRegex(QStringLiteral("^display[0-9]+$"));
    if (!displayRegex.match(display).hasMatch()) {
        data[QStringLiteral("display_id")] = QStringLiteral("display0");
    }
    return data;
}

QString NightBrightness::configFilePath()
{
    return QStandardPaths::writableLocation(QStandardPaths::ConfigLocation) + QStringLiteral("/nightbrightness.json");
}

QVariantMap NightBrightness::values() const
{
    return m_values;
}

void NightBrightness::updateValue(const QString &key, const QVariant &value)
{
    if (!defaultValues().contains(key)) {
        return;
    }
    QVariantMap next = m_values;
    next.insert(key, value);
    next = normalized(next);
    if (next == m_values) {
        return;
    }
    m_values = next;
    Q_EMIT valuesChanged();
    setNeedsSave(m_values != m_saved);
}

void NightBrightness::load()
{
    QVariantMap data;
    QFile file(configFilePath());
    if (file.open(QIODevice::ReadOnly)) {
        const QJsonDocument document = QJsonDocument::fromJson(file.readAll());
        if (document.isObject()) {
            data = document.object().toVariantMap();
        }
    }
    m_saved = normalized(data);
    m_values = m_saved;
    Q_EMIT valuesChanged();
    setNeedsSave(false);
}

void NightBrightness::save()
{
    const QString path = configFilePath();
    if (!QDir().mkpath(QFileInfo(path).absolutePath())) {
        qWarning() << "Could not create configuration directory:" << path;
        return;
    }
    QSaveFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "Could not open configuration:" << path << file.errorString();
        return;
    }
    file.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
    const QJsonDocument document(QJsonObject::fromVariantMap(m_values));
    if (file.write(document.toJson(QJsonDocument::Indented)) < 0 || !file.commit()) {
        qWarning() << "Could not save configuration:" << path << file.errorString();
        return;
    }
    m_saved = m_values;
    setNeedsSave(false);
}

void NightBrightness::defaults()
{
    m_values = defaultValues();
    Q_EMIT valuesChanged();
    setNeedsSave(m_values != m_saved);
}


#include "nightbrightness.moc"
