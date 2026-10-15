#pragma once

#include <KQuickConfigModule>
#include <QVariantMap>

class NightBrightness : public KQuickConfigModule
{
    Q_OBJECT
    Q_PROPERTY(QVariantMap values READ values NOTIFY valuesChanged)

public:
    NightBrightness(QObject *parent, const KPluginMetaData &metadata);
    QVariantMap values() const;
    Q_INVOKABLE void updateValue(const QString &key, const QVariant &value);

    void load() override;
    void save() override;
    void defaults() override;

Q_SIGNALS:
    void valuesChanged();

private:
    static QVariantMap defaultValues();
    static QVariantMap normalized(const QVariantMap &values);
    static QString configFilePath();

    QVariantMap m_values;
    QVariantMap m_saved;
};
