// Assistant AuditM365 : bulle de discussion. Boutons = réponses écrites (gratuites) ;
// « Poser une autre question » = IA via /api/chat (seule partie payante, plafonnée côté serveur).
(() => {
  if (window.__auditChat) return;
  window.__auditChat = true;

  const CSS = `
  #ac-btn{position:fixed;right:20px;bottom:20px;z-index:900;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;
    background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-size:26px;box-shadow:0 8px 28px rgba(99,102,241,.45);transition:transform .2s}
  #ac-btn:hover{transform:translateY(-2px)}
  #ac-btn:focus-visible,#ac-panel button:focus-visible,#ac-panel a:focus-visible,#ac-input:focus-visible{outline:2px solid #a5b4fc;outline-offset:2px}
  #ac-panel{position:fixed;right:20px;bottom:90px;z-index:901;width:380px;max-width:calc(100vw - 32px);height:560px;max-height:calc(100vh - 120px);
    display:none;flex-direction:column;background:#0d1128;border:1px solid #2a3660;border-radius:18px;overflow:hidden;
    box-shadow:0 24px 60px rgba(0,0,0,.55);font-family:inherit;color:#e2e8f0}
  #ac-panel.open{display:flex}
  .ac-head{display:flex;align-items:center;gap:10px;padding:14px 16px;background:#111830;border-bottom:1px solid #1e2845}
  .ac-head b{flex:1;font-size:15px}
  .ac-head small{display:block;font-weight:400;color:#94a3b8;font-size:12px}
  .ac-close{background:none;border:0;color:#94a3b8;font-size:20px;cursor:pointer;padding:4px 8px;border-radius:8px}
  .ac-close:hover{color:#fff;background:#1e2845}
  #ac-log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;font-size:14px;line-height:1.5}
  .ac-msg{max-width:88%;padding:10px 13px;border-radius:14px;word-wrap:break-word}
  .ac-bot{align-self:flex-start;background:#161e38;border:1px solid #1e2845;border-bottom-left-radius:4px}
  .ac-user{align-self:flex-end;background:linear-gradient(135deg,#6366f1,#7c3aed);color:#fff;border-bottom-right-radius:4px}
  .ac-bot a{color:#a5b4fc}
  .ac-link{display:inline-block;margin-top:8px;padding:7px 12px;border-radius:10px;background:rgba(99,102,241,.18);border:1px solid rgba(99,102,241,.4);color:#c7d2fe!important;text-decoration:none;font-weight:600;font-size:13px}
  .ac-typing{color:#94a3b8;font-style:italic}
  #ac-chips{display:flex;flex-wrap:wrap;gap:6px;padding:10px 14px;border-top:1px solid #1e2845;max-height:110px;overflow-y:auto}
  .ac-chip{background:#111830;border:1px solid #2a3660;color:#cbd5e1;border-radius:100px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}
  .ac-chip:hover{border-color:#6366f1;color:#fff}
  .ac-chip.ac-ask{border-color:rgba(99,102,241,.6);color:#c7d2fe}
  #ac-form{display:none;flex-direction:column;gap:6px;padding:10px 14px 12px;border-top:1px solid #1e2845}
  #ac-form.open{display:flex}
  .ac-row{display:flex;gap:8px}
  #ac-input{flex:1;resize:none;height:42px;max-height:110px;padding:10px 12px;border-radius:12px;border:1px solid #2a3660;background:#111830;color:#e2e8f0;font:inherit;font-size:14px}
  #ac-input:focus{outline:none;border-color:#6366f1}
  #ac-send{border:0;border-radius:12px;padding:0 16px;font:inherit;font-weight:700;color:#fff;cursor:pointer;background:linear-gradient(135deg,#6366f1,#8b5cf6)}
  #ac-send:disabled{opacity:.5;cursor:wait}
  .ac-note{font-size:11px;color:#64748b;line-height:1.4}
  .ac-count{font-size:11px;color:#64748b;text-align:right}
  #ac-ts:empty{display:none}
  @media (max-width:480px){#ac-panel{right:16px;left:16px;width:auto;max-width:none;bottom:84px;height:calc(100vh - 110px)}#ac-btn{right:16px;bottom:16px}}
  `;

  const MAX = 500;
  const store = {
    get(k) { try { return JSON.parse(sessionStorage.getItem("ac:" + k)); } catch { return null; } },
    set(k, v) { try { sessionStorage.setItem("ac:" + k, JSON.stringify(v)); } catch { /* stockage indisponible */ } },
  };

  let cfg = null, faq = [], loaded = false, busy = false;
  let history = store.get("history") || [];   // échanges avec l'IA uniquement
  let transcript = store.get("transcript") || []; // affichage
  let pass = store.get("pass");
  let tsWidget = null, tsToken = null, tsWaiters = [];

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const safeHref = h => /^(\/(?!\/)|#|mailto:bonjour@m365intune\.com$|https:\/\/audit\.m365intune\.com\/)/.test(h);

  // Réponse de l'IA : texte échappé, puis liens [x](lien) autorisés, gras, puces, retours à la ligne
  function renderAI(text) {
    let h = esc(text);
    h = h.replace(/\[([^\]]{1,120})\]\(([^)\s]{1,200})\)/g, (m, t, href) => {
      const raw = href.replace(/&amp;/g, "&");
      return safeHref(raw) ? `<a href="${href}">${t}</a>` : t;
    });
    h = h.replace(/\*\*([^*]{1,200})\*\*/g, "<b>$1</b>");
    h = h.replace(/(^|\n)\s*[-*] /g, "$1• ");
    return h.replace(/\n/g, "<br>");
  }

  const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); if (html) e.innerHTML = html; return e; };

  const style = el("style"); style.textContent = CSS; document.head.appendChild(style);
  const btn = el("button", { id: "ac-btn", type: "button", title: "Une question ? Discutez avec l'assistant" }, "💬");
  btn.setAttribute("aria-label", "Ouvrir l'assistant AuditM365");
  btn.setAttribute("aria-expanded", "false");
  const panel = el("div", { id: "ac-panel" }, `
    <div class="ac-head"><span style="font-size:22px">🛡️</span><b>Assistant AuditM365<small>Réponses sur l'application, les licences et l'essai</small></b>
      <button class="ac-close" type="button" aria-label="Fermer l'assistant">✕</button></div>
    <div id="ac-log" aria-live="polite"></div>
    <div id="ac-ts" style="padding:0 14px"></div>
    <div id="ac-chips"></div>
    <form id="ac-form" novalidate>
      <div class="ac-row"><textarea id="ac-input" maxlength="${MAX}" rows="1" placeholder="Votre question…" aria-label="Votre question"></textarea>
        <button id="ac-send" type="submit">Envoyer</button></div>
      <div class="ac-count" id="ac-count">0 / ${MAX}</div>
      <div class="ac-note">Ne saisissez pas de données personnelles. Vos questions sont traitées par une IA (Anthropic) et ne sont pas conservées.</div>
    </form>`);
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Assistant AuditM365");
  document.body.append(btn, panel);

  const log = panel.querySelector("#ac-log"), chips = panel.querySelector("#ac-chips");
  const form = panel.querySelector("#ac-form"), input = panel.querySelector("#ac-input"), send = panel.querySelector("#ac-send");

  function add(role, html, save = true) {
    const m = el("div", { className: "ac-msg " + (role === "user" ? "ac-user" : "ac-bot") }, html);
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
    if (save) { transcript.push({ role, html }); transcript = transcript.slice(-40); store.set("transcript", transcript); }
    return m;
  }

  function renderChips() {
    chips.innerHTML = "";
    faq.forEach(item => {
      const c = el("button", { type: "button", className: "ac-chip", textContent: item.label });
      c.onclick = () => answerFaq(item);
      chips.appendChild(c);
    });
    if (cfg && cfg.ai) {
      const c = el("button", { type: "button", className: "ac-chip ac-ask", textContent: "✍️ Poser une autre question" });
      c.onclick = openForm;
      chips.appendChild(c);
    } else {
      const c = el("button", { type: "button", className: "ac-chip ac-ask", textContent: "✉️ Nous écrire" });
      c.onclick = () => { location.href = "mailto:bonjour@m365intune.com"; };
      chips.appendChild(c);
    }
  }

  function answerFaq(item) {
    add("user", esc(item.label));
    let html = item.answer;
    if (item.link) html += `<br><a class="ac-link" href="${esc(item.link.href)}">${esc(item.link.label)} →</a>`;
    add("bot", html);
  }

  function openForm() {
    form.classList.add("open");
    input.focus();
    if (cfg && cfg.turnstile && !pass) loadTurnstile();
  }

  function loadTurnstile() {
    if (tsWidget !== null || document.getElementById("ac-ts-script")) return;
    window.__acTsReady = () => {
      tsWidget = window.turnstile.render("#ac-ts", {
        sitekey: cfg.turnstile, appearance: "interaction-only", size: "flexible", language: "fr",
        callback: t => { tsToken = t; tsWaiters.splice(0).forEach(f => f(t)); },
        "expired-callback": () => { tsToken = null; },
        "error-callback": () => { tsToken = null; },
      });
    };
    const s = el("script", { id: "ac-ts-script", async: true, src: "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=__acTsReady" });
    document.head.appendChild(s);
  }

  function turnstileToken() {
    if (tsToken) return Promise.resolve(tsToken);
    loadTurnstile();
    return new Promise(resolve => { tsWaiters.push(resolve); setTimeout(() => resolve(null), 20000); });
  }

  async function ask(question) {
    busy = true; send.disabled = true;
    add("user", esc(question));
    const typing = add("bot", "<span class='ac-typing'>L'assistant rédige sa réponse…</span>", false);
    const msgs = history.concat([{ role: "user", content: question }]).slice(-12);
    try {
      let r, j = {};
      for (let attempt = 0; attempt < 2; attempt++) {
        const payload = { messages: msgs, pass };
        if (cfg.turnstile && !pass) {
          payload.turnstile = await turnstileToken();
          if (!payload.turnstile) { j = { error: "challenge" }; break; }  // vérification non passée : inutile d'appeler le serveur
        }
        r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        j = await r.json().catch(() => ({}));
        if (j.error === "challenge") {   // laisser-passer expiré : nouveau jeton anti-robot
          pass = null; store.set("pass", null); tsToken = null;
          if (window.turnstile && tsWidget !== null) window.turnstile.reset(tsWidget);
          continue;
        }
        break;
      }
      if (j.pass) { pass = j.pass; store.set("pass", pass); }
      tsToken = null;
      if (j.error === "challenge") {
        typing.remove();
        add("bot", "🔒 Vérification anti-robot nécessaire : si une case apparaît au-dessus des boutons, cochez-la, puis renvoyez votre question.", false);
        input.value = question;
        if (window.turnstile && tsWidget !== null) window.turnstile.reset(tsWidget);
        return;
      }
      const reply = j.reply || "Je ne peux pas répondre pour le moment. Écrivez-nous à bonjour@m365intune.com.";
      typing.remove();
      add("bot", renderAI(reply));
      if (r.ok && !j.fallback) {
        history = msgs.concat([{ role: "assistant", content: reply }]).slice(-12);
        store.set("history", history);
      }
    } catch {
      typing.remove();
      add("bot", renderAI("La connexion a échoué. Réessayez dans un instant ou écrivez à [bonjour@m365intune.com](mailto:bonjour@m365intune.com)."));
    } finally {
      busy = false; send.disabled = false; input.focus();
    }
  }

  form.addEventListener("submit", e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || busy) return;
    input.value = ""; panel.querySelector("#ac-count").textContent = `0 / ${MAX}`;
    ask(q.slice(0, MAX));
  });
  input.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  input.addEventListener("input", () => { panel.querySelector("#ac-count").textContent = `${input.value.length} / ${MAX}`; });

  async function init() {
    if (loaded) return;
    loaded = true;
    const [c, f] = await Promise.all([
      fetch("/api/chat/config").then(r => r.json()).catch(() => ({ ai: false })),
      fetch("/chat/faq.json").then(r => r.json()).catch(() => ({ items: [] })),
    ]);
    cfg = c; faq = f.items || [];
    if (cfg.turnstile && !pass) loadTurnstile(); // jeton anti-robot prêt avant la première question
    if (transcript.length) transcript.forEach(m => add(m.role, m.html, false));
    else add("bot", "Bonjour 👋 Je réponds à vos questions sur AuditM365. Choisissez un sujet ci-dessous" + (cfg.ai ? " ou posez votre question." : "."));
    renderChips();
  }

  function toggle(open) {
    panel.classList.toggle("open", open);
    btn.setAttribute("aria-expanded", String(open));
    btn.textContent = open ? "✕" : "💬";
    if (open) init();
  }
  btn.onclick = () => toggle(!panel.classList.contains("open"));
  panel.querySelector(".ac-close").onclick = () => { toggle(false); btn.focus(); };
  document.addEventListener("keydown", e => { if (e.key === "Escape" && panel.classList.contains("open")) { toggle(false); btn.focus(); } });
})();
