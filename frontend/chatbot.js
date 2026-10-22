(() => {
  "use strict";
  if (document.getElementById("jalsetu-chat-launcher")) return;

  const apiBase = window.JALSETU_API_BASE + "/api";
  const style = document.createElement("style");
  style.textContent = `
    #jalsetu-chat-launcher{position:fixed;right:22px;bottom:22px;z-index:9998;
      border:0;border-radius:999px;padding:14px 19px;background:#087eae;color:white;
      box-shadow:0 8px 28px #102a4340;font:600 15px system-ui;cursor:pointer}
    #jalsetu-chat-panel{position:fixed;right:22px;bottom:84px;z-index:9999;
      width:min(370px,calc(100vw - 28px));height:min(510px,calc(100dvh - 115px));
      background:#fff;color:#243b53;border:1px solid #d8e6ee;border-radius:18px;
      box-shadow:0 18px 60px #102a4330;display:none;overflow:hidden;
      font:14px/1.45 system-ui,-apple-system,sans-serif}
    #jalsetu-chat-panel.open{display:flex;flex-direction:column}
    .js-chat-head{background:#102a43;color:white;padding:15px 16px;
      display:flex;align-items:center;justify-content:space-between;gap:10px}
    .js-chat-head strong{font-size:16px}.js-chat-head small{display:block;color:#c9e6f3}
    #js-chat-close{background:transparent;color:white;border:0;font-size:24px;cursor:pointer}
    .js-chat-suggestions{padding:10px;display:flex;gap:7px;flex-wrap:wrap;border-bottom:1px solid #e1eaf1}
    .js-chat-suggestions button{border:1px solid #c8e4ed;background:#f0fbfd;color:#075985;
      border-radius:18px;padding:6px 9px;font-size:12px;cursor:pointer}
    #js-chat-messages{padding:13px;overflow:auto;flex:1;background:#f7fafc}
    .js-chat-msg{white-space:pre-wrap;overflow-wrap:anywhere;max-width:94%;
      padding:10px 12px;border-radius:13px;margin:0 0 10px}
    .js-chat-msg.bot{background:white;border:1px solid #e1eaf1;border-top-left-radius:4px}
    .js-chat-msg.user{background:#087eae;color:white;margin-left:auto;border-top-right-radius:4px}
    .js-chat-form{display:flex;gap:8px;padding:10px;border-top:1px solid #e1eaf1}
    #js-chat-input{min-width:0;flex:1;border:1px solid #cbd8e3;border-radius:10px;
      padding:10px;font:inherit}
    #js-chat-send{border:0;border-radius:10px;padding:10px 13px;background:#087eae;color:white;
      font:600 14px system-ui;cursor:pointer}
    #js-chat-send:disabled{opacity:.6;cursor:wait}
    .js-chat-note{font-size:11px;color:#627d98;padding:0 12px 8px;background:#fff}
    @media(max-width:480px){#jalsetu-chat-launcher{right:14px;bottom:14px}
      #jalsetu-chat-panel{right:10px;bottom:75px}}
  `;
  document.head.appendChild(style);

  const launcher = document.createElement("button");
  launcher.id = "jalsetu-chat-launcher";
  launcher.type = "button";
  launcher.textContent = "💧 Ask JalSetu";
  launcher.setAttribute("aria-controls", "jalsetu-chat-panel");
  launcher.setAttribute("aria-expanded", "false");

  const panel = document.createElement("section");
  panel.id = "jalsetu-chat-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "JalSetu support chat");
  panel.innerHTML = `
    <div class="js-chat-head">
      <div><strong>JalSetu Support</strong><small>How can we help you?</small></div>
      <button id="js-chat-close" type="button" aria-label="Close chat">×</button>
    </div>
    <div class="js-chat-suggestions">
      <button type="button">File a complaint</button>
      <button type="button">Track my complaint</button>
      <button type="button">No water supply</button>
      <button type="button">Water quality</button>
    </div>
    <div id="js-chat-messages" aria-live="polite"></div>
    <div class="js-chat-note">Support guidance only · Do not share passwords or private tokens.</div>
    <form class="js-chat-form" id="js-chat-form">
      <input id="js-chat-input" maxlength="1000" autocomplete="off"
        placeholder="Type your question…" aria-label="Your question" required>
      <button id="js-chat-send" type="submit">Send</button>
    </form>`;
  document.body.append(launcher, panel);

  const messages = panel.querySelector("#js-chat-messages");
  const input = panel.querySelector("#js-chat-input");
  const send = panel.querySelector("#js-chat-send");

  function addMessage(text, who) {
    const item = document.createElement("div");
    item.className = "js-chat-msg " + who;
    item.textContent = text;
    messages.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
  }

  function setOpen(open) {
    panel.classList.toggle("open", open);
    launcher.setAttribute("aria-expanded", String(open));
    launcher.textContent = open ? "💧 Close chat" : "💧 Ask JalSetu";
    if (open) input.focus();
  }

  launcher.addEventListener("click", () => setOpen(!panel.classList.contains("open")));
  panel.querySelector("#js-chat-close").addEventListener("click", () => setOpen(false));
  panel.querySelectorAll(".js-chat-suggestions button").forEach(button => {
    button.addEventListener("click", () => {
      input.value = button.textContent;
      panel.querySelector("#js-chat-form").requestSubmit();
    });
  });

  addMessage("Hi! I can guide you through complaints, tracking, account access, and common water-supply issues. What do you need help with?", "bot");

  panel.querySelector("#js-chat-form").addEventListener("submit", async event => {
    event.preventDefault();
    const question = input.value.trim();
    if (!question || send.disabled) return;
    addMessage(question, "user");
    input.value = "";
    send.disabled = true;
    send.textContent = "…";
    try {
      const response = await fetch(apiBase + "/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: question})
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Support is temporarily unavailable.");
      addMessage(data.answer || "Sorry, I couldn't find an answer. Please try again.", "bot");
    } catch (error) {
      addMessage("I couldn't connect to JalSetu support. Please check that the backend is running, then try again. " + error.message, "bot");
    } finally {
      send.disabled = false;
      send.textContent = "Send";
      input.focus();
    }
  });
})();