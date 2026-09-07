@echo off
chcp 65001 >nul
REM ============================================================
REM  科莱德图解词典 - Windows exe 一键打包
REM  使用前提（在你自己电脑、能联网的命令行里执行一次）：
REM      pip install pywebview pyinstaller
REM  然后把本文件放到 visual-dict 目录，双击即可。
REM  说明：app.py 负责加载 index2.html，pages/ 是词典图片。
REM        改了 index2.html / home.html / search.html / words.js 或 pages/ 后，重跑本脚本即可。
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/2] 打包「文件夹版」(推荐，启动快，含 VisualDict 文件夹)
pyinstaller --noconfirm --windowed --name VisualDict --icon=app.ico --hidden-import webview --add-data "index2.html;." --add-data "home.html;." --add-data "search.html;." --add-data "words.js;." --add-data "pages;pages" app.py

REM [2/2] 如需「单个 exe 文件」版(启动略慢、体积相近)：
REM       把下面这行前面的 REM 删掉，并把上面那行前面加 REM 注释掉
REM pyinstaller --noconfirm --windowed --onefile --name VisualDict --icon=app.ico --hidden-import webview --add-data "index2.html;." --add-data "home.html;." --add-data "search.html;." --add-data "words.js;." --add-data "pages;pages" app.py

echo.
echo 完成，输出在 dist\ 目录
pause
