
  const list=document.getElementById('list'), cnt=document.getElementById('cnt'), q=document.getElementById('q');
  const mAll=document.getElementById('mAll'), mFav=document.getElementById('mFav');
  const MAX=300;
  let mode='all';
  let favs=new Set(JSON.parse(localStorage.getItem('vd_favs')||'[]'));

  function saveFavs(){ try{ localStorage.setItem('vd_favs', JSON.stringify([...favs])); }catch(e){} }
  function toggleFav(en, btn){ if(favs.has(en)) favs.delete(en); else favs.add(en); saveFavs(); if(btn) btn.textContent=favs.has(en)?'★':'☆'; if(mode==='fav') render(); }
  function setMode(m){ mode=m; mAll.classList.toggle('on', m==='all'); mFav.classList.toggle('on', m==='fav'); render(); }
  function speak(en){ try{ speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(en); u.lang='en-US'; u.rate=0.92; speechSynthesis.speak(u);}catch(e){} }
  function esc(s){ return (s||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
  function hl(s,key){ if(!key) return esc(s); const i=(''+s).toLowerCase().indexOf(key.toLowerCase()); if(i<0) return esc(s); return esc(s.slice(0,i))+'<mark>'+esc(s.slice(i,i+key.length))+'</mark>'+esc(s.slice(i+key.length)); }
  function render(){
    const k=q.value.trim().toLowerCase();
    list.innerHTML='';
    const favN=favs.size;
    if(!k && mode==='all'){ cnt.textContent='输入关键词开始搜索（共 '+WORDS.length+' 词）· ★收藏 '+favN+' 个'; return; }
    if(!k && mode==='fav'){ cnt.textContent='★ 我的收藏（'+favN+' 个）'; }
    let n=0;
    for(const w of WORDS){
      const en=w[0], ip=w[1], a=w[2], zh=w[3]||'', pg=w[4]||0;
      if(mode==='fav' && !favs.has(en)) continue;
      const enL=en.toLowerCase(), zhL=zh.toLowerCase();
      if(k && enL.indexOf(k)<0 && zhL.indexOf(k)<0) continue;
      const it=document.createElement('div'); it.className='it';
      const main=document.createElement('div'); main.className='main';
      const e=document.createElement('div'); e.className='en'; e.innerHTML=hl(en,k);
      const p=document.createElement('div'); p.className='ipa'+(a?' approx':''); p.textContent=(a?'≈ ':'')+ip+(a?' （近似）':'');
      main.appendChild(e); main.appendChild(p);
      if(zh){ const z=document.createElement('div'); z.className='zh'; z.innerHTML=hl(zh,k); main.appendChild(z); }
      it.appendChild(main);
      if(pg>0){ const v=document.createElement('button'); v.className='ab view'; v.textContent='📖'; v.title='在图典中查看'; v.onclick=(ev)=>{ ev.stopPropagation(); location.href='index2.html#'+pg; }; it.appendChild(v); }
      const spk=document.createElement('button'); spk.className='ab'; spk.textContent='🔊'; spk.onclick=(ev)=>{ ev.stopPropagation(); speak(en); }; it.appendChild(spk);
      const fb=document.createElement('button'); fb.className='ab fav'; fb.textContent=favs.has(en)?'★':'☆'; fb.onclick=(ev)=>{ ev.stopPropagation(); toggleFav(en, fb); }; it.appendChild(fb);
      it.onclick=()=>speak(en);
      list.appendChild(it);
      if(++n>=MAX) break;
    }
    if(k) cnt.textContent= n>=MAX ? '显示前 '+MAX+' 条，请缩小关键词' : '匹配 '+n+' 词 · ★收藏 '+favN+' 个';
    else if(mode==='fav' && n===0) cnt.textContent='还没有收藏，点结果上的 ☆ 即可加入生词本';
    if(n===0 && (k || mode==='fav')){ const e=document.createElement('div'); e.className='empty'; e.textContent= mode==='fav'&&!k ? '还没有收藏，点结果上的 ☆ 即可加入生词本' : '没有匹配的词'; list.appendChild(e); }
  }
  function clearQ(){ q.value=''; q.focus(); render(); }
  q.addEventListener('input', render);
  render();
  /* 支持从首页「我的生词本」以 #fav 直接进入收藏模式 */
  (function(){
    if((location.hash||'').replace('#','').trim()==='fav'){ setMode('fav'); }
  })();

  /* ---------- 生词本听写测验 ---------- */
  let quizPool=[], quizCur=null, quizScore={c:0,t:0};
  function favWordList(){ return WORDS.filter(w=>favs.has(w[0])); }
  function updateQScore(){ document.getElementById('qscore').textContent='得分 '+quizScore.c+'/'+quizScore.t; }
  function startQuiz(){
    const list=favWordList();
    if(!list.length){ toast('先收藏一些单词再来测验 🙂'); return; }
    quizPool=list.slice(); quizScore={c:0,t:0};
    document.getElementById('list').style.display='none';
    document.querySelector('.modes').style.display='none';
    document.getElementById('quiz').style.display='block';
    nextQuiz();
  }
  function nextQuiz(){
    if(!quizPool.length){ document.getElementById('qresult').textContent='🎉 本轮测验完成！'; updateQScore(); return; }
    const i=Math.floor(Math.random()*quizPool.length);
    quizCur=quizPool[i]; quizPool.splice(i,1);
    document.getElementById('qans').value='';
    document.getElementById('qresult').textContent='';
    updateQScore(); quizSpeak();
    setTimeout(()=>{ const e=document.getElementById('qans'); if(e) e.focus(); },50);
  }
  function quizSpeak(){ if(quizCur) speak(quizCur[0]); }
  function showAnswer(){ if(quizCur) document.getElementById('qresult').innerHTML='<span style="color:#1565c0">'+quizCur[0]+' '+quizCur[1]+(quizCur[3]?' '+quizCur[3]:'')+'</span>'; }
  function checkQuiz(){
    if(!quizCur) return;
    const ans=document.getElementById('qans').value.trim().toLowerCase();
    const cor=quizCur[0].toLowerCase();
    quizScore.t++;
    if(ans===cor){ document.getElementById('qresult').innerHTML='<span style="color:#2e7d32">✓ 正确！</span>'; }
    else { document.getElementById('qresult').innerHTML='<span style="color:#b3261e">✗ 正确是：'+quizCur[0]+' '+quizCur[1]+(quizCur[3]?' '+quizCur[3]:'')+'</span>'; }
    updateQScore();
  }
  const qansEl=document.getElementById('qans');
  if(qansEl) qansEl.addEventListener('keydown', e=>{ if(e.key==='Enter') checkQuiz(); });
  function exitQuiz(){
    document.getElementById('quiz').style.display='none';
    document.getElementById('list').style.display='block';
    document.querySelector('.modes').style.display='flex';
    render();
  }

  /* ---------- 生词本选择题测验（点选，移动端友好） ---------- */
  let mcqPool=[], mcqCur=null, mcqScore={c:0,t:0}, mcqCorrect='';
  function updateMcqScore(){ document.getElementById('mcScore').textContent='得分 '+mcqScore.c+'/'+mcqScore.t; }
  function startMCQ(){
    const pool=favWordList().filter(w=>w[3] && w[3].trim());
    if(pool.length===0){ toast('收藏里没有带中文释义的词，先收藏一些再来 🙂'); return; }
    mcqPool=pool.slice(); mcqScore={c:0,t:0};
    document.getElementById('list').style.display='none';
    document.querySelector('.modes').style.display='none';
    document.getElementById('mcq').style.display='block';
    nextMCQ();
  }
  function nextMCQ(){
    if(!mcqPool.length){ document.getElementById('mcResult').innerHTML='🎉 本轮完成！'; updateMcqScore(); return; }
    const i=Math.floor(Math.random()*mcqPool.length);
    mcqCur=mcqPool[i]; mcqPool.splice(i,1);
    const correctZh=mcqCur[3].trim();
    const distractors=new Set();
    let guard=0;
    while(distractors.size<3 && guard++<600){
      const c=WORDS[Math.floor(Math.random()*WORDS.length)];
      const z=(c[3]||'').trim();
      if(z && z!==correctZh && !distractors.has(z)) distractors.add(z);
    }
    const opts=[correctZh, ...distractors];
    for(let k=opts.length-1;k>0;k--){ const j=Math.floor(Math.random()*(k+1)); const t=opts[k]; opts[k]=opts[j]; opts[j]=t; }
    mcqCorrect=correctZh;
    document.getElementById('mcWord').textContent=mcqCur[0];
    document.getElementById('mcOpts').innerHTML=opts.map(o=>'<button class="opt" onclick="checkMCQ(this)">'+esc(o)+'</button>').join('');
    document.getElementById('mcResult').textContent='';
    updateMcqScore(); mcqSpeak();
  }
  function mcqSpeak(){ if(mcqCur) speak(mcqCur[0]); }
  function checkMCQ(btn){
    if(!mcqCur || btn.dataset.done) return;
    const chosen=btn.textContent, correct=mcqCorrect;
    document.querySelectorAll('#mcOpts .opt').forEach(o=>{
      o.dataset.done='1'; o.disabled=true;
      if(o.textContent===correct) o.classList.add('correct');
      if(o===btn && chosen!==correct) o.classList.add('wrong');
    });
    mcqScore.t++;
    if(chosen===correct){ document.getElementById('mcResult').innerHTML='<span style="color:#2e7d32">✓ 正确！</span>'; mcqScore.c++; }
    else { document.getElementById('mcResult').innerHTML='<span style="color:#b3261e">✗ 正确是：'+esc(correct)+'</span>'; }
    updateMcqScore();
  }
  function exitMCQ(){
    document.getElementById('mcq').style.display='none';
    document.getElementById('list').style.display='block';
    document.querySelector('.modes').style.display='flex';
    render();
  }

  /* ---------- 轻量 toast（补全 search.html 缺失定义） ---------- */
  let toastTimer;
  function toast(msg){
    const el=document.getElementById('toast'); if(!el) return;
    el.textContent=msg; el.classList.add('show');
    clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove('show'),1400);
  }

  /* ---------- 生词本导出 / 导入 / 清空（跨设备迁移，纯 JSON 文本） ---------- */
  function openMgr(){ refreshExp(); document.getElementById('mgr').style.display='block'; document.getElementById('list').style.display='none'; document.querySelector('.modes').style.display='none'; }
  function exitMgr(){ document.getElementById('mgr').style.display='none'; document.getElementById('list').style.display='block'; document.querySelector('.modes').style.display='flex'; render(); }
  function exportFavsObj(){ return { app:'科莱德图解词典', type:'favorites', version:1, exportedAt:new Date().toISOString(), count:favs.size, words:[...favs] }; }
  function refreshExp(){
    const obj=exportFavsObj(); const txt=JSON.stringify(obj,null,2);
    document.getElementById('expOut').value=txt;
    try{ const blob=new Blob([txt],{type:'application/json'}); const url=URL.createObjectURL(blob); const a=document.getElementById('expLink'); a.href=url; a.download='生词本.json'; }
    catch(e){ const a=document.getElementById('expLink'); if(a) a.style.display='none'; }
  }
  function copyFavs(){
    const t=document.getElementById('expOut'); const v=t.value;
    if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(v).then(()=>toast('已复制到剪贴板'),()=>fallbackCopy(t)); }
    else fallbackCopy(t);
  }
  function fallbackCopy(t){ t.removeAttribute('readonly'); t.focus(); t.select(); try{ document.execCommand('copy'); toast('已复制（兼容模式）'); }catch(e){ toast('请手动选择并复制文本框内容'); } t.setAttribute('readonly',''); t.blur(); }
  function doImport(text){
    let added=0;
    try{
      const obj=JSON.parse(text);
      const arr = Array.isArray(obj) ? obj : (obj.words || obj.favorites || []);
      if(!Array.isArray(arr)) throw new Error('未找到 words 数组');
      for(const w of arr){
        const s = (w && typeof w==='object' && w.en) ? w.en : (typeof w==='string' ? w : null);
        if(s && s.trim()){ const k=s.trim(); if(!favs.has(k)){ favs.add(k); added++; } }
      }
      saveFavs();
      document.getElementById('mgrMsg').textContent='✓ 成功导入 '+added+' 个新词（共 '+favs.size+' 个）';
      toast('导入完成：+'+added+' 词');
      document.getElementById('impIn').value='';
      refreshExp();
    }catch(e){ document.getElementById('mgrMsg').textContent='✗ 解析失败：'+e.message; toast('导入失败，检查 JSON 格式'); }
  }
  function importFavs(){ doImport(document.getElementById('impIn').value.trim()); }
  function importFavsFile(inp){ const f=inp.files[0]; if(!f) return; const r=new FileReader(); r.onload=()=>{ doImport(r.result); inp.value=''; }; r.readAsText(f); }
  let clearArmed=false;
  function clearFavs(){
    if(!favs.size){ toast('生词本已是空的'); return; }
    const b=document.getElementById('clearBtn');
    if(!clearArmed){ clearArmed=true; b.textContent='再点一次确认清空'; setTimeout(()=>{ clearArmed=false; b.textContent='🗑 清空生词本'; },3000); return; }
    clearArmed=false; b.textContent='🗑 清空生词本';
    favs.clear(); saveFavs(); toast('已清空生词本'); refreshExp();
  }
