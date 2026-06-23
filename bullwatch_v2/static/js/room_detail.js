/* room_detail.js — FAZ 34 — Room detail + WebSocket chat IIFE */
window.RD = (function () {
  "use strict";

  const slug = document.querySelector('meta[name="room-slug"]')?.content || "";
  let room = null;
  let ws = null;
  let reconnectTimer = null;

  document.addEventListener("DOMContentLoaded", () => { if (slug) loadRoom(); });

  function $(id) { return document.getElementById(id); }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function timeStr(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  }

  async function api(url, opts) {
    try {
      const r = await fetch(url, opts);
      return await r.json();
    } catch { return { ok: false }; }
  }

  async function loadRoom() {
    const data = await api("/api/room/" + encodeURIComponent(slug));
    if (!data.ok) {
      $("rdContent").innerHTML = '<div class="rd-loading">Oda bulunamadı</div>';
      return;
    }
    room = data.room;
    render(data.room, data.participants, data.messages);
    connectWS();
  }

  function render(r, participants, messages) {
    const letter = (r.mentor_display_name || "?")[0].toUpperCase();
    const marketLabels = { crypto: "Kripto", bist: "BIST", stocks: "Hisse", forex: "Forex", commodities: "Emtia" };
    const visLabels = { public: "Herkese Açık", followers_only: "Takipçi", subscribers_only: "Abone" };

    const activeBadge = r.is_active
      ? '<span class="rd-badge active">🔴 CANLI</span>'
      : '<span class="rd-badge inactive">Pasif</span>';
    const marketBadge = r.market ? `<span class="rd-badge market">${marketLabels[r.market] || r.market}</span>` : "";
    const visBadge = r.visibility !== "public" ? `<span class="rd-badge vis">${visLabels[r.visibility] || r.visibility}</span>` : "";

    // Actions
    let actionsHtml = "";
    if (r.is_owner) {
      if (r.is_active) {
        actionsHtml += `<button class="rd-btn rd-btn-stop" onclick="RD.stopRoom()">⏹ Yayını Durdur</button>`;
      } else {
        actionsHtml += `<button class="rd-btn rd-btn-start" onclick="RD.startRoom()">▶ Yayın Başlat</button>`;
      }
    }
    if (r.is_joined && !r.is_owner) {
      actionsHtml += `<button class="rd-btn rd-btn-leave" onclick="RD.leaveRoom()">Ayrıl</button>`;
      actionsHtml += `<button class="rd-btn rd-btn-joined">✓ Katıldı</button>`;
    }
    if (!r.is_joined && !r.is_owner) {
      actionsHtml += `<button class="rd-btn rd-btn-join" onclick="RD.joinRoom()">Katıl</button>`;
    }

    // Participants sidebar
    let pHtml = "";
    (participants || []).forEach(p => {
      pHtml += `<div class="rd-pitem"><span class="role-dot ${p.role}"></span>${escapeHtml(p.username)} <span style="color:#475569;font-size:.7rem;">${p.role === "mentor" ? "👑" : p.role === "moderator" ? "🛡" : ""}</span></div>`;
    });

    // Messages
    let msgsHtml = "";
    (messages || []).forEach(m => { msgsHtml += renderMessage(m); });

    $("rdContent").innerHTML = `
      <div class="rd-header">
        <div class="rd-header-top">
          <div class="rd-header-avatar">${letter}</div>
          <div class="rd-header-info">
            <div class="rd-header-title">${escapeHtml(r.title)}</div>
            <div class="rd-header-mentor"><a href="/mentor/${encodeURIComponent(r.mentor_username)}">${escapeHtml(r.mentor_display_name)}</a></div>
          </div>
        </div>
        <div class="rd-badges">${activeBadge}${marketBadge}${visBadge}</div>
        ${r.description ? `<div class="rd-desc">${escapeHtml(r.description)}</div>` : ""}
        <div class="rd-actions">${actionsHtml}</div>
      </div>

      <div class="rd-layout">
        <div class="rd-chat">
          <div class="rd-chat-header">
            💬 Sohbet
            <span id="rdWsStatus" class="rd-ws-status disconnected">Bağlanıyor...</span>
          </div>
          <div class="rd-chat-messages" id="rdMessages">${msgsHtml}</div>
          <div class="rd-chat-input">
            <select id="rdMsgType">
              <option value="text">💬</option>
              <option value="signal">📊</option>
              <option value="chart_share">📈</option>
            </select>
            <input type="text" id="rdMsgInput" placeholder="Mesaj yaz..." onkeydown="if(event.key==='Enter')RD.sendMessage()">
            <button onclick="RD.sendMessage()">Gönder</button>
          </div>
        </div>

        <div class="rd-sidebar">
          <div class="rd-participants">
            <h3>👥 Katılımcılar (${(participants || []).length})</h3>
            <div class="rd-plist" id="rdParticipants">${pHtml}</div>
          </div>
        </div>
      </div>
    `;

    // Scroll chat to bottom
    const mc = $("rdMessages");
    if (mc) mc.scrollTop = mc.scrollHeight;
  }

  function renderMessage(m) {
    if (m.message_type === "system") {
      return `<div class="rd-msg-system">⚙ ${escapeHtml(m.content)}</div>`;
    }
    const wrapClass = m.message_type === "signal" ? " rd-msg-signal" : m.message_type === "chart_share" ? " rd-msg-chart" : "";
    const typeIcon = m.message_type === "signal" ? "📊 " : m.message_type === "chart_share" ? "📈 " : "";
    const roleClass = m.role || "member";
    const mentorIcon = m.role === "mentor" ? " 👑" : m.role === "moderator" ? " 🛡" : "";

    return `
      <div class="rd-msg${wrapClass}">
        <div class="rd-msg-header">
          <span class="rd-msg-user ${roleClass}">${escapeHtml(m.username)}${mentorIcon}</span>
          <span class="rd-msg-time">${timeStr(m.created_at)}</span>
        </div>
        <div class="rd-msg-content">${typeIcon}${escapeHtml(m.content)}</div>
      </div>
    `;
  }

  // ── WebSocket ──────────────────────────────────────────────
  function connectWS() {
    if (!room) return;
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/ws/room/${room.id}`;

    try {
      ws = new WebSocket(url);

      ws.onopen = () => {
        const st = $("rdWsStatus");
        if (st) { st.textContent = "Bağlı"; st.className = "rd-ws-status connected"; }
        ws.send(JSON.stringify({ action: "join" }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleWSMessage(data);
        } catch {}
      };

      ws.onclose = () => {
        const st = $("rdWsStatus");
        if (st) { st.textContent = "Bağlantı kesildi"; st.className = "rd-ws-status disconnected"; }
        reconnectTimer = setTimeout(connectWS, 3000);
      };

      ws.onerror = () => {};
    } catch {}
  }

  function handleWSMessage(data) {
    const mc = $("rdMessages");
    if (!mc) return;

    if (data.type === "new_message" && data.message) {
      mc.insertAdjacentHTML("beforeend", renderMessage(data.message));
      mc.scrollTop = mc.scrollHeight;
    } else if (data.type === "system") {
      mc.insertAdjacentHTML("beforeend", `<div class="rd-msg-system">⚙ ${escapeHtml(data.content)}</div>`);
      mc.scrollTop = mc.scrollHeight;
    } else if (data.type === "user_joined") {
      mc.insertAdjacentHTML("beforeend", `<div class="rd-msg-system">${escapeHtml(data.username)} odaya katıldı</div>`);
      mc.scrollTop = mc.scrollHeight;
    } else if (data.type === "user_left") {
      mc.insertAdjacentHTML("beforeend", `<div class="rd-msg-system">${escapeHtml(data.username)} odadan ayrıldı</div>`);
      mc.scrollTop = mc.scrollHeight;
    } else if (data.type === "pong") {
      // keepalive response
    }
  }

  // ── Actions ────────────────────────────────────────────────
  async function sendMessage() {
    const input = $("rdMsgInput");
    const typeSelect = $("rdMsgType");
    if (!input || !room) return;
    const content = input.value.trim();
    if (!content) return;

    const msgType = typeSelect ? typeSelect.value : "text";

    const data = await api(`/api/room/${room.id}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, message_type: msgType }),
    });

    if (data.ok) {
      input.value = "";
      // Message will arrive via WebSocket, but also render immediately
      const mc = $("rdMessages");
      if (mc) {
        mc.insertAdjacentHTML("beforeend", renderMessage(data.message));
        mc.scrollTop = mc.scrollHeight;
      }
    }
  }

  async function joinRoom() {
    if (!room) return;
    const data = await api(`/api/room/${room.id}/join`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (data.ok) loadRoom();
  }

  async function leaveRoom() {
    if (!room) return;
    const data = await api(`/api/room/${room.id}/leave`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (data.ok) loadRoom();
  }

  async function startRoom() {
    if (!room) return;
    const data = await api(`/api/room/${room.id}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (data.ok) loadRoom();
  }

  async function stopRoom() {
    if (!room) return;
    const data = await api(`/api/room/${room.id}/stop`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (data.ok) loadRoom();
  }

  return { sendMessage, joinRoom, leaveRoom, startRoom, stopRoom };
})();
