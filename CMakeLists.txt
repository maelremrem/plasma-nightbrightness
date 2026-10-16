cmake_minimum_required(VERSION 3.20)
project(plasma-nightbrightness VERSION 0.2.2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

find_package(ECM 6.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})
include(KDEInstallDirs)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(KDECMakeSettings)

find_package(Qt6 6.6 REQUIRED COMPONENTS Core Quick Qml Positioning)
find_package(KF6 6.0 REQUIRED COMPONENTS CoreAddons KCMUtils I18n)

add_executable(nightbrightness-geolocation tools/nightbrightness-geolocation.cpp)
target_link_libraries(nightbrightness-geolocation PRIVATE Qt6::Core Qt6::Positioning)
install(TARGETS nightbrightness-geolocation RUNTIME DESTINATION libexec)

kcmutils_add_qml_kcm(kcm_nightbrightness SOURCES
    src/nightbrightness.cpp
    src/nightbrightness.h
)
target_link_libraries(kcm_nightbrightness PRIVATE
    Qt6::Core
    Qt6::Quick
    KF6::CoreAddons
    KF6::KCMUtils
    KF6::KCMUtilsQuick
    KF6::I18n
)
