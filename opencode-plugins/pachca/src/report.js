/**
 * Standalone HTML report renderer — form v2.2.
 *
 * Invariants:
 * - no external CSS, JS, fonts, images or network requests (no fetch/XHR/WebSocket);
 * - every user-controlled string is escaped;
 * - numbers are computed before rendering, not in the model prompt;
 * - excluded participants are absent from the chart but visible in a panel;
 * - the HTML never stores a token: an enabled «Отправить» button only queues a
 *   message into .pachca/outbox/ (File System Access API, download fallback);
 *   the plugin/agent sends it via pachca_send_message after a separate user
 *   confirmation and a scope/role preflight.
 *
 * Section order: summary → personal actions (optional) → projects → activity →
 * tasks → method. Draft boxes sit under every blocker and every personal
 * action item; buttons are disabled unless the token has messages:create.
 */

import {
  asArray,
  asNumber,
  asString,
  daysWord,
  escapeHtml,
  escapeJson,
  formatDate,
  formatDay,
  parseDate,
  truncate,
} from "./util.js";

const STATUS = {
  on_track: { label: "В графике", className: "ok" },
  at_risk: { label: "Риск", className: "warn" },
  blocked: { label: "Блокер", className: "bad" },
  unknown: { label: "Нет данных", className: "muted" },
};

const CONFIDENCE = {
  high: "высокая",
  medium: "средняя",
  low: "низкая",
};

const SEV_LABEL = { high: "высокая", medium: "средняя", low: "низкая" };
const SEV_ORDER = { high: 0, medium: 1, low: 2 };

const KIND_LABEL = {
  reply: "ответ на обращение",
  approval: "аппрув",
  answer_request: "ваш запрос без ответа",
  followup: "без ответа",
  decision: "решение",
  project: "движение по проекту",
  process: "процесс",
};

function safeUrl(value) {
  const url = asString(value);
  return /^https:\/\/app\.pachca\.com\//.test(url) ? url : "";
}

function statusBadge(status) {
  const item = STATUS[status] || STATUS.unknown;
  return `<span class="badge ${item.className}">${escapeHtml(item.label)}</span>`;
}

function confidenceBadge(value) {
  return `<span class="badge quiet">уверенность: ${escapeHtml(CONFIDENCE[value] || "низкая")}</span>`;
}

function pct(part, total) {
  if (!total) return 0;
  return Math.max(0, Math.min(100, Math.round((part / total) * 100)));
}

function utcDay(value) {
  const date = parseDate(value);
  return date ? date.toISOString().slice(0, 10) : null;
}

function channelLabel(snapshot, chatId, hint = "") {
  const chat = snapshot.chats.find((item) => item.id === String(chatId));
  if (chat?.personal) {
    const person = asString(hint).replace(/личный чат/gi, "").replace(/[()]/g, "").trim();
    return person ? `Личный чат · ${person}` : "Личный чат";
  }
  return chat?.name || asString(hint) || `чат ${chatId}`;
}

function draftBox(snapshot, { chatId, text, hint = "", ref }, sendEnabled) {
  const chan = channelLabel(snapshot, chatId, hint);
  const attrs = sendEnabled
    ? ""
    : ` disabled title="Токен только на чтение: нет скоупа messages:create"`;
  const sendHint = sendEnabled
    ? "очередь .pachca/outbox/ → ваше подтверждение → pachca_send_message"
    : "недоступно: токен только на чтение (нет messages:create)";
  return `<div class="draft-box">
      <div class="draft-head"><span class="draft-h">Черновик сообщения · редактируемый</span><span class="chan">Канал: <b>${escapeHtml(chan)}</b> · #${escapeHtml(chatId)}</span></div>
      <textarea class="draft-edit" rows="4" spellcheck="false">${escapeHtml(text)}</textarea>
      <div class="send-row"><button type="button" class="send-btn" data-chat="${escapeHtml(chatId)}" data-chan="${escapeHtml(chan)}" data-ref="${escapeHtml(ref)}"${attrs}>Отправить</button><span class="send-hint">${escapeHtml(sendHint)}</span></div>
    </div>`;
}

function renderEvidence(project) {
  const evidence = asArray(project.evidence);
  if (!evidence.length) {
    return `<p class="empty">Нет цитат: вывод не подтверждён сообщениями.</p>`;
  }
  return `<ul class="evidence">${evidence
    .map((message) => {
      const href = safeUrl(message.url);
      const link = href
        ? `<a href="${escapeHtml(href)}" rel="noreferrer">${escapeHtml(formatDate(message.createdAt))}</a>`
        : escapeHtml(formatDate(message.createdAt));
      return `<li><div class="ev-head">${link}<span>${escapeHtml(message.userName || `Сотрудник ${message.userId}`)}</span></div><blockquote>${escapeHtml(message.excerpt || truncate(message.content, 260))}</blockquote></li>`;
    })
    .join("")}</ul>`;
}

