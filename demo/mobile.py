import json

PHONE_WIDTH = "640px"

ALERT = """
<dialog class="dw-alert" aria-labelledby="dw-alert-heading">
  <header class="dw-alert__bar">
    <h2 id="dw-alert-heading">Answer</h2>
    <button type="button" class="dw-alert__close" aria-label="Close" data-dw-alert-close>
      &times;
    </button>
  </header>
  <div class="dw-alert__body" aria-live="polite"></div>
  <form class="dw-alert__reply" data-dw-alert-reply>
    <label class="dw-alert__label" for="dw-alert-input">Reply or ask something else</label>
    <div class="dw-alert__row">
      <textarea id="dw-alert-input" rows="1" maxlength="300"
        placeholder="Type a message"></textarea>
      <button type="submit" class="dw-alert__send">Send</button>
    </div>
  </form>
</dialog>
"""

SCRIPT_TEMPLATE = """
<script>
(() => {
  const PHONE = window.matchMedia("(max-width: %(width)s)");
  const PLACEHOLDER = %(placeholder)s;
  const ALERT = %(alert)s;
  let lastShown = PLACEHOLDER;

  function mountAlert() {
    const holder = document.createElement("div");
    holder.innerHTML = ALERT;
    const alert = holder.firstElementChild;
    document.body.appendChild(alert);

    const body = alert.querySelector(".dw-alert__body");
    const form = alert.querySelector("[data-dw-alert-reply]");
    const input = form.querySelector("textarea");
    const send = form.querySelector("button");

    alert.querySelector("[data-dw-alert-close]").addEventListener("click", () => alert.close());
    alert.addEventListener("click", (event) => { if (event.target === alert) alert.close(); });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();
      const question = document.querySelector("#dw-question textarea");
      const ask = document.querySelector("#dw-ask");
      if (!text || !question || !ask || send.disabled) return;

      question.value = text;
      question.dispatchEvent(new Event("input", { bubbles: true }));
      ask.click();

      const asked = document.createElement("blockquote");
      asked.textContent = text;
      const waiting = document.createElement("p");
      waiting.className = "dw-alert__waiting";
      waiting.textContent = "Thinking…";
      body.replaceChildren(asked, waiting);
      input.value = "";
      send.disabled = true;
    });

    return { alert, body, send };
  }

  function watchAnswers(answer, view) {
    let settle;
    new MutationObserver(() => {
      clearTimeout(settle);
      settle = setTimeout(() => {
        const prose = answer.querySelector(".prose");
        const text = prose?.innerText.trim() ?? "";
        if (!PHONE.matches || !text || text === lastShown) return;
        lastShown = text;
        view.body.innerHTML = prose.innerHTML;
        view.body.scrollTop = 0;
        view.send.disabled = false;
        if (!view.alert.open) view.alert.showModal();
      }, 250);
    }).observe(answer, { subtree: true, childList: true, characterData: true });
  }

  const ready = setInterval(() => {
    const answer = document.querySelector(".dw-answer");
    const behind = document.querySelector(".dw-behind .label-wrap");
    if (!answer || !behind) return;
    clearInterval(ready);
    if (PHONE.matches && behind.classList.contains("open")) behind.click();
    document.documentElement.classList.add("dw-behind-ready");
    watchAnswers(answer, mountAlert());
  }, 200);
})();
</script>
"""


def script(placeholder: str) -> str:
    return SCRIPT_TEMPLATE % {
        "width": PHONE_WIDTH,
        "placeholder": json.dumps(placeholder.strip()),
        "alert": json.dumps(ALERT.strip()).replace("</", "<\\/"),
    }


