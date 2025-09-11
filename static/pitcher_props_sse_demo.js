// Minimal frontend demo for Pitcher Props SSE & Line History + Volatility spark
// Usage: include <script src="/static/pitcher_props_sse_demo.js"></script> in a template
// Provides window.initPitcherPropsSSE(containerId)

(function(){
  function el(tag, cls){ const e=document.createElement(tag); if(cls) e.className=cls; return e; }
  function fmt(ts){ try { return new Date(ts).toLocaleTimeString(); } catch(e){ return ts; } }

  function spark(values, width=60, height=16){
    if(!values.length) return '';
    const min=Math.min(...values), max=Math.max(...values);
    if(max-min < 1e-9) return ''.padEnd(values.length,'-');
    return values.map(v=>{ const r=(v-min)/(max-min); const idx=Math.round(r*7); return '▁▂▃▄▅▆▇█'[idx]; }).join('');
  }

  function init(containerId){
    const root = document.getElementById(containerId);
    if(!root){ console.warn('Pitcher SSE container not found'); return; }
    root.innerHTML = '';
    const status = el('div','ppsse-status'); root.appendChild(status);
    const eventsDiv = el('div','ppsse-events'); root.appendChild(eventsDiv);
    const volDiv = el('div','ppsse-vol'); root.appendChild(volDiv);

    function setStatus(msg){ status.textContent = '[Pitcher SSE] '+msg; }

    async function loadVol(){
      try {
        const r = await fetch('/api/pitcher-props/model-diagnostics');
        const j = await r.json();
        if(!j.success) return;
        const vol = j.volatility || {};
        const lines=[];
        Object.entries(vol).forEach(([p, mkts])=>{
          Object.entries(mkts).forEach(([mk, info])=>{
            if(info && typeof info==='object' && info.var!=null){
              lines.push({p, mk, std: Math.sqrt(Math.max(0, info.var))});
            }
          });
        });
        lines.sort((a,b)=> b.std - a.std);
        volDiv.innerHTML = '<h4>Top Volatility (Std)</h4>' + lines.slice(0,10).map(x=>`${x.p} ${x.mk}: ${x.std.toFixed(2)}`).join('<br/>');
      }catch(e){ /* ignore */ }
    }

    loadVol();
    setInterval(loadVol, 60_000);

    const es = new EventSource('/api/pitcher-props/stream');
    es.onopen = ()=> setStatus('connected');
    es.onerror = ()=> setStatus('disconnected (retrying)');
    es.onmessage = ev => {
      try {
        const data = JSON.parse(ev.data);
        if(data.type === 'heartbeat') return; // skip spam
        const row = el('div','ppsse-ev');
        row.textContent = `${fmt(data.ts)} ${data.type} ${data.pitcher||''} ${data.market||''} ${data.old_line||''} -> ${data.new_line||''}`;
        eventsDiv.prepend(row);
        while(eventsDiv.childElementCount > 120) eventsDiv.removeChild(eventsDiv.lastChild);
      } catch(e){}
    };
  }

  window.initPitcherPropsSSE = init;
})();
