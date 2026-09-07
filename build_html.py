# -*- coding: utf-8 -*-
"""Generate index2.html: original page images + per-word American IPA + click-to-speak."""
import os, json

OUT = os.path.dirname(os.path.abspath(__file__))
pages = json.load(open(os.path.join(OUT, "pages_meta.json"), encoding="utf-8"))

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>图解词典 · 原图注音版</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; }
  body { background: #2b2f36; color: #e8eaed; display: flex; flex-direction: column; height: 100vh; }
  header { flex: 0 0 auto; background: #1f2329; border-bottom: 1px solid #000; padding: 8px 12px;
           display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  header .title { font-weight: 700; color: #ffd479; margin-right: 6px; white-space: nowrap; }
  header button { background: #3a4049; color: #e8eaed; border: 1px solid #555; border-radius: 6px;
                  padding: 5px 10px; cursor: pointer; font-size: 14px; }
  header button:hover { background: #4a525c; }
  header input[type=number] { width: 64px; padding: 4px 6px; border-radius: 6px; border: 1px solid #555;
                              background: #2b2f36; color: #e8eaed; text-align: center; }
  header input[type=text] { padding: 5px 8px; border-radius: 6px; border: 1px solid #555;
                            background: #2b2f36; color: #e8eaed; min-width: 160px; }
  header label { font-size: 13px; display: flex; align-items: center; gap: 4px; cursor: pointer; }
  .stat { font-size: 12px; color: #9aa0a6; white-space: nowrap; }
  .help { position: relative; }
  .help .pop { display: none; position: absolute; top: 30px; right: 0; width: 280px; background: #1f2329;
               border: 1px solid #555; border-radius: 8px; padding: 10px; font-size: 12px; line-height: 1.6; z-index: 50; }
  .help:hover .pop { display: block; }
  main { flex: 1 1 auto; overflow: auto; padding: 14px; display: flex; justify-content: center; }
  .page-wrap { position: relative; width: 100%; max-width: 1000px; background: #fff;
               box-shadow: 0 4px 24px rgba(0,0,0,.5); }
  .page-wrap img { display: block; width: 100%; height: auto; }
  .word-hit { position: absolute; cursor: pointer; border-radius: 3px; }
  .word-hit:hover { background: rgba(220,60,60,.18); outline: 1px solid rgba(220,60,60,.7); }
  .word-hit.flash { background: rgba(255,200,0,.55); outline: 2px solid #ffc800; }
  .ipa { position: absolute; font-size: 11px; line-height: 1; color: #b3261e; font-weight: 600;
         background: rgba(255,255,255,.9); border: 1px solid #e7c4c0; border-radius: 4px;
         padding: 1px 4px; white-space: nowrap; cursor: pointer;
         box-shadow: 0 1px 2px rgba(0,0,0,.2); }
  .ipa.approx { color: #1f6fd6; background: rgba(232,240,255,.94); border-color: #9bbce0;
                border-style: dashed; box-shadow: 0 1px 2px rgba(0,0,0,.12); }
  .ipa.approx::before { content: "≈"; opacity: .75; margin-right: 1px; }
  body.no-ipa .ipa { display: none; }
  #toast { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%);
           background: #111; color: #ffd479; padding: 8px 16px; border-radius: 20px; font-size: 15px;
           opacity: 0; transition: opacity .25s; pointer-events: none; z-index: 100; }
  #toast.show { opacity: 1; }
  #results { position: absolute; background: #1f2329; border: 1px solid #555; border-radius: 8px;
             max-height: 320px; overflow: auto; z-index: 60; font-size: 13px; min-width: 220px; }
  #results div { padding: 6px 10px; cursor: pointer; display: flex; justify-content: space-between; gap: 10px; }
  #results div:hover { background: #3a4049; }
  #results .pi { color: #9aa0a6; }
  .srch-wrap { position: relative; }
</style>
</head>
<body>
<header>
  <span class="title">📇 图解词典</span>
  <button id="prev">◀ 上一页</button>
  <input type="number" id="jump" min="1" title="跳到原书页码">
  <button id="next">下一页 ▶</button>
  <span class="stat" id="stat"></span>
  <label><input type="checkbox" id="ipaToggle" checked> 显示音标</label>
  <span class="srch-wrap">
    <input type="text" id="search" placeholder="搜索单词…">
    <div id="results" style="display:none"></div>
  </span>
  <span class="help">ℹ️
    <div class="pop">• 原书页面图片完整保留（含插画）。<br>• 每个英文单词后附加<b>美式音标</b>：<span style="color:#b3261e">红色</span>为离线词典（ECDICT/CMU）注音；<span style="color:#1f6fd6">蓝色「≈」</span>为规则推算的<b>近似音标</b>，仅供参考。<br>• <b>点击任意单词</b>即可用浏览器内置的<b>美式英语</b>真人发音朗读。<br>• 读音以浏览器 en-US 语音为准；近似音标与实际读音可能有出入。</div>
  </span>
</header>
<main>
  <div class="page-wrap" id="wrap">
    <img id="pageImg" alt="page">
    <div id="overlay"></div>
  </div>
</main>
<div id="toast"></div>

<script>
const PAGES = __PAGES_JSON__;
let cur = 0;
let showIpa = true;
const img = document.getElementById('pageImg');
const overlay = document.getElementById('overlay');
const jump = document.getElementById('jump');
const stat = document.getElementById('stat');
const results = document.getElementById('results');
const searchBox = document.getElementById('search');
const toastEl = document.getElementById('toast');

/* ---------- speech ---------- */
let voices = [];
function loadVoices(){ voices = window.speechSynthesis ? speechSynthesis.getVoices() : []; }
if (window.speechSynthesis) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }
function speak(text){
  if (!window.speechSynthesis) { toast('当前浏览器不支持语音'); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = 'en-US'; u.rate = 0.95; u.pitch = 1;
  const v = voices.find(v => /en[-_]US/i.test(v.lang));
  if (v) u.voice = v;
  speechSynthesis.speak(u);
  toast('🔊 ' + text);
}
let toastTimer;
function toast(msg){
  toastEl.textContent = msg; toastEl.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(()=>toastEl.classList.remove('show'), 1400);
}

/* ---------- render ---------- */
function render(idx){
  cur = Math.max(0, Math.min(PAGES.length - 1, idx));
  const p = PAGES[cur];
  img.src = p.img;
  overlay.innerHTML = '';
  for (const w of p.words){
    const hit = document.createElement('div');
    hit.className = 'word-hit';
    hit.style.left = w.x + '%'; hit.style.top = w.y + '%';
    hit.style.width = w.w + '%'; hit.style.height = w.h + '%';
    hit.dataset.word = w.t;
    overlay.appendChild(hit);
    if (w.ipa && showIpa){
      const ip = document.createElement('div');
      ip.className = 'ipa' + (w.approx ? ' approx' : '');
      if (w.approx) ip.title = '近似音标（规则推算，仅供参考）';
      // 垂直居中于单词；默认右侧放，仅贴边(>94%)翻到左侧，并加 4px 间隙
      ip.style.top = (w.y + w.h/2) + '%';
      if (w.x + w.w > 94){
        ip.style.right = (100 - w.x) + '%';
        ip.style.transform = 'translate(-4px,-50%)';
      } else {
        ip.style.left = (w.x + w.w) + '%';
        ip.style.transform = 'translate(4px,-50%)';
      }
      ip.dataset.word = w.t;
      ip.textContent = w.ipa;
      overlay.appendChild(ip);
    }
  }
  jump.value = p.n;
  const ipaCount = p.words.filter(w=>w.ipa).length;
  stat.textContent = `第 ${cur+1}/${PAGES.length} 页 · 原书 P${p.n} · 本页 ${p.words.length} 词（音标 ${ipaCount}）`;
}

overlay.addEventListener('click', e=>{
  const el = e.target.closest('[data-word]');
  if (el) speak(el.dataset.word);
});

/* ---------- nav ---------- */
document.getElementById('prev').onclick = ()=>render(cur-1);
document.getElementById('next').onclick = ()=>render(cur+1);
jump.onchange = ()=>{
  const n = parseInt(jump.value, 10);
  const idx = PAGES.findIndex(p=>p.n===n);
  if (idx>=0) render(idx); else { const i=PAGES.findIndex(p=>p.n>=n); render(i<0?PAGES.length-1:i); }
};
document.getElementById('ipaToggle').onchange = e=>{
  showIpa = e.target.checked;
  document.body.classList.toggle('no-ipa', !showIpa);
  render(cur);
};
document.addEventListener('keydown', e=>{
  if (e.target.tagName==='INPUT') return;
  if (e.key==='ArrowLeft') render(cur-1);
  if (e.key==='ArrowRight') render(cur+1);
});

/* ---------- search ---------- */
const allWords = [];
PAGES.forEach((p,i)=>p.words.forEach(w=>allWords.push({w, pageIdx:i, n:p.n})));
searchBox.addEventListener('input', ()=>{
  const q = searchBox.value.trim().toLowerCase();
  if (!q){ results.style.display='none'; return; }
  const hits = allWords.filter(o=>o.w.t.toLowerCase().includes(q)).slice(0,40);
  if (!hits.length){ results.style.display='none'; return; }
  results.innerHTML = '';
  hits.forEach(o=>{
    const d = document.createElement('div');
    d.innerHTML = `<span>${o.w.t}${o.w.ipa?' <span style="color:'+(o.w.approx?'#1f6fd6':'#e08')+'">'+o.w.ipa+'</span>':''}</span><span class="pi">P${o.n}</span>`;
    d.onclick = ()=>{ render(o.pageIdx); flash(o.w.t); results.style.display='none'; searchBox.blur(); };
    results.appendChild(d);
  });
  results.style.display = 'block';
});
document.addEventListener('click', e=>{ if(!e.target.closest('.srch-wrap')) results.style.display='none'; });
function flash(term){
  requestAnimationFrame(()=>{
    const el = overlay.querySelector(`.word-hit[data-word="${CSS.escape(term)}"]`);
    if (el){ el.classList.add('flash'); setTimeout(()=>el.classList.remove('flash'), 1500); }
  });
}

render(0);
</script>
</body>
</html>
"""

payload = json.dumps(pages, ensure_ascii=False)
html = HTML.replace("__PAGES_JSON__", payload)
out_path = os.path.join(OUT, "index2.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", out_path, "size(KB)=", round(os.path.getsize(out_path)/1024, 1), "pages=", len(pages))