CSS = f"""
:root {{
  --dw-button: #201f1d; --dw-button-hover: #3a3835; --dw-button-text: #faf8f4;
}}
.dark {{
  --dw-button: #e1ad66; --dw-button-hover: #ecc188; --dw-button-text: #1b1a18;
}}

@media (min-width: calc({PHONE_WIDTH} + 1px)) {{
  .dw-behind .label-wrap {{ display: none !important; }}
  .dw-behind {{ border: 0 !important; padding: 0 !important; background: none !important; }}
}}

@media (max-width: {PHONE_WIDTH}) {{
  .dw-behind-heading {{ display: none !important; }}
  html:not(.dw-behind-ready) .dw-behind .label-wrap ~ * {{ visibility: hidden; max-height: 0; }}
  .dw-behind .label-wrap span {{
    font-family: "Cormorant Garamond", Georgia, serif; font-size: 20px; font-weight: 500;
  }}
}}

.dw-alert {{
  margin: auto auto 0; width: 100%; max-width: 100%; max-height: 85vh; padding: 0;
  display: none; flex-direction: column; color: var(--dw-ink); background: var(--dw-raised);
  border: 1px solid var(--dw-line); border-top: 4px solid var(--dw-gold);
  border-radius: 1rem 1rem 0 0; font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif;
}}
.dw-alert[open] {{ display: flex; animation: dw-rise 0.32s var(--dw-ease-out-quint); }}
.dw-alert::backdrop {{ background: rgb(0 0 0 / 0.55); backdrop-filter: blur(2px); }}
.dw-alert__bar {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.1rem 0.6rem; border-bottom: 1px solid var(--dw-line);
}}
.dw-alert__bar h2 {{
  margin: 0; font-family: "Cormorant Garamond", Georgia, serif; font-weight: 500;
  font-size: 1.4rem; color: var(--dw-ink);
}}
.dw-alert__close {{
  padding: 0; font-size: 1.6rem; line-height: 1; color: var(--dw-muted);
  background: none; border: 0; cursor: pointer;
}}
.dw-alert__body {{ flex: 1; min-height: 0; overflow-y: auto; padding: 0.9rem 1.1rem; }}
.dw-alert__body p, .dw-alert__body li {{ margin: 0 0 0.6rem; }}
.dw-alert__body blockquote {{
  margin: 0 0 0.8rem; padding: 0 0 0.6rem; border: 0; border-bottom: 1px solid var(--dw-gold);
  color: var(--dw-muted); font-style: italic;
}}
.dw-alert__body a {{ color: var(--dw-gold); }}
.dw-alert__waiting {{ color: var(--dw-muted); animation: dw-pulse 1.4s ease-in-out infinite; }}

.dw-alert__reply {{ padding: 0.7rem 1.1rem 1rem; border-top: 1px solid var(--dw-line); }}
.dw-alert__label {{
  display: block; margin-bottom: 0.35rem; font-size: 0.75rem; font-weight: 700;
  color: var(--dw-muted);
}}
.dw-alert__row {{ display: flex; gap: 0.5rem; align-items: flex-end; }}
.dw-alert__row textarea {{
  flex: 1; min-height: 2.6rem; max-height: 8rem; padding: 0.6rem 0.75rem; resize: none;
  font: inherit; color: var(--dw-ink); background: var(--dw-paper, transparent);
  border: 1px solid var(--dw-line); border-radius: 0.375rem; field-sizing: content;
}}
.dw-alert__row textarea:focus {{ outline: 2px solid var(--dw-gold); outline-offset: 1px; }}
.dw-alert__send {{
  padding: 0 1.1rem; height: 2.6rem; font: inherit; font-weight: 600;
  color: var(--dw-button-text); background: var(--dw-button);
  border: 0; border-radius: 0.375rem; cursor: pointer;
}}
.dw-alert__send:hover {{ background: var(--dw-button-hover); }}
.dw-alert__send:disabled {{ opacity: 0.5; cursor: wait; }}

@keyframes dw-rise {{ from {{ transform: translateY(100%); }} to {{ transform: translateY(0); }} }}
@keyframes dw-pulse {{ 50% {{ opacity: 0.45; }} }}
@media (prefers-reduced-motion: reduce) {{
  .dw-alert[open], .dw-alert__waiting {{ animation: none; }}
}}
"""
