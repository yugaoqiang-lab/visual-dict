
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
  let quizPool=[], quizCur=null, quizScore={c:0,t:0}, quizWrong=[], quizDir='sound';
  function favWordList(){ return WORDS.filter(w=>favs.has(w[0])); }
  function updateQScore(){ document.getElementById('qscore').textContent='得分 '+quizScore.c+'/'+quizScore.t; }
  function startQuiz(){
    const list=favWordList();
    if(!list.length){ toast('先收藏一些单词再来测验 🙂'); return; }
    quizPool=list.slice().sort(dueCmp); quizScore={c:0,t:0}; quizWrong=[];
    document.getElementById('list').style.display='none';
    document.querySelector('.modes').style.display='none';
    document.getElementById('quiz').style.display='block';
    document.getElementById('quizSummary').style.display='none';
    document.getElementById('quizNext').style.display='inline-block';
    nextQuiz();
  }
  function nextQuiz(){
    if(!quizPool.length){ showQuizSummary(); return; }
    const i=Math.floor(Math.random()*quizPool.length);
    quizCur=quizPool[i]; quizPool.splice(i,1);
    document.getElementById('qans').value='';
    document.getElementById('qresult').textContent='';
    document.getElementById('quizPrompt').textContent = quizDir==='zh2en' ? ((quizCur[3]||'').trim()||quizCur[0]) : '';
    updateQScore();
    if(quizDir==='sound') quizSpeak();
    setTimeout(()=>{ const e=document.getElementById('qans'); if(e) e.focus(); },50);
  }
  function quizSpeak(){ if(quizCur) speak(quizCur[0]); }
  function setQuizDir(d){
    quizDir=d;
    document.getElementById('quizDirSound').classList.toggle('on', d==='sound');
    document.getElementById('quizDirZh').classList.toggle('on', d==='zh2en');
    document.getElementById('quizHint').textContent = d==='zh2en' ? '看中文释义，写出对应的英文单词（来自你的生词本）' : '听发音，写出英文单词（来自你的生词本）';
    if(quizCur) document.getElementById('quizPrompt').textContent = d==='zh2en' ? ((quizCur[3]||'').trim()||quizCur[0]) : '';
    if(d==='sound') quizSpeak();
  }
  function showAnswer(){ if(quizCur) document.getElementById('qresult').innerHTML='<span style="color:#1565c0">'+quizCur[0]+' '+quizCur[1]+(quizCur[3]?' '+quizCur[3]:'')+'</span>'; }
  function checkQuiz(){
    if(!quizCur) return;
    const ans=document.getElementById('qans').value.trim().toLowerCase();
    const cor=quizCur[0].toLowerCase();
    quizScore.t++;
    if(ans===cor){ document.getElementById('qresult').innerHTML='<span style="color:#2e7d32">✓ 正确！</span>'; recordResult(quizCur[0], true); }
    else { document.getElementById('qresult').innerHTML='<span style="color:#b3261e">✗ 正确是：'+quizCur[0]+' '+quizCur[1]+(quizCur[3]?' '+quizCur[3]:'')+'</span>'; quizWrong.push(quizCur); recordResult(quizCur[0], false); }
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
  function showQuizSummary(){
    bumpStreak();
    const c=quizScore.c, t=quizScore.t, wrong=t-c;
    document.getElementById('quizSumText').innerHTML = t===0 ? '本轮没有题目' : ('本轮完成：对 <span style="color:#2e7d32">'+c+'</span> / 错 <span style="color:#c0392b">'+wrong+'</span>'+(wrong===0?' 🎉 全对！':''));
    const list=document.getElementById('quizSumList');
    if(quizWrong.length){
      list.innerHTML = '<div style="color:#5a6b85;font-size:13px;margin-bottom:6px">拼错的词（建议重点复习）：</div>' + quizWrong.map(w=>'<div class="weak-item"><span class="wk-en">'+esc(w[0])+'</span> <span class="wk-ipa">'+esc(w[1])+'</span> <span class="wk-zh">'+esc(w[3]||'')+'</span></div>').join('');
    } else {
      list.innerHTML = '<div class="empty" style="margin-top:6px">本轮没有拼错的词，棒 👍</div>';
    }
    document.getElementById('quizRedrill').style.display = quizWrong.length ? 'inline-block' : 'none';
    document.getElementById('qans').value='';
    document.getElementById('qresult').textContent='';
    document.getElementById('quizNext').style.display='none';
    document.getElementById('quizSummary').style.display='block';
    updateQScore();
  }
  function redrillQuizWrong(){
    if(!quizWrong.length){ exitQuiz(); return; }
    const pool=quizWrong.slice();
    document.getElementById('quizSummary').style.display='none';
    document.getElementById('quizNext').style.display='inline-block';
    quizPool=pool.slice().sort(dueCmp); quizScore={c:0,t:0}; quizWrong=[];
    nextQuiz();
  }

  /* ---------- 生词本选择题测验（点选，移动端友好） ---------- */
  let mcqPool=[], mcqCur=null, mcqScore={c:0,t:0}, mcqCorrect='', mcqDir='en2zh', mcqWrong=[];
  function updateMcqScore(){ document.getElementById('mcScore').textContent='得分 '+mcqScore.c+'/'+mcqScore.t; }
  function setMcqDir(d){ mcqDir=d; document.getElementById('mcDirEn').classList.toggle('on', d==='en2zh'); document.getElementById('mcDirZh').classList.toggle('on', d==='zh2en'); }
  function launchMCQ(pool){
    mcqPool=pool.slice().sort(dueCmp); mcqScore={c:0,t:0}; mcqWrong=[];
    document.getElementById('list').style.display='none';
    document.querySelector('.modes').style.display='none';
    document.getElementById('mcq').style.display='block';
    document.getElementById('mcSummary').style.display='none';
    document.getElementById('mcNext').style.display='inline-block';
    nextMCQ();
  }
  function startMCQ(){
    const pool=favWordList().filter(w=>w[3] && w[3].trim());
    if(pool.length===0){ toast('收藏里没有带中文释义的词，先收藏一些再来 🙂'); return; }
    launchMCQ(pool);
  }
  function startReview(){
    const now=Date.now();
    let due=favWordList().filter(w=>{ if(!(w[3]&&w[3].trim())) return false; const s=stats[w[0]]; return s && (s.due||0)<=now && (s.r+s.w)>0; });
    if(!due.length){ due=favWordList().filter(w=>w[3]&&w[3].trim()); if(!due.length){ toast('收藏里没有带中文释义的词，先收藏一些再来 🙂'); return; } toast('当前没有到期词，先练最薄弱的 💪'); }
    launchMCQ(due);
  }
  function nextMCQ(){
    if(!mcqPool.length){ showMcqSummary(); return; }
    const i=Math.floor(Math.random()*mcqPool.length);
    mcqCur=mcqPool[i]; mcqPool.splice(i,1);
    const en=mcqCur[0], zh=(mcqCur[3]||'').trim();
    let promptText, opts, correctVal;
    if(mcqDir==='zh2en'){
      promptText = zh || en;
      const others=favWordList().filter(w=>w[0]!==en && w[0]);
      const dset=new Set(); let g=0;
      while(dset.size<3 && g++<600){ const c=others[Math.floor(Math.random()*others.length)]; if(c && c[0] && !dset.has(c[0])) dset.add(c[0]); }
      opts=[en, ...dset]; correctVal=en;
    } else {
      promptText = en;
      const dset=new Set(); let g=0;
      while(dset.size<3 && g++<600){ const c=WORDS[Math.floor(Math.random()*WORDS.length)]; const z=(c[3]||'').trim(); if(z && z!==zh && !dset.has(z)) dset.add(z); }
      opts=[zh, ...dset]; correctVal=zh;
    }
    for(let k=opts.length-1;k>0;k--){ const j=Math.floor(Math.random()*(k+1)); const t=opts[k]; opts[k]=opts[j]; opts[j]=t; }
    mcqCorrect=correctVal;
    document.getElementById('mcWord').textContent=promptText;
    document.getElementById('mcHint').textContent = mcqDir==='zh2en' ? '看中文释义，选出正确的英文单词（来自你的生词本）' : '听发音 / 看英文，选出正确的中文释义（来自你的生词本）';
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
    if(chosen===correct){ document.getElementById('mcResult').innerHTML='<span style="color:#2e7d32">✓ 正确！</span>'; mcqScore.c++; recordResult(mcqCur[0], true); }
    else { document.getElementById('mcResult').innerHTML='<span style="color:#b3261e">✗ 正确是：'+esc(correct)+'</span>'; mcqWrong.push(mcqCur); recordResult(mcqCur[0], false); }
    updateMcqScore();
  }
  function exitMCQ(){
    document.getElementById('mcq').style.display='none';
    document.getElementById('list').style.display='block';
    document.querySelector('.modes').style.display='flex';
    render();
  }
  function showMcqSummary(){
    bumpStreak();
    const c=mcqScore.c, t=mcqScore.t, wrong=t-c;
    document.getElementById('mcSumText').innerHTML = t===0 ? '本轮没有题目' : ('本轮完成：对 <span style="color:#2e7d32">'+c+'</span> / 错 <span style="color:#c0392b">'+wrong+'</span>'+(wrong===0?' 🎉 全对！':''));
    const list=document.getElementById('mcSumList');
    if(mcqWrong.length){
      list.innerHTML = '<div style="color:#5a6b85;font-size:13px;margin-bottom:6px">答错的词（建议重点复习）：</div>' + mcqWrong.map(w=>'<div class="weak-item"><span class="wk-en">'+esc(w[0])+'</span> <span class="wk-ipa">'+esc(w[1])+'</span> <span class="wk-zh">'+esc(w[3]||'')+'</span></div>').join('');
    } else {
      list.innerHTML = '<div class="empty" style="margin-top:6px">本轮没有答错的词，棒 👍</div>';
    }
    document.getElementById('mcRedrill').style.display = mcqWrong.length ? 'inline-block' : 'none';
    document.getElementById('mcWord').textContent='';
    document.getElementById('mcOpts').innerHTML='';
    document.getElementById('mcResult').textContent='';
    document.getElementById('mcNext').style.display='none';
    document.getElementById('mcSummary').style.display='block';
    updateMcqScore();
  }
  function redrillWrong(){
    if(!mcqWrong.length){ exitMCQ(); return; }
    const pool=mcqWrong.slice();
    document.getElementById('mcSummary').style.display='none';
    launchMCQ(pool);
  }

  /* ---------- 生词本学习统计 + 薄弱词优先 ---------- */
  let stats=JSON.parse(localStorage.getItem('vd_stats')||'{}');
  function saveStats(){ try{ localStorage.setItem('vd_stats', JSON.stringify(stats)); }catch(e){} }
  function recordResult(en, ok){
    const s=stats[en]||{r:0,w:0,t:0,ivl:0,due:0,reps:0}; const now=Date.now();
    if(ok){ s.r++; s.reps++; s.ivl = s.ivl<=0 ? 1 : Math.min(Math.round(s.ivl*2), 30); s.due = now + s.ivl*86400000; }
    else { s.w++; s.reps=0; s.ivl=0; s.due=0; }
    s.t=now; stats[en]=s; saveStats();
  }
  function dueCmp(a,b){
    const sa=stats[a[0]]||{ivl:0,due:0,w:0,r:0}, sb=stats[b[0]]||{ivl:0,due:0,w:0,r:0};
    const now=Date.now();
    const oa=(sa.due||0)<=now?0:1, ob=(sb.due||0)<=now?0:1;   // 0=到期/逾期优先
    if(oa!==ob) return oa-ob;
    return (sb.w-sb.r)-(sa.w-sa.r) || ((sa.due||0)-(sb.due||0));
  }
  function fmtDue(due){
    if(!due) return '待练';
    const days=Math.ceil((due-Date.now())/86400000);
    if(days<=0) return '今天'; if(days===1) return '明天';
    if(days<30) return days+'天后'; return '已巩固';
  }
  function statCard(label,val,color){ return '<div class="stat-card"'+(color?' style="color:'+color+'"':'')+'><div class="sc-val">'+val+'</div><div class="sc-lab">'+label+'</div></div>'; }
  function openStats(){ renderStats(); document.getElementById('stats').style.display='block'; document.getElementById('list').style.display='none'; document.querySelector('.modes').style.display='none'; }
  function exitStats(){ document.getElementById('stats').style.display='none'; document.getElementById('list').style.display='block'; document.querySelector('.modes').style.display='flex'; render(); }
  function renderStats(){
    const favArr=[...favs]; let tested=0, mastered=0, dueN=0; const rows=[]; const now=Date.now();
    for(const en of favArr){
      const s=stats[en]; const r=s?(s.r||0):0, w=s?(s.w||0):0, due=s?(s.due||0):0;
      if(r+w>0) tested++;
      if(r>=2 && w===0) mastered++;
      if((r+w>0) && due<=now) dueN++;
      const wd=WORDS.find(z=>z[0]===en);
      rows.push({ en, r, w, due, weak:(w-r), ipa:wd?wd[1]:'', zh:wd?(wd[3]||''):'' });
    }
    const total=favArr.length, untested=total-tested;
    document.getElementById('statCards').innerHTML =
      statCard('收藏', total) + statCard('已测验', tested) + statCard('已掌握', mastered, '#2e7d32') + statCard('待复习', dueN, '#f0a020') + statCard('未测验', untested, '#7a88a0') + statCard('连续打卡', (streak?streak.count:0)+'天', '#f0a020');
    rows.sort((a,b)=> (b.due>now?1:0)-(a.due>now?1:0) || b.weak - a.weak);
    const list=rows.slice(0,15);
    document.getElementById('weakList').innerHTML = list.map(x=>
      '<div class="weak-item"><span class="wk-en">'+esc(x.en)+'</span> <span class="wk-ipa">'+esc(x.ipa)+'</span> <span class="wk-zh">'+esc(x.zh)+'</span> <span class="badge">对'+x.r+'/错'+x.w+' · '+fmtDue(x.due)+'</span></div>'
    ).join('') || '<div class="empty" style="margin-top:10px">还没有测验记录，去做几道题吧</div>';
  }

  /* ---------- 生词本错题本 + 错词专项练习 ---------- */
  function openMistakes(){
    renderMistakes();
    document.getElementById('mistakes').style.display='block';
    document.getElementById('list').style.display='none';
    document.querySelector('.modes').style.display='none';
  }
  function exitMistakes(){
    document.getElementById('mistakes').style.display='none';
    document.getElementById('list').style.display='block';
    document.querySelector('.modes').style.display='flex';
    render();
  }
  function mistakeEntries(){
    const arr=[];
    for(const en of favs){
      const s=stats[en];
      if(s && s.w>0){
        const wd=WORDS.find(z=>z[0]===en);
        if(wd) arr.push({ wd, w:s.w, r:s.r||0, due:s.due||0 });
      }
    }
    arr.sort((a,b)=> b.w-a.w || (b.due>Date.now()?1:0)-(a.due>Date.now()?1:0));
    return arr;
  }
  function renderMistakes(){
    const arr=mistakeEntries();
    document.getElementById('mistakeCount').textContent = arr.length ? ('共 '+arr.length+' 个曾经答错过的词') : '还没有答错过任何词，继续保持 💪';
    document.getElementById('drillBtn').style.display = arr.length ? 'inline-block' : 'none';
    document.getElementById('mistakeList').innerHTML = arr.map(x=>
      '<div class="weak-item"><span class="wk-en">'+esc(x.wd[0])+'</span> <span class="wk-ipa">'+esc(x.wd[1])+'</span> <span class="wk-zh">'+esc(x.wd[3]||'')+'</span> <span class="badge">对'+x.r+'/错'+x.w+' · '+fmtDue(x.due)+'</span></div>'
    ).join('') || '<div class="empty" style="margin-top:10px">还没有测验记录</div>';
  }
  function startMistakeDrill(){
    const arr=mistakeEntries();
    if(!arr.length){ toast('错题本里还没有词，先去做几道题 🙂'); return; }
    document.getElementById('mistakes').style.display='none';
    launchMCQ(arr.map(o=>o.wd));
  }

  /* ---------- 每日打卡（连续练习 streak） ---------- */
  let streak=JSON.parse(localStorage.getItem('vd_streak')||'null');
  function saveStreak(){ try{ localStorage.setItem('vd_streak', JSON.stringify(streak)); }catch(e){} }
  function todayStr(){ const d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
  function bumpStreak(){
    const t=todayStr();
    if(!streak) streak={last:'',count:0,best:0};
    if(streak.last===t) return;
    const y=new Date(); y.setDate(y.getDate()-1);
    const ystr=y.getFullYear()+'-'+String(y.getMonth()+1).padStart(2,'0')+'-'+String(y.getDate()).padStart(2,'0');
    streak.count = (streak.last===ystr) ? streak.count+1 : 1;
    streak.last=t; if(streak.count>(streak.best||0)) streak.best=streak.count;
    saveStreak(); updateStreakChip();
  }
  function updateStreakChip(){
    const c=streak?streak.count:0;
    const el=document.getElementById('streakChip'); if(el) el.textContent='🔥 '+c+' 天';
  }
  updateStreakChip();

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
  function exportFavsObj(){ return { app:'科莱德图解词典', type:'favorites', version:1, exportedAt:new Date().toISOString(), count:favs.size, words:[...favs], stats:stats }; }
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
      if(obj.stats && typeof obj.stats==='object'){ for(const k in obj.stats){ if(!stats[k]) stats[k]=obj.stats[k]; } saveStats(); }
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
