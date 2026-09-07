package com.klyde.visualdict;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.provider.Settings;
import android.speech.tts.TextToSpeech;
import android.widget.Toast;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.CountDownLatch;

public class MainActivity extends Activity {
    private static final int PORT = 8765;
    private static final String BASE_URL = "http://127.0.0.1:" + PORT + "/";
    // 【关键】永远用 file:///android_asset/ 打开：不依赖任何本地服务器/网络，100% 能开。
    private static final String FILE_URL = "file:///android_asset/home.html";
    // 安装 TTS 语音数据的系统广播 action（等价于 TextToSpeech.Engine.ACTION_TTS_DATA_INSTALL，
    // 但用字面量避免部分编译环境下该常量不可见导致编译失败）
    private static final String TTS_INSTALL_ACTION = "android.speech.tts.engine.INSTALL_TTS_DATA";
    private WebView webView;
    private AssetServer server;
    // 原生 TTS 引擎（离线发音用，WebView 的 Web Speech API 多数真机不支持）
    private TextToSpeech tts;
    private volatile boolean ttsReady = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(true);
        ws.setAllowContentAccess(true);
        // 允许 file:// 页面加载同域（android_asset）下的子资源（words.js、pages_mob/*.jpg 等），
        // 否则部分 WebView 构建会拦截 file:// 页面的子资源，导致白屏/图片缺失。
        ws.setAllowFileAccessFromFileURLs(true);
        ws.setAllowUniversalAccessFromFileURLs(true);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);

        // 只做日志记录，绝不在主框架出错时把用户留在空白/错误页。
        // 注意：Android 10+ 上 onReceivedError 对 ERR_CONNECTION_REFUSED 不会回调，
        // 因此“出错就重试/回退”的逻辑是死代码——这里不再依赖它。
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    android.util.Log.w("AssetServer", "main frame error: " + error.getErrorCode());
                }
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
                // 子资源（图片等）加载失败时静默忽略，不影响页面打开
            }
        });
        webView.setWebChromeClient(new WebChromeClient());

        // 本地服务器：尽力启动，仅用于“可选”的 http 上下文。即使它没起来，App 也照样能打开。
        server = new AssetServer(getApplicationContext(), PORT);
        server.start();

        // 原生 TTS 桥：把 Android 系统 TextToSpeech 暴露给网页 JS，离线发音。
        // WebView 的 speechSynthesis 多数真机不可用，故优先走原生引擎。
        final TtsBridge ttsBridge = new TtsBridge();
        tts = new TextToSpeech(this, new TextToSpeech.OnInitListener() {
            @Override
            public void onInit(int status) {
                if (status != TextToSpeech.SUCCESS) {
                    runOnUiThread(() -> Toast.makeText(MainActivity.this,
                            "语音引擎初始化失败，发音不可用", Toast.LENGTH_LONG).show());
                    return;
                }
                int r = tts.setLanguage(Locale.US);
                if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                    // 设备未安装英语语音数据：明确提示用户，并提供跳转安装入口。
                    ttsReady = false;
                    runOnUiThread(() -> Toast.makeText(MainActivity.this,
                            "未安装英语语音包：设置→语言和输入法→文字转语音(TTS)输出→安装语音数据(English)",
                            Toast.LENGTH_LONG).show());
                } else {
                    ttsReady = true;
                    ttsBridge.flushPending();
                }
            }
        });
        webView.addJavascriptInterface(ttsBridge, "AndroidTTS");

        // 【核心修复】先开 file://，保证 App 一定能进首页；后续页面通过相对路径（index2.html /
        // search.html / pages_mob/*.jpg）都能在 file:// 下正常解析，完全离线可用。
        webView.loadUrl(FILE_URL);
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (server != null) server.stopServer();
        if (tts != null) { tts.stop(); tts.shutdown(); tts = null; }
    }

    /** 暴露给 JS 的原生 TTS 桥。JS 调用 AndroidTTS.speak("word") 即触发系统离线语音。 */
    class TtsBridge {
        private final Queue<String> pending = new ConcurrentLinkedQueue<>();

        @JavascriptInterface
        public boolean isAvailable() {
            return tts != null && ttsReady;
        }

        /** 英语语音数据是否缺失（供网页决定是否显示“安装语音包”提示）。 */
        @JavascriptInterface
        public boolean needInstall() {
            return tts != null && !ttsReady;
        }

        /** 跳转到系统 TTS / 语音数据安装设置页（尽最大努力）。 */
        @JavascriptInterface
        public void openSettings() {
            Intent i = new Intent(TTS_INSTALL_ACTION);
            if (i.resolveActivity(getPackageManager()) == null) {
                i = new Intent(Settings.ACTION_SETTINGS);
            }
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            try { startActivity(i); } catch (Exception ignore) {}
        }

        void promptInstallTtsData() {
            Intent i = new Intent(TTS_INSTALL_ACTION);
            if (i.resolveActivity(getPackageManager()) != null) {
                try { startActivity(i); } catch (Exception ignore) {}
            }
        }

        @JavascriptInterface
        public void speak(String text) {
            if (text == null || text.isEmpty()) return;
            if (tts == null || !ttsReady) {
                // 引擎未就绪或语言缺失：给出明确提示，而不是静默吞掉。
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        tts == null ? "语音引擎未就绪" : "英语语音包未安装，请到设置安装后重试",
                        Toast.LENGTH_SHORT).show());
                if (tts == null) pending.add(text);
                return;
            }
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "vd_" + System.currentTimeMillis());
        }

        void flushPending() {
            if (tts == null || !ttsReady) return;
            String t;
            while ((t = pending.poll()) != null) {
                tts.speak(t, TextToSpeech.QUEUE_FLUSH, null, "vd_" + System.currentTimeMillis());
            }
        }
    }

    static class AssetServer extends Thread {
        private final android.content.Context ctx;
        private final int port;
        private ServerSocket ss;
        private volatile boolean running = true;
        // 绑定完成信号：ServerSocket 真正绑到 127.0.0.1:port 之后才 countDown
        final CountDownLatch readyLatch = new CountDownLatch(1);

        AssetServer(android.content.Context c, int p) { ctx = c; port = p; }

        public void run() {
            try {
                // 显式绑定 IPv4 回环 127.0.0.1，避免 getLoopbackAddress() 在部分设备返回 ::1（IPv6）
                InetAddress loop = InetAddress.getByName("127.0.0.1");
                ss = new ServerSocket(port, 0, loop);
                readyLatch.countDown();
                while (running) {
                    try {
                        Socket s = ss.accept();
                        handle(s);
                    } catch (IOException ignore) {}
                }
            } catch (IOException e) {
                readyLatch.countDown(); // 让主线程别无限等
                android.util.Log.e("AssetServer", "server error", e);
            }
        }

        private void handle(Socket s) {
            try {
                BufferedReader reader = new BufferedReader(
                        new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
                String reqLine = reader.readLine();
                // 丢弃请求头，直到空行
                String line;
                while ((line = reader.readLine()) != null && !line.isEmpty()) {}

                if (reqLine == null) { s.close(); return; }

                // 解析路径: GET /path HTTP/1.1
                String path;
                int sp1 = reqLine.indexOf(' ');
                int sp2 = reqLine.lastIndexOf(' ');
                if (sp1 > 0 && sp2 > sp1) path = reqLine.substring(sp1 + 1, sp2);
                else path = "/";
                if (path.equals("/")) path = "/home.html";
                if (path.startsWith("/")) path = path.substring(1);

                // 探针：前端可用 <img src="http://127.0.0.1:8765/__ping"> 检测服务器是否存活
                if (path.equals("__ping")) {
                    String body = "ok";
                    byte[] b = body.getBytes(StandardCharsets.UTF_8);
                    String header = "HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: "
                            + b.length + "\r\nConnection: close\r\n\r\n";
                    OutputStream os = s.getOutputStream();
                    os.write(header.getBytes(StandardCharsets.UTF_8));
                    os.write(b);
                    os.flush();
                    s.close();
                    return;
                }

                byte[] data;
                String mime;
                try {
                    InputStream ais = ctx.getAssets().open(path);
                    data = readAll(ais);
                    mime = mimeFor(path);
                } catch (IOException e) {
                    String body = "404 Not Found";
                    byte[] b = body.getBytes(StandardCharsets.UTF_8);
                    String header = "HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: "
                            + b.length + "\r\nConnection: close\r\n\r\n";
                    OutputStream os = s.getOutputStream();
                    os.write(header.getBytes(StandardCharsets.UTF_8));
                    os.write(b);
                    os.flush();
                    s.close();
                    return;
                }

                String header = "HTTP/1.1 200 OK\r\nContent-Type: " + mime + "\r\nContent-Length: "
                        + data.length + "\r\nConnection: close\r\n\r\n";
                OutputStream os = s.getOutputStream();
                os.write(header.getBytes(StandardCharsets.UTF_8));
                os.write(data);
                os.flush();
            } catch (IOException ignore) {
            } finally {
                try { s.close(); } catch (IOException ignore) {}
            }
        }

        private String mimeFor(String p) {
            if (p.endsWith(".html") || p.endsWith(".htm")) return "text/html; charset=utf-8";
            if (p.endsWith(".jpg") || p.endsWith(".jpeg")) return "image/jpeg";
            if (p.endsWith(".png")) return "image/png";
            if (p.endsWith(".css")) return "text/css; charset=utf-8";
            if (p.endsWith(".js")) return "application/javascript";
            if (p.endsWith(".json")) return "application/json";
            if (p.endsWith(".svg")) return "image/svg+xml";
            return "application/octet-stream";
        }

        private byte[] readAll(InputStream is) throws IOException {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) != -1) baos.write(buf, 0, n);
            is.close();
            return baos.toByteArray();
        }

        void stopServer() {
            running = false;
            try { if (ss != null) ss.close(); } catch (IOException ignore) {}
        }
    }
}
