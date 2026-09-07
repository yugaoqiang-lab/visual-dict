@echo off
REM 一键构建图解词典 APK（需本机已装 Android SDK 与 JDK17）
set JAVA_HOME=D:/Android/jdk17
set ANDROID_HOME=D:/Program Files/Android/Sdk
set PATH=%JAVA_HOME%\bin;%PATH%
REM 出正式 release 签名版（keystore 在 app/keystore/visualdict.jks，已配好签名）
"D:/Android/gradle-8.4/bin/gradle.bat" assembleRelease -x lintVitalRelease -x lintRelease
echo.
echo 构建完成，release 签名 APK 位于: app\build\outputs\apk\release\app-release.apk
echo 调试版可用: gradle assembleDebug
pause
