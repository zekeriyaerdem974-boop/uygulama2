export async function jget(url){ const r=await fetch(url); if(!r.ok) return { ok:false, error:`HTTP ${r.status}` }; return r.json(); }
export function fmt(n,d=2){ if(n===null||n===undefined||isNaN(n))return'--'; return Number(n).toLocaleString('en-US',{maximumFractionDigits:d}); }
export function toLocalISO(iso){ if(!iso)return'--'; const d=new Date(iso); return d.toLocaleString(); }
