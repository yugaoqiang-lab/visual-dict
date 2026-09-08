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
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
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
    private TtsBridge ttsBridge;
    // 当前实际选用的语音引擎包名（优先讯飞，回退系统默认），用于提示用户
    private volatile String activeEngineName = "系统默认";
    // TTS 诊断信息（已检测到的引擎列表），供网页展示，辅助排查“缺什么”
    private volatile String ttsDiag = "";

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
        // 优先选用设备已装的【讯飞语音引擎】(com.iflytek.speechcloud / com.iflytek.tts)，
        // 国行平板通常自带且无需 GMS；找不到或该引擎无英文音库时回退系统默认引擎。
        ttsBridge = new TtsBridge();
        webView.addJavascriptInterface(ttsBridge, "AndroidTTS");
        initTts();

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

    /**
     * 初始化原生 TTS：先枚举设备里所有已装的语音引擎，按“eSpeak → 讯飞 → Google → 系统默认”的优先级
     * 逐个尝试，选第一个“能初始化且支持英文(Locale.US，退而求 Locale.ENGLISH)”的引擎。
     * 即便某些引擎 setLanguage 报“缺数据”，只要实例能创建也尽量保留为候选（eSpeak 的英文通常是
     * 内置的，设语言失败往往只是检测误报，实际 speak 仍能出声）；最终由网页“测试发音”按钮真机验证。
     */
    private void initTts() {
        // 用一个临时实例枚举已装引擎（getEngines() 需在初始化成功后调用）
        final TextToSpeech[] probeHolder = new TextToSpeech[1];
        probeHolder[0] = new TextToSpeech(this, status -> {
            TextToSpeech probe = probeHolder[0];
            List<String> pkgs = new ArrayList<>();
            List<String> labels = new ArrayList<>();
            if (status == TextToSpeech.SUCCESS) {
                try {
                    for (TextToSpeech.EngineInfo e : probe.getEngines()) {
                        pkgs.add(e.name);
                        labels.add(e.label != null ? e.label : e.name);
                    }
                } catch (Exception ignore) {}
            }
            try { probe.shutdown(); } catch (Exception ignore) {}
            // 记录诊断：已检测到哪些引擎
            StringBuilder sb = new StringBuilder();
            sb.append("已检测到 ").append(pkgs.size()).append(" 个语音引擎");
            if (!pkgs.isEmpty()) {
                sb.append("（");
                for (int i = 0; i < labels.size(); i++) {
                    if (i > 0) sb.append("、");
                    sb.append(labels.get(i));
                }
                sb.append("）");
            }
            ttsDiag = sb.toString();
            // 候选顺序：eSpeak 最优先，其次讯飞/Google，其余保持，最后系统默认兜底
            List<String> ordered = new ArrayList<>(pkgs);
            Collections.sort(ordered, (a, b) -> {
                int ra = rank(a), rb = rank(b);
                if (ra != rb) return Integer.compare(ra, rb);
                return 0;
            });
            ordered.add(null); // 系统默认引擎兜底
            initTtsRecursive(ordered.toArray(new String[0]), 0, null);
        });
    }

    /** 引擎优先级（数值越小越优先）：eSpeak > 讯飞 > Google > 三星 > 其它 > 系统默认(null)。 */
    private int rank(String pkg) {
        if (pkg == null) return 5;
        String p = pkg.toLowerCase();
        if (p.contains("reecedunn") || p.contains("espeak")) return 0; // eSpeak 离线英文最稳
        if (p.contains("iflytek")) return 1;
        if (p.contains("google")) return 2;
        if (p.contains("samsung")) return 3;
        return 4;
    }

    private void initTtsRecursive(final String[] engines, final int idx, final TextToSpeech prev) {
        if (idx >= engines.length) {
            // 所有引擎尝试完毕：保留最后一个可用实例（优先 eSpeak）作为候选并尽量尝试发音。
            // eSpeak 的英文多为内置，setLanguage 即便报“缺数据”也常能 speak 出声，故标记 ready。
            tts = prev;
            ttsReady = (prev != null);
            activeEngineName = (prev != null) ? describeEngine(prev) : "无";
            if (prev != null) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "已选用「" + activeEngineName + "」。如点词仍无声，请打开该引擎 App 确认 English 语音数据已下载；也可点页面右下“测试发音”自检",
                        Toast.LENGTH_LONG).show());
            } else {
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "未检测到任何 TTS 引擎：请在平板安装 eSpeak TTS 后重启 App",
                        Toast.LENGTH_LONG).show());
            }
            return;
        }
        final String pkg = engines[idx];
        // 用数组持有实例，规避“lambda 在构造期间可能捕获到尚未赋值的局部变量 t”的编译错误
        final TextToSpeech[] holder = new TextToSpeech[1];
        holder[0] = new TextToSpeech(this, status -> {
            TextToSpeech t = holder[0];
            if (status != TextToSpeech.SUCCESS) {
                // 该引擎未安装：丢弃并尝试下一个（保留之前可用的回退引擎）
                if (prev != null && prev != t) prev.shutdown();
                initTtsRecursive(engines, idx + 1, prev);
                return;
            }
            int r = t.setLanguage(Locale.US);
            if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                // en-US 缺失时退而求其次试语言级 en（eSpeak 等常以此通过）
                r = t.setLanguage(Locale.ENGLISH);
            }
            if (r == TextToSpeech.LANG_MISSING_DATA || r == TextToSpeech.LANG_NOT_SUPPORTED) {
                // 仍不支持英文：保留为候选（继续尝试下一个引擎），不立即丢弃
                if (prev != null && prev != t) prev.shutdown();
                initTtsRecursive(engines, idx + 1, t);
                return;
            }
            // 该引擎支持英文发音：正式选用它（先关掉之前的回退实例）
            if (prev != null && prev != t) prev.shutdown();
            tts = t;
            ttsReady = true;
            activeEngineName = (pkg == null) ? "系统默认" : pkg;
            ttsBridge.flushPending();
        }, pkg);
    }

    private String describeEngine(TextToSpeech t) {
        try {
            if (t != null) {
                String n = t.getDefaultEngine();
                if (n != null && !n.isEmpty()) return n;
            }
        } catch (Exception ignore) {}
        return "系统默认";
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

        /** 当前选用的语音引擎包名（如 com.reecedunn.espeak / 系统默认），供网页展示。 */
        @JavascriptInterface
        public String engineName() {
            return activeEngineName;
        }

        /** 设备已检测到的语音引擎列表（用于排查“缺什么”）。 */
        @JavascriptInterface
        public String diag() {
            return ttsDiag;
        }

        /** 综合状态（供网页自检面板展示）。 */
        @JavascriptInterface
        public String status() {
            return "ready=" + (tts != null && ttsReady) + "; engine=" + activeEngineName + "; " + ttsDiag;
        }

        /** 真机自测：直接朗读一句英文，返回结果文案（App 内“测试发音”按钮调用）。 */
        @JavascriptInterface
        public String testSpeak() {
            if (tts == null) {
                return "未就绪：" + ttsDiag + "（无可用引擎实例）";
            }
            try {
                tts.speak("This is a test. Hello, eSpeak.", TextToSpeech.QUEUE_FLUSH, null, "vd_test");
                return "已用「" + activeEngineName + "」发出测试音，请听设备扬声器";
            } catch (Exception e) {
                return "发音异常：" + e.getMessage();
            }
        }

        /** 跳转到系统 TTS / 语音数据安装设置页（尽最大努力）。 */
        @JavascriptInterface
        public void openSettings() {
            // 优先打开“安装语音数据”页（针对当前默认引擎）；若无法解析则退回系统设置。
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
            if (tts == null) {
                // 引擎实例都没创建成功：明确提示并缓存，待引擎就绪后重试
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "语音引擎未就绪，请稍候或重启 App", Toast.LENGTH_SHORT).show());
                pending.add(text);
                return;
            }
            // 引擎实例存在就尽量出声（eSpeak 英文常内置，setLanguage 报缺数据也不影响实际朗读）
            try {
                tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "vd_" + System.currentTimeMillis());
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this,
                        "发音失败：" + e.getMessage(), Toast.LENGTH_SHORT).show());
            }
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