function renderProject(project, snapshot, sendEnabled) {
  const blockers = asArray(project.blockers);
  const nextSteps = asArray(project.nextSteps);
  const points = asArray(project.progressPoints);
  const kicker = project.chatName && project.chatName !== project.project ? project.chatName : "Проект";
  const progressHtml = points.length
    ? `<ul class="prog">${points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>`
    : `<p class="progress">${escapeHtml(project.progress)}</p>`;
  const blockersHtml = blockers.length
    ? `<ul class="blockers">${blockers
        .map(
          (blocker, index) =>
            `<li><span class="severity ${escapeHtml(blocker.severity)}">${escapeHtml(blocker.severity)}</span><div class="blocker-body"><span>${escapeHtml(blocker.text || "Без описания")}</span>${blocker.verified ? "" : `<em class="unverified">без подтверждённой цитаты</em>`}<details class="draft-details"><summary>Черновик сообщения → канал: ${escapeHtml(channelLabel(snapshot, project.chatId))}</summary>${draftBox(
              snapshot,
              {
                chatId: project.chatId,
                text: asString(blocker.draft ?? ""),
                ref: `blocker:${project.project}:${index + 1}`,
              },
              sendEnabled,
            )}</details></div></li>`,
        )
        .join("")}</ul>`
    : `<p class="empty">—</p>`;
  return `<article class="project" data-status="${escapeHtml(project.status)}">
    <div class="project-head">
      <div>
        <p class="eyebrow">${escapeHtml(kicker)}</p>
        <h3>${escapeHtml(project.project)}</h3>
      </div>
      <div class="project-badges">${statusBadge(project.status)}${confidenceBadge(project.confidence)}</div>
    </div>
    ${progressHtml}
    <div class="project-grid">
      <div>
        <h4>Блокеры</h4>
        ${blockersHtml}
      </div>
      <div>
        <h4>Следующие шаги</h4>
        ${
          nextSteps.length
            ? `<ul class="steps">${nextSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ul>`
            : `<p class="empty">—</p>`
        }
      </div>
    </div>
    ${project.warnings?.length ? `<p class="project-warning">${escapeHtml(project.warnings.join(" · "))}</p>` : ""}
    <details class="evidence-wrap" ${project.verified ? "" : "open"}>
      <summary>Цитаты и источники <span>${asArray(project.evidence).length}</span></summary>
      ${renderEvidence(project)}
    </details>
  </article>`;
}

function renderSummary(model, num) {
  const cp = model.analysis?.crossProject || {};
  const deadlines = asArray(cp.deadlines);
  const risks = asArray(cp.risks);
  const highlights = asArray(cp.highlights);
  const external = asArray(cp.external);
  const structured = Boolean(deadlines.length || risks.length || highlights.length || external.length);
  const today = utcDay(model.snapshot.collectedAt);
  const collectedDate = parseDate(model.snapshot.collectedAt);
  const tomorrow = collectedDate ? utcDay(new Date(collectedDate.getTime() + 86_400_000)) : null;
  let body = "";
  if (structured) {
    body += `<div class="sum-grid">`;
    if (deadlines.length) {
      body += `<section class="sum-block sum-wide"><h3>Ближайшие сроки</h3><ol class="deadlines">${deadlines
        .map((item) => {
          const date = asString(item.date);
          const when = asString(item.when);
          const cls = date
            ? date === today
              ? "today"
              : date === tomorrow
                ? "tomorrow"
                : ""
            : when === "сегодня"
              ? "today"
              : when === "завтра"
                ? "tomorrow"
                : "";
          const dateLabel = /^\d{4}-\d{2}-\d{2}$/.test(date) ? `${date.slice(8, 10)}.${date.slice(5, 7)}` : date;
          const due = [dateLabel, when].filter(Boolean).join(" · ");
          const time = item.time ? `<span class="due-time">${escapeHtml(item.time)}</span>` : "";
          return `<li class="${cls}"><span class="due">${escapeHtml(due)}</span>${time}<div>${escapeHtml(item.what || "")} <span class="proj-tag">${escapeHtml(item.project || "")}</span></div></li>`;
        })
        .join("")}</ol></section>`;
    }
    if (risks.length) {
      const sorted = [...risks].sort(
        (a, b) => (SEV_ORDER[a.severity] ?? 1) - (SEV_ORDER[b.severity] ?? 1),
      );
      body += `<section class="sum-block"><h3>Блокеры и риски</h3><ul class="risk-list">${sorted
        .map((risk) => {
          const sev = SEV_ORDER[risk.severity] != null ? risk.severity : "medium";
          return `<li><span class="severity ${escapeHtml(sev)}">${escapeHtml(SEV_LABEL[sev])}</span> <span class="proj-tag">${escapeHtml(risk.project || "")}</span><div>${escapeHtml(risk.text || "")}</div></li>`;
        })
        .join("")}</ul></section>`;
    }
    if (highlights.length) {
      body += `<section class="sum-block"><h3>Главное за окно</h3><ul class="hl">${highlights
        .map((item) => `<li><span class="proj-tag">${escapeHtml(item.project || "")}</span><div>${escapeHtml(item.text || "")}</div></li>`)
        .join("")}</ul></section>`;
    }
    if (external.length) {
      body += `<section class="sum-block sum-wide"><h3>Внешние зависимости (люди вне чатов и инфраструктура)</h3><ul class="hl">${external
        .map((item) => `<li><span class="proj-tag">${escapeHtml(item.project || "")}</span><div>${escapeHtml(item.text || "")}</div></li>`)
        .join("")}</ul></section>`;
    }
    body += `</div>`;
    if (cp.summary) {
      body += `<details class="sum-text"><summary>Текстовая версия сводки</summary><p>${escapeHtml(cp.summary)}</p></details>`;
    }
  } else if (cp.summary) {
    body += `<div class="callout"><b>Сводка по всем проектам</b><p>${escapeHtml(cp.summary)}</p></div>`;
  } else {
    body += `<p class="empty">Сводка не заполнена: структурированных полей crossProject нет.</p>`;
  }
  return `<section id="summary" class="section">
    <div class="section-head"><div><p class="eyebrow">${num} · Сводка</p><h2>Сводка по всем проектам</h2></div><p class="section-note">Сроки подсвечены относительно даты сбора snapshot (UTC): «сегодня» и «завтра». Риски отсортированы от высоких к низким.</p></div>
    <div class="section-body">${body}</div>
  </section>`;
}

function renderActions(model, num) {
  const actions = model.actions;
  const snapshot = model.snapshot;
  const sendEnabled = model.sendEnabled === true;
  const items = asArray(actions.items);
  const count = (kinds) => items.filter((item) => kinds.includes(item.kind)).length;
  const kpis = [
    [count(["reply"]), "ждут вашего ответа"],
    [count(["approval", "answer_request"]), "ждут решения или аппрува"],
    [count(["decision", "project"]), "решения по проектам"],
    [count(["process"]), "процессные риски"],
  ];
  const cards = items
    .map((item) => {
      const pri = /^P[0-2]$/i.test(item.priority) ? item.priority.toUpperCase() : "P2";
      const priClass = pri === "P0" ? "bad" : pri === "P1" ? "warn" : "muted";
      const waiting = item.waiting && item.waiting !== "—" ? `ждёт ${item.waiting}` : "новая точка";
      const quotes = asArray(item.ev)
        .map(
          (id) =>
            `<a class="quote" href="https://app.pachca.com/chats/${encodeURIComponent(item.chatId)}?message=${encodeURIComponent(id)}">${escapeHtml(id)}</a>`,
        )
        .join("");
      return `<article class="project act-item">
      <div class="project-head">
        <div><p class="eyebrow">Личное действие</p><h3>${escapeHtml(item.id)} · ${escapeHtml(KIND_LABEL[item.kind] || item.kind)}</h3></div>
        <div class="project-badges"><span class="badge ${priClass}">${escapeHtml(pri)}</span></div>
      </div>
      <p class="act-meta">${escapeHtml(item.chat)} · ${escapeHtml(waiting)}</p>
      <div class="act-fields">
        <p><b>Кто:</b> ${escapeHtml(item.from)} · <b>с</b> ${escapeHtml(item.since)}</p>
        <p><b>Что ждут:</b> ${escapeHtml(item.ask)}</p>
        <p><b>Почему сейчас:</b> ${escapeHtml(item.why)}</p>
        <p><b>Что сделать:</b> ${escapeHtml(item.action)}</p>
      </div>
      ${draftBox(snapshot, { chatId: item.chatId, text: item.draft, hint: item.chat, ref: item.id }, sendEnabled)}
      ${quotes ? `<div class="act-quotes">${quotes}</div>` : ""}
    </article>`;
    })
    .join("");
  return `<section id="actions" class="section">
    <div class="section-head"><div><p class="eyebrow">${num} · Личные сообщения</p><h2>Личные сообщения: что ждут от вас — ${escapeHtml(actions.owner.name)}</h2></div><p class="section-note">${escapeHtml(actions.basis)} Обращений к вам: ${asNumber(actions.addressedToYou, 0)}; ваших открытых запросов: ${asNumber(actions.yourOpenAsks, 0)}.</p></div>
    <div class="section-body">
      <div class="act-kpis">${kpis.map(([value, label]) => `<div class="act-kpi"><b>${value}</b><span>${escapeHtml(label)}</span></div>`).join("")}</div>
      <div class="projects">${cards || `<p class="empty">Личных действий в окне нет.</p>`}</div>
    </div>
  </section>`;
}

function personRow(person, maxCount, threshold, excluded = false) {
  const counts = {};
  for (const [chatId, item] of Object.entries(person.byChat || {})) {
    counts[chatId] = {
      count: asNumber(item.count, 0),
      lastMessageAt: item.lastMessageAt || null,
    };
  }
  const width = maxCount > 0 ? Math.max(person.count > 0 ? 2 : 0, Math.round((person.count / maxCount) * 100)) : 0;
  const days = person.daysSilent;
  const daysLabel = days == null ? null : String(days).replace(".", ",");
  const longSilence = days == null || days > 7;
  return `<div class="person${person.inactive ? " inactive" : ""}${longSilence ? " long-silence" : ""}${excluded ? " excluded" : ""}"
    role="listitem"
    data-id="${escapeHtml(person.id)}"
    data-name="${escapeHtml(person.name)}"
    data-count="${person.count}"
    data-last="${escapeHtml(person.lastMessageAt || "")}"
    data-excluded="${person.excluded ? "true" : "false"}"
    data-by-chat="${escapeHtml(JSON.stringify(counts))}">
    <div class="person-head">
      <span class="person-name">${escapeHtml(person.name)}</span>
      <span class="person-badge${person.inactive ? " bad" : " ok"}">${escapeHtml(person.inactive ? (days == null ? "нет сообщений" : `${daysLabel} ${daysWord(days)}`) : "активен")}</span>
    </div>
    <div class="track" aria-hidden="true"><span class="bar" style="width:${width}%"></span></div>
    <div class="person-meta">
      <span class="person-count">${person.count} сообщ.</span>
      <span class="person-last">${person.lastMessageAt ? `последнее: ${escapeHtml(formatDay(person.lastMessageAt))}` : "нет сообщений в окне"}</span>
    </div>
  </div>`;
}

function renderActivity(activity, snapshot, num) {
  const visible = asArray(activity.visible);
  const maxCount = visible.reduce((max, item) => Math.max(max, item.count), 0);
  const chatOptions = snapshot.chats
    .map((chat) => `<option value="${escapeHtml(chat.id)}">${escapeHtml(chat.name)}</option>`)
    .join("");
  const rows = visible.map((person) => personRow(person, maxCount, activity.inactivityDays)).join("");
  const excludedRows = asArray(activity.excluded)
    .map(
      (person) =>
        `<div class="excluded-item">${personRow(person, maxCount, activity.inactivityDays, true)}<p class="hint">Причина: ${escapeHtml(person.exclusionReason || "не указана")} · вернуть: <code>.pachca/exclusions.md</code></p></div>`,
    )
    .join("");
  return `<section id="activity" class="section">
    <div class="section-head">
      <div><p class="eyebrow">${num} · Люди</p><h2>Активность участников</h2></div>
      <p class="section-note">Считаются сообщения в новом окне. Молчание — календарные дни с последнего сообщения; порог ${activity.inactivityDays} дн.</p>
    </div>
    <div class="activity-summary">
      <span><b id="activity-visible">${activity.stats.visible}</b> в диаграмме</span>
      <span><b id="activity-active">${activity.stats.active}</b> активны</span>
      <span><b id="activity-inactive">${activity.stats.inactive}</b> молчат &gt; ${activity.inactivityDays} дн.</span>
      <span><b id="activity-excluded">${activity.stats.excluded}</b> исключено</span>
      <span><b id="activity-max">${maxCount}</b> макс. сообщений</span>
    </div>
    <div class="toolbar" role="search">
      <label class="field"><span>Поиск</span><input id="activity-search" type="search" placeholder="Имя участника" autocomplete="off"></label>
      <label class="field"><span>Чат</span><select id="activity-chat"><option value="all">Все чаты</option>${chatOptions}</select></label>
      <label class="field"><span>Сортировка</span><select id="activity-sort"><option value="count">По сообщениям</option><option value="silence">По молчанию</option><option value="name">По имени</option></select></label>
      <label class="check"><input id="activity-only-inactive" type="checkbox"> Только молчащие</label>
    </div>
    <div id="activity-chart" class="chart" role="list" aria-label="Активность участников">${rows}</div>
    <p id="activity-empty" class="empty-state" hidden>Никто не подходит под фильтр.</p>
    ${
      activity.excluded.length
        ? `<details class="excluded-panel" open><summary>Исключены из диаграммы <span>${activity.excluded.length}</span></summary>
            <p class="hint">Эти участники не входят в диаграмму, но остаются в данных проектов. Причина и возврат — в <code>.pachca/exclusions.md</code>.</p>
            <div class="excluded-list">${excludedRows}</div>
          </details>`
        : ""
    }
  </section>`;
}

function renderTasks(tasks) {
  if (!asArray(tasks).length) {
    return `<p class="empty">Сохранённых задач нет. Добавьте задачу с каналом и действиями — плагин проверит права до сохранения.</p>`;
  }
  return `<div class="table-wrap"><table class="tasks">
    <thead><tr><th>Задача</th><th>Канал</th><th>Тип</th><th>Действия</th><th>Проверка прав</th><th>Последний запуск</th></tr></thead>
    <tbody>${asArray(tasks)
      .map(
        (task) => `<tr>
          <td><b>${escapeHtml(task.title || task.id)}</b><span class="mono">${escapeHtml(task.id)}</span></td>
          <td>${escapeHtml(task.channel || "—")}</td>
          <td>${escapeHtml(task.kind || "custom")}</td>
          <td>${escapeHtml((task.actions || []).join(", ") || "—")}</td>
          <td><span class="badge ${task.check === "ok" ? "ok" : task.check === "blocked" ? "bad" : "warn"}">${escapeHtml(task.check || "unchecked")}</span>${task.checkReason ? `<span class="task-reason">${escapeHtml(task.checkReason)}</span>` : ""}</td>
          <td>${task.lastRun ? escapeHtml(formatDate(task.lastRun)) : "—"}</td>
        </tr>`,
      )
      .join("")}</tbody>
  </table></div>`;
}

function sendDialog() {
  return `<dialog id="send-dialog" aria-labelledby="sd-title">
  <h3 id="sd-title">Отправка сообщения — очередь outbox</h3>
  <p class="chan" id="sd-chan"></p>
  <textarea id="sd-text" rows="7" spellcheck="false"></textarea>
  <p class="hint">Сообщение попадёт в <code>.pachca/outbox/</code> со статусом <code>pending_confirmation</code>. Ничего не отправляется автоматически: агент/плагин покажет очередь и отправит через <code>pachca_send_message</code> только после вашего отдельного подтверждения, с проверкой скоупов и роли в чате. При первом использовании браузер попросит выбрать папку outbox.</p>
  <div class="send-row"><button type="button" id="sd-confirm" class="send-btn">В очередь на отправку</button><button type="button" id="sd-copy" class="btn-plain">Скопировать текст</button><button type="button" id="sd-cancel" class="btn-plain">Отмена</button></div>
  <p class="hint" id="sd-status" role="status"></p>
</dialog>`;
}

function outboxScript(sendEnabled) {
  return `<script>
(function(){
  var SEND_ENABLED=${sendEnabled ? "true" : "false"};
  var dlg=document.getElementById('send-dialog');if(!dlg)return;
  var chanEl=document.getElementById('sd-chan'),textEl=document.getElementById('sd-text'),statusEl=document.getElementById('sd-status');
  var curChat=null,curChan='',curRef='';
  function closeDlg(){if(typeof dlg.close==='function'){dlg.close();}else{dlg.removeAttribute('open');}}
  document.querySelectorAll('.send-btn[data-chat]').forEach(function(b){
    if(b.disabled||!SEND_ENABLED)return;
    b.addEventListener('click',function(){
      var box=b.closest('.draft-box');var ta=box?box.querySelector('textarea'):null;
      curChat=b.getAttribute('data-chat');curChan=b.getAttribute('data-chan');curRef=b.getAttribute('data-ref')||'';
      chanEl.textContent='Канал: '+curChan+' · #'+curChat;
      textEl.value=ta?ta.value:'';statusEl.textContent='';
      if(typeof dlg.showModal==='function'){dlg.showModal();}else{dlg.setAttribute('open','');}
    });
  });
  function copyText(t){
    if(navigator.clipboard&&navigator.clipboard.writeText){return navigator.clipboard.writeText(t);}
    return new Promise(function(res,rej){var ta=document.createElement('textarea');ta.value=t;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();var ok=false;try{ok=document.execCommand('copy');}catch(e){ok=false;}document.body.removeChild(ta);ok?res():rej(new Error('copy failed'));});
  }
  function idb(){return new Promise(function(res,rej){var r=indexedDB.open('pachca-outbox',1);r.onupgradeneeded=function(){r.result.createObjectStore('handles');};r.onsuccess=function(){res(r.result);};r.onerror=function(){rej(r.error||new Error('idb'));};});}
  function getStoredDir(){return idb().then(function(db){return new Promise(function(res,rej){var rq=db.transaction('handles','readonly').objectStore('handles').get('dir');rq.onsuccess=function(){res(rq.result||null);};rq.onerror=function(){rej(rq.error);};});});}
  function storeDir(h){return idb().then(function(db){return new Promise(function(res,rej){var tx=db.transaction('handles','readwrite').objectStore('handles').put(h,'dir');tx.onsuccess=function(){res();};tx.onerror=function(){rej(tx.error);};});});}
  function ensureDir(){return getStoredDir().then(function(h){
    if(h){return h.queryPermission({mode:'readwrite'}).then(function(p){if(p==='granted')return h;return h.requestPermission({mode:'readwrite'}).then(function(p2){if(p2==='granted')return h;throw new Error('нет доступа к папке');});});}
    if(!window.showDirectoryPicker)throw new Error('File System Access API недоступен');
    return window.showDirectoryPicker({mode:'readwrite',id:'pachca-outbox'}).then(function(nh){return storeDir(nh).then(function(){return nh;});});
  });}
  function queueMessage(payload){
    var name='pachca-outbox-'+payload.chatId+'-'+Date.now()+'.json';
    var content=JSON.stringify(payload,null,2);
    return ensureDir().then(function(dir){
      return dir.getFileHandle(name,{create:true}).then(function(fh){return fh.createWritable();}).then(function(w){return w.write(content).then(function(){return w.close();});}).then(function(){return {via:'outbox',name:name};});
    }).catch(function(err){
      var blob=new Blob([content],{type:'application/json'});var url=URL.createObjectURL(blob);
      var aEl=document.createElement('a');aEl.href=url;aEl.download=name;document.body.appendChild(aEl);aEl.click();document.body.removeChild(aEl);
      setTimeout(function(){URL.revokeObjectURL(url);},5000);
      return {via:'download',name:name,reason:(err&&err.message)||String(err)};
    });
  }
  document.getElementById('sd-confirm').addEventListener('click',function(){
    var t=textEl.value;
    if(!t.trim()){statusEl.textContent='Пустой черновик — впишите текст сообщения.';return;}
    var payload={schemaVersion:1,kind:'pachca-outbox-message',id:'ob-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,7),queuedAt:new Date().toISOString(),chatId:curChat,channel:curChan,text:t,source:{report:document.title,ref:curRef},status:'pending_confirmation',sendPolicy:'confirm_then_send'};
    statusEl.textContent='Записываю в очередь…';
    queueMessage(payload).then(function(r){
      if(r.via==='outbox'){statusEl.textContent='Добавлено в .pachca/outbox/'+r.name+'. Отправит агент/плагин после вашего отдельного подтверждения.';}
      else{statusEl.textContent='Запись в папку недоступна ('+r.reason+'). Файл '+r.name+' скачан — положите его в .pachca/outbox/ и передайте агенту.';}
    }).catch(function(e){statusEl.textContent='Ошибка очереди: '+((e&&e.message)||e);});
  });
  document.getElementById('sd-copy').addEventListener('click',function(){
    copyText(textEl.value).then(function(){statusEl.textContent='Текст скопирован в буфер обмена.';}).catch(function(){statusEl.textContent='Не удалось скопировать — выделите текст вручную.';});
  });
  document.getElementById('sd-cancel').addEventListener('click',closeDlg);
})();
</script>`;
}

export function renderReport(model) {
  const snapshot = model.snapshot;
  const activity = model.activity;
  const projects = model.projects;
  const stats = model.projectStats;
  const coverage = model.coverage;
  const analysisQuality = model.analysis?.quality || "missing";
  const sendEnabled = model.sendEnabled === true;
  const hasActions = Boolean(model.actions);
  const num = {
    summary: "01",
    actions: "02",
    projects: hasActions ? "03" : "02",
    activity: hasActions ? "04" : "03",
    tasks: hasActions ? "05" : "04",
    method: hasActions ? "06" : "05",
  };
  const maxCount = activity.visible.reduce((max, item) => Math.max(max, item.count), 0);
  const kpi = [
    ["Сообщений", coverage.messages, "в новом окне"],
    ["Чатов прочитано", `${coverage.chatsRead}/${coverage.chatsAvailable}`, `${coverage.chatsQuiet} без новых сообщений`],
    ["Участников", activity.stats.visible, `${activity.stats.inactive} молчат > ${activity.inactivityDays} дн.`],
    ["Проектов", projects.length, `${stats.withBlockers} с блокерами, ${stats.atRisk} в риске`],
    ["Задач", asArray(model.tasks).length, "сохранено с preflight"],
    ["Доказательства", `${stats.verified}/${projects.length}`, "проектов с цитатами"],
  ];
  const window = coverage.window || {};
  const period = `${formatDay(window.from)} — ${formatDay(window.to)}`;
  const sourceLabel = snapshot.source === "rest" ? "Pachca REST API" : "Pachca MCP / snapshot";
  const warningItems = [
    ...(model.analysis?.warnings || []),
    ...model.failedChats.map((chat) => `Чат «${chat.name}»: ${chat.errors.map((error) => error.message).join("; ")}`),
    ...snapshot.chats.flatMap((chat) =>
      asArray(chat.coverage.errors)
        .filter((error) => error.stage === "thread")
        .map((error) => `Тред в чате «${chat.name}»: ${error.message}`),
    ),
    ...snapshot.chats
      .filter((chat) => chat.coverage.truncated)
      .map((chat) => `Чат «${chat.name}»: выборка обрезана лимитом сообщений`),
  ];
  const summaryJson = {
    schemaVersion: 1,
    formVersion: 2,
    generatedAt: model.generatedAt,
    asOf: snapshot.collectedAt,
    title: model.title,
    window,
    source: snapshot.source,
    sendEnabled,
    sendMechanism: "outbox",
    actionsPresent: hasActions,
    stats: {
      messages: coverage.messages,
      chatsRead: coverage.chatsRead,
      chatsAvailable: coverage.chatsAvailable,
      participants: activity.stats.visible,
      inactive: activity.stats.inactive,
      projects: projects.length,
      blocked: stats.blocked,
      withBlockers: stats.withBlockers,
      atRisk: stats.atRisk,
      verifiedProjects: stats.verified,
      tasks: asArray(model.tasks).length,
    },
    analysisQuality,
  };

  return `<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>${escapeHtml(model.title)} · ${escapeHtml(period)}</title>
<style>
:root{--paper:#f5f3ef;--card:#fff;--ink:#151a21;--muted:#5e6876;--line:#dde2e7;--line2:#c5ccd5;--teal:#17605c;--teal2:#e4efed;--green:#1c7346;--green2:#e6f3ea;--amber:#9a5b00;--amber2:#fbf0da;--red:#a62a1f;--red2:#fbe9e6;--violet:#5f4e9b;--mono:ui-monospace,"Cascadia Code",Consolas,monospace;--sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans)}
a{color:var(--teal);text-decoration-thickness:1px;text-underline-offset:2px}a:hover{color:#0b3f3c}
.skip{position:absolute;left:-999px;top:0;background:#fff;padding:10px;z-index:50}.skip:focus{left:10px;top:10px}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px}
.hero{padding:46px 0 18px}.topline{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:26px}
.brand{font-size:11px;letter-spacing:.12em;text-transform:uppercase;font-weight:750;color:var(--teal)}
.stamp{font-size:11.5px;color:var(--muted)}
h1{font-size:clamp(32px,5vw,58px);line-height:1.02;letter-spacing:-.035em;margin:0 0 14px;max-width:900px}
.lede{font-size:17px;color:var(--muted);max-width:820px;margin:0 0 20px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}.chip{border:1px solid var(--line);background:var(--card);border-radius:999px;padding:5px 10px;font-size:11.5px;color:var(--muted)}.chip b{color:var(--ink)}
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:26px 0 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 14px;min-height:92px}
.kpi span{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:750}
.kpi b{display:block;font-size:25px;line-height:1.1;margin:7px 0 4px;letter-spacing:-.02em}
.kpi small{color:var(--muted);font-size:10.5px}
.nav{position:sticky;top:0;z-index:20;background:rgba(245,243,239,.94);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);margin-top:24px}
.nav .wrap{display:flex;gap:16px;align-items:center;min-height:46px;flex-wrap:wrap;font-size:12px}
.nav a{color:var(--muted);text-decoration:none}.nav a:hover{color:var(--ink)}.nav .spacer{margin-left:auto}
.section{background:var(--card);border:1px solid var(--line);border-radius:15px;margin:16px 0;overflow:hidden}
.section-head{display:flex;justify-content:space-between;gap:20px;align-items:flex-end;flex-wrap:wrap;padding:20px 22px 15px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--teal);font-weight:750;margin:0 0 4px}
h2{font-size:25px;line-height:1.15;letter-spacing:-.02em;margin:0}h3{font-size:19px;line-height:1.2;margin:0;letter-spacing:-.01em}h4{font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin:0 0 7px}
.section-note{max-width:520px;color:var(--muted);font-size:12px;margin:0}
.section-body{padding:20px 22px 24px}
.badge{display:inline-flex;align-items:center;border-radius:6px;padding:3px 7px;font-size:10px;font-weight:750;text-transform:uppercase;letter-spacing:.04em;white-space:nowrap}
.badge.ok{background:var(--green2);color:var(--green)}.badge.warn{background:var(--amber2);color:var(--amber)}.badge.bad{background:var(--red2);color:var(--red)}.badge.muted,.badge.quiet{background:#eef0f3;color:var(--muted)}
.projects{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.project{border:1px solid var(--line);border-radius:12px;padding:16px;background:#fff;border-top:4px solid var(--line2)}
.project[data-status="on_track"]{border-top-color:var(--green)}.project[data-status="at_risk"]{border-top-color:var(--amber)}.project[data-status="blocked"]{border-top-color:var(--red)}
.project-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px}
.project-badges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.progress{margin:0 0 13px;font-size:14px}
.prog{margin:0 0 13px;padding-left:18px;font-size:14px}.prog li{margin:4px 0}
.project-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid var(--line);padding-top:12px}
.blockers,.steps,.evidence{list-style:none;margin:0;padding:0}
.blockers li{display:flex;gap:7px;align-items:flex-start;margin-bottom:7px;font-size:12.5px}
.blocker-body{flex:1;min-width:0}
.severity{flex:0 0 auto;border-radius:4px;padding:1px 5px;font-size:9px;text-transform:uppercase;font-weight:750;background:#eef0f3;color:var(--muted)}
.severity.high{background:var(--red2);color:var(--red)}.severity.medium{background:var(--amber2);color:var(--amber)}.severity.low{background:var(--green2);color:var(--green)}
.unverified{display:block;color:var(--red);font-size:10.5px;font-style:normal;margin-top:2px}
.steps li{font-size:12.5px;margin-bottom:5px;padding-left:12px;position:relative}.steps li::before{content:"→";position:absolute;left:0;color:var(--muted)}
.empty{color:var(--muted);margin:0;font-size:13px}
.project-warning{border-top:1px dashed var(--line);margin:12px 0 0;padding-top:9px;color:var(--amber);font-size:11px}
.evidence-wrap{margin-top:12px;border-top:1px solid var(--line);padding-top:9px}.evidence-wrap summary{cursor:pointer;font-size:11.5px;color:var(--teal);font-weight:700}.evidence-wrap summary span{color:var(--muted);font-weight:400}
.evidence{margin-top:8px}.evidence li{border-left:2px solid var(--line2);padding-left:9px;margin-bottom:8px}.ev-head{display:flex;justify-content:space-between;gap:8px;font-size:10.5px;color:var(--muted)}.ev-head span{text-align:right}
blockquote{margin:3px 0 0;font-size:12px;color:#2a313a}
.sum-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:0 0 14px}
.sum-block{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:#fff;margin:0}
.sum-block h3{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 10px}
.sum-wide{grid-column:1/-1}
.deadlines{list-style:none;margin:0;padding:0}
.deadlines li{display:flex;gap:10px;align-items:baseline;padding:7px 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
.deadlines li:last-child{border-bottom:none}
.due{font-size:10.5px;font-weight:750;border-radius:6px;padding:2px 8px;white-space:nowrap;background:#eef0f3;color:var(--muted)}
.deadlines li.today .due{background:var(--red2);color:var(--red)}
.deadlines li.tomorrow .due{background:var(--amber2);color:var(--amber)}
.due-time{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums;white-space:nowrap}
.deadlines li>div{flex:1;min-width:200px;font-size:13px}
.proj-tag{display:inline-block;font-size:10px;font-weight:750;border:1px solid var(--line);border-radius:999px;padding:1px 8px;margin-right:6px;color:var(--muted);white-space:nowrap}
.risk-list,.hl{list-style:none;margin:0;padding:0}
.risk-list li,.hl li{margin:0 0 10px;font-size:13px}
.risk-list li>div{margin-top:3px}
.hl li>div{margin-top:3px}
.sum-text{margin:0 0 12px}.sum-text summary{cursor:pointer;font-size:12px;color:var(--teal);font-weight:700}.sum-text p{margin:6px 0 0;font-size:13px;color:var(--muted)}
.act-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 14px}
.act-kpi{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:#fff}
.act-kpi b{display:block;font-size:24px;letter-spacing:-.02em}
.act-kpi span{font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:750}
.act-item{border-top-color:var(--teal)}
.act-meta{margin:0 0 8px;font-size:11.5px;color:var(--muted)}
.act-fields p{margin:6px 0 0;font-size:13px}
.act-quotes{margin-top:8px}
.quote{display:inline-block;font-size:10.5px;border:1px solid var(--line);border-radius:999px;padding:1px 7px;margin:2px 4px 0 0;text-decoration:none;color:var(--muted)}
.quote:hover{color:var(--ink);border-color:var(--line2)}
.draft-box{margin-top:10px;border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:var(--paper)}
.draft-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.draft-h{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:750}
.chan{font-size:11.5px;color:var(--muted)}.chan b{color:var(--ink)}
textarea.draft-edit{width:100%;min-height:84px;resize:vertical;font:13px/1.5 var(--sans);padding:8px 10px;border:1px solid var(--line2);border-radius:7px;background:#fff;color:var(--ink)}
textarea.draft-edit:focus{outline:2px solid var(--teal);outline-offset:-1px}
.send-row{display:flex;gap:10px;align-items:center;margin-top:8px;flex-wrap:wrap}
.send-btn{font:600 12.5px var(--sans);padding:6px 16px;border-radius:999px;border:1px solid var(--teal);background:var(--teal2);color:var(--teal);cursor:pointer}
.send-btn:hover:not(:disabled){background:var(--teal);color:#fff}
.send-btn:disabled{opacity:.55;cursor:not-allowed;border-color:var(--line2);background:#eef0f3;color:var(--muted)}
.btn-plain{font:12.5px var(--sans);padding:6px 16px;border-radius:999px;border:1px solid var(--line2);background:#fff;color:var(--ink);cursor:pointer}
.send-hint{font-size:10.5px;color:var(--muted)}
details.draft-details{margin-top:8px}
details.draft-details>summary{cursor:pointer;font-size:11.5px;font-weight:700;color:var(--teal)}
details.draft-details .draft-box{margin-top:8px}
dialog#send-dialog{border:1px solid var(--line2);border-radius:14px;background:var(--card);color:var(--ink);padding:18px 20px;max-width:640px;width:calc(100% - 40px)}
dialog#send-dialog::backdrop{background:rgba(21,26,33,.45)}
dialog#send-dialog h3{margin:0 0 6px}
dialog#send-dialog textarea{width:100%;min-height:140px;resize:vertical;font:13px/1.5 var(--sans);padding:8px 10px;border:1px solid var(--line2);border-radius:7px;background:var(--paper);color:var(--ink);margin:8px 0}
.activity-summary{display:flex;gap:9px;flex-wrap:wrap;padding:14px 22px 0;color:var(--muted);font-size:11.5px}.activity-summary b{color:var(--ink)}
.toolbar{display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;padding:14px 22px 6px}
.field{display:flex;flex-direction:column;gap:4px;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:700}
.field input,.field select{border:1px solid var(--line2);border-radius:7px;background:#fff;color:var(--ink);font:13px var(--sans);padding:7px 9px;min-height:34px}
.field input{min-width:190px}.field select{min-width:150px}
.check{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted);min-height:34px;padding-bottom:2px}
.chart{padding:10px 22px 22px;display:flex;flex-direction:column;gap:9px}
.person{border:1px solid var(--line);border-radius:9px;padding:9px 11px;background:#fff}
.person.inactive{border-left:4px solid var(--amber);background:#fffdf7}.person.inactive .person-name{text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;text-decoration-color:var(--amber)}.person.inactive.long-silence{border-left-color:var(--red);background:#fffafa}.person.inactive.long-silence .person-name{text-decoration-color:var(--red)}
.person.excluded{opacity:.72;background:#f7f7f7;border-left-color:var(--line2)}
.person-head{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:5px}
.person-name{font-weight:700;font-size:13px}.person-badge{font-size:10px;border-radius:5px;padding:2px 6px;white-space:nowrap}.person-badge.ok{background:var(--green2);color:var(--green)}.person-badge.bad{background:var(--red2);color:var(--red)}
.track{height:9px;background:#edf0f3;border-radius:999px;overflow:hidden}.bar{display:block;height:100%;background:linear-gradient(90deg,#2a7d77,#17605c);border-radius:999px;min-width:0}
.person.inactive .bar{background:linear-gradient(90deg,#c98a24,#9a5b00)}.person.inactive.long-silence .bar{background:linear-gradient(90deg,#c9554a,#a62a1f)}
.person-meta{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:10.5px;margin-top:4px}
.excluded-panel{margin:0 22px 22px;border:1px dashed var(--line2);border-radius:10px;padding:11px 13px;background:#fafafa}
.excluded-panel summary{cursor:pointer;font-weight:700;font-size:12px}.excluded-panel summary span{color:var(--muted);font-weight:400}
.hint{color:var(--muted);font-size:11.5px;margin:7px 0}.excluded-list{display:flex;flex-direction:column;gap:7px;margin-top:9px}
.empty-state{color:var(--muted);padding:0 22px 22px;font-size:13px}
.table-wrap{overflow:auto}.tasks{width:100%;border-collapse:collapse;font-size:12px;margin:0}
.tasks th{text-align:left;font-size:9.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);border-bottom:1px solid var(--line2);padding:8px 10px;white-space:nowrap}
.tasks td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:top}.tasks tr:last-child td{border-bottom:0}
.tasks b{display:block}.mono{font-family:var(--mono);font-size:10.5px;color:var(--muted)}.task-reason{display:block;color:var(--muted);font-size:10.5px;margin-top:3px;max-width:340px}
.callout{border:1px solid var(--line);border-left:4px solid var(--teal);background:#fbfdfd;border-radius:10px;padding:13px 15px;margin:0 0 14px}
.callout b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:4px}.callout p{margin:0;font-size:13px}
.method{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}.method ul{padding-left:18px;margin:0}.method li{font-size:12.5px;margin-bottom:6px}
.quality{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 12px}.quality span{border:1px solid var(--line);border-radius:6px;padding:3px 7px;font-size:10.5px;color:var(--muted)}
.warnings{margin:0;padding-left:18px}.warnings li{color:var(--amber);font-size:12px;margin-bottom:5px}
.footer{padding:12px 0 40px;color:var(--muted);font-size:11.5px}.footer .wrap{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
code{font-family:var(--mono);font-size:11.5px;background:#f0f2f4;border-radius:4px;padding:1px 4px}
@media(max-width:980px){.kpis{grid-template-columns:repeat(3,1fr)}.projects{grid-template-columns:1fr}.method{grid-template-columns:1fr}.sum-grid{grid-template-columns:1fr}.act-kpis{grid-template-columns:repeat(2,1fr)}}
@media(max-width:620px){.wrap{padding:0 14px}.kpis{grid-template-columns:repeat(2,1fr)}.project-grid{grid-template-columns:1fr}.hero{padding-top:28px}.section-head{padding:16px}.section-body{padding:16px}.chart{padding:8px 16px 16px}.toolbar{padding:12px 16px 4px}.field input{min-width:100%}.field{flex:1 1 100%}.act-kpis{grid-template-columns:repeat(2,1fr)}}
@media print{@page{size:A4;margin:12mm}body{background:#fff;font-size:9.5pt}.nav,.toolbar,.send-row,dialog#send-dialog{display:none}.wrap{max-width:none;padding:0}.section,.project,.person,.draft-box{break-inside:avoid;box-shadow:none}.kpis{grid-template-columns:repeat(3,1fr)}.act-kpis{grid-template-columns:repeat(4,1fr)}a{color:#000;text-decoration:none}.hero{padding-top:0}}
</style>
</head>
<body>
<a class="skip" href="#main">К содержанию</a>
<header class="hero"><div class="wrap">
  <div class="topline"><span class="brand">Pachca · workspace report</span><span class="stamp">сформировано ${escapeHtml(formatDate(model.generatedAt))} · ${escapeHtml(sourceLabel)}</span></div>
  <h1>${escapeHtml(model.title)}</h1>
  <p class="lede">Что сдвинулось в проектах, где блокеры и кто перестал писать. Все числа собраны из сообщений, доступных токену; прогресс и блокеры подтверждены цитатами или помечены как неподтверждённые.</p>
  <div class="chips">
    <span class="chip">Окно: <b>${escapeHtml(period)}</b></span>
    <span class="chip">Чатов: <b>${coverage.chatsRead}/${coverage.chatsAvailable}</b></span>
    <span class="chip">Сообщений: <b>${coverage.messages}</b></span>
    <span class="chip">Качество анализа: <b>${escapeHtml(analysisQuality)}</b></span>
    <span class="chip">Источник: <b>${escapeHtml(sourceLabel)}</b></span>
    <span class="chip">Отправка: <b>${sendEnabled ? "outbox, с подтверждением" : "только чтение"}</b></span>
  </div>
  <div class="kpis">${kpi.map(([label, value, note]) => `<div class="kpi"><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b><small>${escapeHtml(note)}</small></div>`).join("")}</div>
</div></header>
<nav class="nav" aria-label="Разделы отчёта"><div class="wrap">
  <a href="#summary">Сводка</a>${hasActions ? `<a href="#actions">Личные сообщения</a>` : ""}<a href="#projects">Проекты</a><a href="#activity">Активность</a><a href="#tasks">Задачи</a><a href="#method">Методика</a>
  <span class="spacer"></span><span>${escapeHtml(period)}</span>
</div></nav>
<main id="main" class="wrap">
  ${warningItems.length ? `<div class="callout"><b>Что требует внимания</b><ul class="warnings">${warningItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>` : ""}
  ${renderSummary(model, num.summary)}
  ${hasActions ? renderActions(model, num.actions) : ""}
  <section id="projects" class="section">
    <div class="section-head"><div><p class="eyebrow">${num.projects} · Смысл</p><h2>Прогресс и блокеры по проектам</h2></div><p class="section-note">${stats.withBlockers} проект(ов) с блокерами, ${stats.atRisk} в риске, ${stats.unknown} без анализа. Прочерк в блокерах означает, что новых блокеров не найдено.</p></div>
    <div class="section-body">
      <div class="projects">${projects.map((project) => renderProject(project, snapshot, sendEnabled)).join("") || `<p class="empty">В snapshot нет чатов.</p>`}</div>
    </div>
  </section>
  ${renderActivity(activity, snapshot, num.activity)}
  <section id="tasks" class="section">
    <div class="section-head"><div><p class="eyebrow">${num.tasks} · Автоматизация</p><h2>Сохранённые задачи</h2></div><p class="section-note">Задача сохраняется только после проверки скоупов, роли, тарифа и доступа к каналу. Перед запуском проверка повторяется.</p></div>
    <div class="section-body">${renderTasks(model.tasks)}</div>
  </section>
  <section id="method" class="section">
    <div class="section-head"><div><p class="eyebrow">${num.method} · Методика</p><h2>Как читать и чего здесь нет</h2></div><p class="section-note">Измерение отделено от интерпретации.</p></div>
    <div class="section-body method">
      <div>
        <div class="quality">
          <span>сообщения: measured</span><span>молчание: derived</span><span>прогресс/блокеры: expert</span><span>без цитат: missing</span>
        </div>
        <ul>
          <li><b>Сообщения.</b> Уникальные ID сообщений в окне, включая треды; боты не попадают в диаграмму участников.</li>
          <li><b>Молчание.</b> Календарные дни между последним сообщением участника и концом окна. «Более двух дней» — настраиваемый порог, не научный закон.</li>
          <li><b>Прогресс и блокеры.</b> Смысловой анализ новых сообщений. Вывод без ID-цитаты помечается как неподтверждённый.</li>
          <li><b>Черновики сообщений.</b> Текст черновика — суждение модели; он редактируется перед отправкой, канал назначения подписан у каждого черновика.</li>
          <li><b>Кнопки «Отправить».</b> ${sendEnabled ? "активны — есть скоуп messages:create" : "неактивны — токен только на чтение (нет messages:create)"}.</li>
          <li><b>Прочерк.</b> В блокерах «—» означает «новых блокеров не найдено», а не «блокеров не существует».</li>
          <li><b>Активность ≠ продуктивность.</b> Число сообщений — сигнал, а не оценка человека. Отчёт не ранжирует людей.</li>
        </ul>
      </div>
      <div>
        <h4>Покрытие и ограничения</h4>
        <ul>
          <li>Окно: ${escapeHtml(formatDate(window.from))} — ${escapeHtml(formatDate(window.to))}.</li>
          <li>Чаты: ${coverage.chatsRead} прочитано, ${coverage.chatsQuiet} без новых сообщений, ${coverage.chatsFailed} с ошибками, ${coverage.truncated} обрезано лимитом.</li>
          <li>Треды: ${coverage.threads} найдено; сообщения треда привязаны к родительскому чату.</li>
          <li>Личные переписки: ${snapshot.chats.filter((chat) => chat.personal).length}; архивные: ${snapshot.chats.filter((chat) => chat.archived).length}.</li>
          <li>Скоупы токена: ${escapeHtml(asArray(snapshot.account?.scopes).join(", ") || "не указаны")}.</li>
          <li><b>Механизм отправки (outbox).</b> Автономный HTML не хранит токен и не делает сетевых запросов. Активная кнопка ставит сообщение в очередь <code>.pachca/outbox/</code> со статусом <code>pending_confirmation</code> (File System Access API; если браузер не поддерживает — скачивается JSON, который нужно положить в outbox). Отправку выполняет плагин/агент через <code>pachca_send_message</code> только после отдельного подтверждения пользователя, с preflight скоупов и роли в чате; статус меняется на <code>sent</code> или <code>rejected</code>. Автоматически ничего не отправляется.</li>
          <li>Доступ определяется токеном и ролью. Закрытые чаты вне членства не читаются.</li>
          <li>Исключения влияют только на диаграмму; данные проектов сохраняются.</li>
        </ul>
      </div>
    </div>
  </section>
</main>
${sendDialog()}
<footer class="footer"><div class="wrap"><span>opencode-pachca · автономный отчёт, без внешних запросов</span><span>${escapeHtml(formatDate(model.generatedAt))}</span></div></footer>
<script id="report-data" type="application/json">${escapeJson(summaryJson)}</script>
<script>
(function(){
  "use strict";
  var chart=document.getElementById("activity-chart");
  if(!chart)return;
  var rows=Array.prototype.slice.call(chart.querySelectorAll(".person"));
  var search=document.getElementById("activity-search");
  var chat=document.getElementById("activity-chat");
  var sort=document.getElementById("activity-sort");
  var onlyInactive=document.getElementById("activity-only-inactive");
  var empty=document.getElementById("activity-empty");
  var asOfIso=document.getElementById("report-data");
  var meta={};try{meta=JSON.parse(asOfIso.textContent)}catch(e){}
  var end=new Date(meta.asOf||meta.generatedAt||Date.now());
  var threshold=${Number(activity.inactivityDays)};
  var msDay=86400000;

  function parseByChat(row){try{return JSON.parse(row.getAttribute("data-by-chat")||"{}")}catch(e){return {}}}
  function daysFrom(iso){if(!iso)return null;var d=new Date(iso);if(isNaN(d.getTime()))return null;return Math.round(((end-d.getTime())/msDay)*10)/10}
  function fmtDay(iso){if(!iso)return "нет сообщений в окне";var d=new Date(iso);if(isNaN(d.getTime()))return "нет сообщений в окне";return new Intl.DateTimeFormat("ru-RU",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"}).format(d)}
  function state(row){
    var selected=chat.value;
    if(selected==="all")return {count:Number(row.getAttribute("data-count")||0),last:row.getAttribute("data-last")||""};
    var map=parseByChat(row);var item=map[selected];
    if(!item)return null;
    return {count:Number(item.count||0),last:item.lastMessageAt||""};
  }
  function word(n){n=Math.abs(n);var a=n%10,b=n%100;if(a===1&&b!==11)return "день";if(a>=2&&a<=4&&(b<12||b>14))return "дня";return "дней"}
  function render(){
    var q=(search.value||"").trim().toLowerCase();
    var visible=0;var active=0;var inactive=0;var max=0;var shown=[];
    rows.forEach(function(row){
      var name=(row.getAttribute("data-name")||"").toLowerCase();
      var st=state(row);
      var ok=!q||name.indexOf(q)>=0;
      if(st===null)ok=false;
      var d=st?daysFrom(st.last):null;
      var isInactive=st?(st.last?d>threshold:true):true;
      if(onlyInactive.checked&&!isInactive)ok=false;
      row.hidden=!ok;
      if(!ok)return;
      visible++;if(isInactive)inactive++;else active++;
      max=Math.max(max,st.count);
      row.setAttribute("data-view-count",String(st.count));
      row.setAttribute("data-view-last",st.last||"");
      row.setAttribute("data-view-inactive",isInactive?"true":"false");
      var badge=row.querySelector(".person-badge");
      if(badge){badge.textContent=isInactive?(st.last?String(d).replace(".",",")+" "+word(d):"нет сообщений"):"активен";badge.className="person-badge "+(isInactive?"bad":"ok")}
      var count=row.querySelector(".person-count");if(count)count.textContent=st.count+" сообщ.";
      var last=row.querySelector(".person-last");if(last)last.textContent=st.last?"последнее: "+fmtDay(st.last):"нет сообщений в окне";
      row.classList.toggle("inactive",isInactive);
      row.classList.toggle("long-silence",isInactive&&(d===null||d>7));
      row.classList.remove("excluded");
      shown.push(row);
    });
    shown.forEach(function(row){
      var count=Number(row.getAttribute("data-view-count")||0);
      var bar=row.querySelector(".bar");
      if(bar)bar.style.width=(max>0?Math.max(count>0?2:0,Math.round(count/max*100)):0)+"%";
    });
    var mode=sort.value;
    shown.sort(function(a,b){
      if(mode==="name")return (a.getAttribute("data-name")||"").localeCompare(b.getAttribute("data-name")||"","ru");
      if(mode==="silence"){var da=daysFrom(a.getAttribute("data-view-last"));var db=daysFrom(b.getAttribute("data-view-last"));return (db==null?1e9:db)-(da==null?1e9:da)}
      return Number(b.getAttribute("data-view-count")||0)-Number(a.getAttribute("data-view-count")||0);
    });
    shown.forEach(function(row){chart.appendChild(row)});
    empty.hidden=shown.length>0;
    var v=document.getElementById("activity-visible");if(v)v.textContent=String(visible);
    var ac=document.getElementById("activity-active");if(ac)ac.textContent=String(active);
    var ic=document.getElementById("activity-inactive");if(ic)ic.textContent=String(inactive);
    var mx=document.getElementById("activity-max");if(mx)mx.textContent=String(max);
  }
  [search,chat,sort,onlyInactive].forEach(function(el){if(el){el.addEventListener("input",render);el.addEventListener("change",render)}});
  render();
})();
</script>
${outboxScript(sendEnabled)}
</body>
</html>`;
}
