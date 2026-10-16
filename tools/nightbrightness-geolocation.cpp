#include <QCoreApplication>
#include <QGeoCoordinate>
#include <QGeoPositionInfo>
#include <QGeoPositionInfoSource>
#include <QTimer>
#include <QTextStream>
#include <QVariantMap>

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    QVariantMap params;
    params.insert(QStringLiteral("desktopId"), QStringLiteral("kcm_nightbrightness"));
    auto *source = QGeoPositionInfoSource::createSource(QStringLiteral("geoclue2"), params, &app);
    if (!source) {
        QTextStream(stderr) << "GeoClue2 positioning plugin unavailable\n";
        return 2;
    }
    bool positionDelivered = false;
    QObject::connect(source, &QGeoPositionInfoSource::positionUpdated, &app,
                     [&](const QGeoPositionInfo &info) {
        if (positionDelivered) return;
        const auto c = info.coordinate();
        if (!c.isValid()) return;
        positionDelivered = true;
        QTextStream output(stdout);
        output << QString::number(c.latitude(), 'f', 6) << " "
               << QString::number(c.longitude(), 'f', 6) << Qt::endl;
        app.exit(0);
    });
    QObject::connect(source, &QGeoPositionInfoSource::errorOccurred, &app,
                     [&](QGeoPositionInfoSource::Error) { app.exit(2); });
    QTimer::singleShot(18000, &app, [&] { app.exit(2); });
    source->requestUpdate(15000);
    return app.exec();
}
