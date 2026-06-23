async function apiChat(payload){
  const r = await fetch('/api/chat',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  return r.json();
}
function renderMsg(role, content){
  const box = document.getElementById('chat-box');
  const bubble = document.createElement('div');
  bubble.className = `p-3 rounded-xl ${role==='user' ? 'bg-neutral-800 self-end':'bg-neutral-950 border border-neutral-800'}`;
  bubble.innerHTML = `<div class="text-xs text-neutral-400 mb-1">${role}</div><div class="whitespace-pre-wrap">${content}</div>`;
  box.appendChild(bubble); box.scrollTop = box.scrollHeight;
}
document.getElementById('send-btn')?.addEventListener('click', async ()=>{
  const ta = document.getElementById('user-input');
  const model = document.getElementById('model').value.trim();
  const useWeb = document.getElementById('use-web').checked;
  const q = ta.value.trim(); if(!q) return;
  renderMsg('user', q); ta.value='';
  const payload = { model, messages:[{role:'user', content:q}], tools:{ web_search: useWeb } };
  const res = await apiChat(payload);
  if(!res.ok){ renderMsg('assistant', 'Hata: '+(res.error||'bilinmeyen')); return; }
  renderMsg('assistant', res.data.response);
});
