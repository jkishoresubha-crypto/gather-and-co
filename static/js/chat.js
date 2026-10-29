/* Gather & Co. chat widget: talks to the Django assistant endpoints.
   No API keys live here – all AI calls are made by the server. */
(function () {
  "use strict";
  var root = document.getElementById("chat-widget");
  if (!root) return;

  var panel = document.getElementById("chat-panel");
  var launcher = document.getElementById("chat-launcher");
  var closeBtn = document.getElementById("chat-close");
  var log = document.getElementById("chat-log");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var sendBtn = document.getElementById("chat-send");
  var suggestions = document.getElementById("chat-suggestions");
  var pageContext = root.dataset.context || "";
  var busy = false;

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrfToken() {
    var field = form.querySelector("[name=csrfmiddlewaretoken]");
    return field ? field.value : getCookie("csrftoken");
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body)
    }).then(function (res) {
      return res.json().catch(function () { return { ok: false, error: "Unexpected response (" + res.status + ")." }; })
        .then(function (data) { data._status = res.status; return data; });
    });
  }

  function open(prompt) {
    panel.hidden = false;
    launcher.setAttribute("aria-expanded", "true");
    input.focus();
    if (prompt) { ask(prompt); }
  }
  function close() {
    panel.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
    launcher.focus();
  }

  // Render **bold** and plain URLs safely (text is escaped via textContent).
  function renderText(el, text) {
    var parts = text.split(/(\*\*[^*]+\*\*|\/inventory\/[a-z0-9-]+\/)/g);
    parts.forEach(function (part) {
      if (/^\*\*[^*]+\*\*$/.test(part)) {
        var b = document.createElement("strong"); b.textContent = part.slice(2, -2); el.appendChild(b);
      } else if (/^\/inventory\/[a-z0-9-]+\/$/.test(part)) {
        var a = document.createElement("a"); a.href = part; a.textContent = "view item"; el.appendChild(a);
      } else if (part) {
        el.appendChild(document.createTextNode(part));
      }
    });
  }

  function addMessage(kind, text) {
    var wrap = document.createElement("div");
    wrap.className = "chat-msg " + kind;
    var bubble = document.createElement("div");
    bubble.className = "bubble";
    renderText(bubble, text);
    wrap.appendChild(bubble);
    log.appendChild(wrap);
    log.scrollTop = log.scrollHeight;
    return bubble;
  }

  function addTyping() {
    var bubble = addMessage("bot", "");
    bubble.innerHTML = '<span class="typing" aria-label="Assistant is typing"><span></span><span></span><span></span></span>';
    return bubble.parentNode;
  }

  function sourceLabel(source) {
    return { ai: "AI answer grounded in our FAQ database", fallback: "FAQ database text (not AI-generated)",
             no_answer: "No verified answer found" }[source] || "";
  }

  function addFeedback(bubble, messageId) {
    var row = document.createElement("div");
    row.className = "chat-actions";
    var label = document.createElement("span");
    label.className = "chat-meta me-1"; label.textContent = "Helpful?";
    row.appendChild(label);
    [["bi-hand-thumbs-up", 5, "Yes, helpful"], ["bi-hand-thumbs-down", 1, "Not helpful"]].forEach(function (opt) {
      var btn = document.createElement("button");
      btn.type = "button"; btn.className = "btn btn-outline-secondary";
      btn.setAttribute("aria-label", opt[2]);
      btn.innerHTML = '<i class="bi ' + opt[0] + '" aria-hidden="true"></i>';
      btn.addEventListener("click", function () {
        row.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
        post(root.dataset.feedbackUrl, { message_id: messageId, rating: opt[1] }).then(function (data) {
          label.textContent = data.ok ? (data.notice || "Thanks for your feedback!") : (data.error || "Couldn't save feedback.");
        }).catch(function () { label.textContent = "Couldn't send feedback (network error)."; });
      });
      row.appendChild(btn);
    });
    bubble.appendChild(row);
  }

  function addTicketOffer(bubble, messageId) {
    var box = document.createElement("div");
    box.className = "chat-actions";
    var emailId = "ticket-email-" + messageId.slice(0, 8);
    box.innerHTML = '<label class="visually-hidden" for="' + emailId + '">Email for a reply (optional)</label>' +
      '<input type="email" id="' + emailId + '" class="form-control form-control-sm" maxlength="254" placeholder="Email for a reply (optional)">' +
      '<button type="button" class="btn btn-brand">Create support ticket</button>';
    var btn = box.querySelector("button");
    btn.addEventListener("click", function () {
      btn.disabled = true; btn.textContent = "Creating…";
      post(root.dataset.ticketUrl, { message_id: messageId, email: box.querySelector("input").value }).then(function (data) {
        if (data.ok) {
          box.innerHTML = "";
          var ok = document.createElement("div");
          ok.className = "chat-notice"; ok.setAttribute("role", "status");
          ok.textContent = "Support ticket created. Your reference is " + data.reference + ". Keep it to follow up.";
          box.appendChild(ok);
        } else {
          btn.disabled = false; btn.textContent = "Create support ticket";
          addMessage("error", data.error || "The ticket could not be created.");
        }
      }).catch(function () {
        btn.disabled = false; btn.textContent = "Create support ticket";
        addMessage("error", "Network error – the ticket could not be created. You can also use the Support page.");
      });
    });
    bubble.appendChild(box);
  }

  function ask(question) {
    question = (question || "").trim();
    if (!question || busy) return;
    if (question.length > 500) { addMessage("error", "Please keep your question under 500 characters."); return; }
    busy = true; sendBtn.disabled = true;
    if (suggestions) suggestions.hidden = true;
    addMessage("user", question);
    var typing = addTyping();
    post(root.dataset.chatUrl, { message: question, context: pageContext, path: window.location.pathname })
      .then(function (data) {
        typing.remove();
        if (!data.ok) { addMessage("error", data.error || "Something went wrong. Please try again."); return; }
        var bubble = addMessage("bot", data.answer);
        if (data.notice) {
          var n = document.createElement("div"); n.className = "chat-notice"; n.textContent = data.notice; bubble.appendChild(n);
        }
        var meta = document.createElement("div"); meta.className = "chat-meta"; meta.textContent = sourceLabel(data.source);
        bubble.appendChild(meta);
        if (data.offer_ticket) addTicketOffer(bubble, data.message_id);
        else addFeedback(bubble, data.message_id);
        pageContext = ""; // only send the error-page context with the first question
      })
      .catch(function () {
        typing.remove();
        addMessage("error", "Network error – the assistant couldn't be reached. Check your connection and try again.");
      })
      .finally(function () { busy = false; sendBtn.disabled = false; input.focus(); log.scrollTop = log.scrollHeight; });
  }

  launcher.addEventListener("click", function () { panel.hidden ? open() : close(); });
  closeBtn.addEventListener("click", close);
  panel.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  form.addEventListener("submit", function (e) { e.preventDefault(); var q = input.value; input.value = ""; ask(q); });
  document.querySelectorAll("[data-suggest]").forEach(function (b) {
    b.addEventListener("click", function () { ask(b.dataset.suggest); });
  });
  document.querySelectorAll("[data-open-chat]").forEach(function (b) {
    b.addEventListener("click", function () { open(b.dataset.chatPrompt); });
  });

  // Show a loading state on regular form submit buttons.
  document.querySelectorAll("form button[data-loading-text]").forEach(function (btn) {
    btn.form && btn.form.addEventListener("submit", function () {
      setTimeout(function () { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>' + btn.dataset.loadingText; }, 0);
    });
  });
})();
