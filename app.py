import webview
import os
import sys
import base64
from datetime import datetime


def resource_path(relative):
    """打包后资源在 sys._MEIPASS，开发时在同目录"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative)


class Api:
    """暴露给前端的本地能力：把分享卡 PNG（dataURL）保存到用户下载目录。"""

    def save_share_card(self, data_url):
        try:
            _, b64 = data_url.split(",", 1)
            raw = base64.b64decode(b64)
        except Exception:
            return ""
        dl = os.path.join(os.path.expanduser("~"), "Downloads")
        if not os.path.isdir(dl):
            dl = os.path.dirname(os.path.abspath(__file__))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(dl, "科莱德学习成就卡_%s.png" % ts)
        try:
            with open(path, "wb") as f:
                f.write(raw)
            return path
        except Exception:
            return ""


def on_loaded():
    # 禁用右键菜单，体验更接近原生 App
    webview.windows[0].evaluate_js(
        "document.addEventListener('contextmenu', e => e.preventDefault());"
    )


if __name__ == "__main__":
    html = resource_path("home.html")
    window = webview.create_window(
        "科莱德图解词典",
        html,
        width=1280,
        height=860,
        min_size=(1024, 700),
        js_api=Api(),
    )
    window.events.loaded += on_loaded
    webview.start()
