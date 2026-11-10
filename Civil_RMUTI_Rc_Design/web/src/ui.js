/* Civil RMUTI Rc Design - web user interface.
 * All engineering logic lives in core.js (RC); this file only renders.
 */
(function () {
  "use strict";

  const RC = window.RC;
  const SPEC = RC.SPEC;
  const STORE_KEY = "civil-rmuti-rc-design.session.v2";
  const LOGO = "__LOGO_DATA_URI__";

  const state = {
    project: null,
    fileName: "",
    modified: false,
    view: "project",
    selected: {},
  };

  // ================================================================ helpers
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "text") el.textContent = v;
      else if (k === "svg") el.innerHTML = v; // trusted, static icon markup only
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k === "value") el.value = v;
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  function s(tag, attrs, text) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    if (text !== undefined) el.textContent = text;
    return el;
  }

  let toastTimer = null;
  function toast(message, isError) {
    document.querySelectorAll(".toast").forEach((t) => t.remove());
    const el = h("div", { class: "toast" + (isError ? " err" : ""), role: "status" }, message);
    document.body.append(el);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.remove(), 3200);
  }

  function dtList() { return SPEC.design_types; }
  function dtByValue(v) { return RC.designType(v); }
  function units() { return state.project.design_settings.unit_system; }

  // ================================================================ persistence (this browser only)
  let persistTimer = null;
  function writeStore() {
    clearTimeout(persistTimer);
    persistTimer = null;
    if (!state.project) return;
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({
        file: RC.serialize(JSON.parse(JSON.stringify(state.project))),
        fileName: state.fileName, modified: state.modified,
        view: state.view,
      }));
    } catch (e) { /* storage unavailable: the page still works */ }
  }
  function persist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(writeStore, 250);
  }
  function flushStore() { if (persistTimer) writeStore(); }

  function restore() {
    try {
      const raw = localStorage.getItem(STORE_KEY);
      if (!raw) return false;
      const data = JSON.parse(raw);
      state.project = RC.deserialize(data.file);
      state.fileName = data.fileName || "";
      state.modified = !!data.modified;
      state.view = data.view || "design";
      return true;
    } catch (e) {
      return false;
    }
  }

  function markModified() {
    state.modified = true;
    updateChrome();
    persist();
  }

  // ================================================================ icons
  const ICONS = {
    column: '<rect x="22" y="6" width="20" height="52" class="i-fill"/><path d="M27 9v46M37 9v46" class="i-bar"/><path d="M24 14h16M24 22h16M24 30h16M24 38h16M24 46h16M24 54h16" class="i-tie"/>',
    beam: '<rect x="4" y="20" width="56" height="20" class="i-fill"/><path d="M8 35h48M8 25h48" class="i-bar"/><path d="M10 40l-5 10h10zM54 40l-5 10h10z" class="i-sup"/>',
    slab: '<path d="M4 30L22 16H60L42 30Z" class="i-fill"/><path d="M4 30H42V38H4Z M42 30L60 16V24L42 38Z" class="i-fill"/><path d="M8.5 26.5h38M13 23h38M17.5 19.5h38" class="i-tie"/><path d="M10 38v18M38 38v18" class="i-bar"/>',
    stair: '<path d="M6 58V48H16V38H26V28H36V18H46V8H58V18L20 58Z" class="i-fill"/>',
    footing: '<rect x="2" y="50" width="60" height="10" class="i-soil"/><rect x="26" y="6" width="12" height="34" class="i-fill"/><rect x="8" y="38" width="48" height="14" class="i-fill"/><path d="M12 48h40" class="i-bar"/>',
  };
  function icon(dtValue, size) {
    return `<svg viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true">
      <style>.i-fill{fill:var(--concrete);stroke:var(--accent);stroke-width:2.5;stroke-linejoin:round}
      .i-bar{stroke:var(--accent);stroke-width:2.4;fill:none;stroke-linecap:round}
      .i-tie{stroke:var(--accent);stroke-width:1.3;fill:none}.i-sup{fill:var(--accent)}
      .i-soil{fill:var(--muted);opacity:.35}</style>${ICONS[dtValue]}</svg>`;
  }

  // ================================================================ chrome
  const VIEWS = ["start", "project", "design", ...SPEC.design_types.map((d) => d.value), "materials", "help"];

  function updateChrome() {
    const has = !!state.project;
    document.getElementById("project-name").textContent = has ? (state.project.project_information.project_name || "Untitled") : "No project open";
    document.getElementById("dirty").hidden = !has || !state.modified;
    document.getElementById("btn-save").disabled = !has;
    document.getElementById("brand-sub").textContent = `v${SPEC.app.version} · Web`;
    document.title = "Civil RMUTI Rc Design";
    renderTabs();
  }

  function renderTabs() {
    const nav = document.getElementById("tabs");
    nav.replaceChildren();
    const tab = (id, label, count) => h("button", {
      class: "tab", type: "button", "aria-current": state.view === id ? "page" : null,
      onclick: () => go(id),
    }, label, count !== undefined ? h("span", { class: "count" }, count) : null);
    if (!state.project) {
      nav.append(tab("start", "Start"), tab("help", "Help"));
      return;
    }
    nav.append(tab("project", "Project"), tab("design", "Design"), h("span", { class: "tab-sep" }));
    for (const dt of dtList()) nav.append(tab(dt.value, dt.title, RC.members(state.project, dt.value).length));
    nav.append(h("span", { class: "tab-sep" }), tab("materials", "Materials"), tab("help", "Help"));
  }

  function go(view) {
    if (!VIEWS.includes(view)) view = state.project ? "design" : "start";
    if (!state.project && view !== "help") view = "start";
    if (state.project && view === "start") view = "design";
    state.view = view;
    if (location.hash !== "#" + view) {
      try { history.replaceState(null, "", "#" + view); } catch (e) { location.hash = view; }
    }
    render();
    window.scrollTo(0, 0);
    persist();
  }

  function render() {
    updateChrome();
    const main = document.getElementById("main");
    main.replaceChildren();
    const v = state.view;
    if (v === "help") main.append(renderHelp());
    else if (!state.project) main.append(renderStart());
    else if (v === "project") main.append(renderProject());
    else if (v === "design") main.append(renderSelection());
    else if (v === "materials") main.append(renderMaterials());
    else main.append(renderEditor(v));
  }

  // ================================================================ start view
  function renderStart() {
    const recent = state.fileName ? h("p", { class: "brand-sub" }, `Last file: ${state.fileName}`) : null;
    return h("div", { class: "start" },
      LOGO.startsWith("data:")
        ? h("img", { class: "start-logo", src: LOGO, alt: "RMUTI emblem", width: 120, height: 120 })
        : h("div", { class: "mark big", "aria-hidden": "true" }, "RC"),
      h("h1", {}, SPEC.app.name),
      h("p", { class: "start-sub" }, "Reinforced Concrete Structural Design", h("br"), "โปรแกรมออกแบบโครงสร้างคอนกรีตเสริมเหล็ก"),
      h("div", { class: "start-actions" },
        h("button", { class: "btn primary", type: "button", onclick: () => newProjectDialog() }, "New Project"),
        h("button", { class: "btn", type: "button", onclick: openProject }, "Open Project...")),
      recent,
      h("ol", { class: "start-steps" },
        h("li", {}, h("b", {}, "New Project"), " — enter the project information, design standard and unit system."),
        h("li", {}, h("b", {}, "Select Design"), " — Column, Beam, Slab, Stair or Footing."),
        h("li", {}, h("b", {}, "Calculate and Save"), " — results, report and a .rcproj file that also opens in the desktop program.")),
      h("p", { class: "brand-sub" }, `v${SPEC.app.version} · ${SPEC.app.phase}`));
  }

  function resetData() {
    confirmBox("Reset this browser's data",
      "This closes the current project and deletes the copy kept in this browser. Project files you saved are not affected.",
      "Reset", () => {
        try { localStorage.removeItem(STORE_KEY); } catch (e) { /* nothing stored */ }
        clearTimeout(persistTimer); persistTimer = null;
        Object.assign(state, { project: null, fileName: "", modified: false, selected: {} });
        go("start");
        toast("Data reset. Ready for a new project.");
      });
  }

  // ================================================================ project view
  const INFO_FIELDS = [
    ["project_name", "Project Name", true], ["project_number", "Project Number"],
    ["designer", "Designer"], ["checker", "Checker"], ["organization", "Company / Organization"],
    ["project_date", "Date"], ["location", "Location"],
  ];

  function textField(id, label, value, oninput, opts) {
    const o = opts || {};
    const input = h(o.multiline ? "textarea" : "input", {
      id, type: o.multiline ? null : (o.type || "text"), value: value || "", rows: o.multiline ? 3 : null,
      maxlength: o.max || 200, oninput: (e) => oninput(e.target.value, e.target),
    });
    if (o.multiline) input.value = value || "";
    return h("div", { class: "field" + (o.invalid ? " invalid" : "") },
      h("label", { for: id }, label, o.required ? h("span", { class: "req" }, " *") : null),
      h("div", { class: "input-wrap" }, input),
      h("div", { class: "err", hidden: !o.invalid }, o.invalid || ""));
  }

  function selectField(id, label, options, value, onchange) {
    const sel = h("select", { id, onchange: (e) => onchange(e.target.value) },
      options.map(([v, text]) => h("option", { value: v, selected: v === value ? true : null }, text)));
    return h("div", { class: "field" }, h("label", { for: id }, label), h("div", { class: "input-wrap" }, sel));
  }

  function renderProject() {
    const p = state.project;
    const info = p.project_information;
    const settings = p.design_settings;
    const wrap = h("div");
    wrap.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Project Information"),
      h("p", {}, "Changes are kept in this browser automatically. Use Save to get a .rcproj file."))));

    const infoGrid = h("div", { class: "form-grid" });
    for (const [key, label, required] of INFO_FIELDS) {
      const field = textField(`info-${key}`, label, info[key], (value, el) => {
        info[key] = value.trim() ? value : "";
        const bad = required && !value.trim();
        el.closest(".field").classList.toggle("invalid", bad);
        const err = el.closest(".field").querySelector(".err");
        err.hidden = !bad; err.textContent = bad ? `${label} is required.` : "";
        markModified();
      }, { required, type: key === "project_date" ? "date" : "text", invalid: required && !info[key] ? `${label} is required.` : "" });
      infoGrid.append(field);
    }
    infoGrid.append(textField("info-description", "Description", info.description, (v) => { info.description = v; markModified(); },
      { multiline: true, max: 2000 }));

    const unitNote = h("p", { class: "err", hidden: true },
      "Changing the unit system does not convert values already entered for members.");
    const settingsGrid = h("div", { class: "form-grid" },
      selectField("set-standard", "Design Standard", SPEC.standards.map((x) => [x.value, x.label]), settings.design_standard,
        (v) => { settings.design_standard = v; RC.syncStandardLabel(p); markModified(); }),
      selectField("set-units", "Unit System", SPEC.units.map((x) => [x.value, x.label]), settings.unit_system,
        (v) => { settings.unit_system = v; unitNote.hidden = false; markModified(); }),
      selectField("set-concrete", "Default Concrete", p.materials.concrete.map((c) => [c.name, c.name]), settings.default_concrete,
        (v) => { settings.default_concrete = v; markModified(); }),
      selectField("set-main", "Default Main Bars", p.reinforcement.grades.map((g) => [g.name, g.name]), settings.default_main_rebar,
        (v) => { settings.default_main_rebar = v; markModified(); }),
      selectField("set-tie", "Default Ties / Stirrups", p.reinforcement.grades.map((g) => [g.name, g.name]), settings.default_tie_rebar,
        (v) => { settings.default_tie_rebar = v; markModified(); }));

    const left = h("div", { class: "out-stack" },
      h("section", { class: "panel" }, h("div", { class: "panel-head" }, "General", h("span", { class: "hint" }, "* required")),
        h("div", { class: "panel-body" }, infoGrid)),
      h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Design Settings"),
        h("div", { class: "panel-body" }, settingsGrid, unitNote)));

    const counts = h("ul", { class: "stat-list" }, dtList().map((dt) => h("li", {},
      h("a", { href: "#" + dt.value, onclick: (e) => { e.preventDefault(); go(dt.value); } }, `${dt.title}s`),
      h("span", { class: "num" }, RC.members(p, dt.value).length))));
    const fileBox = h("div", { class: "panel-body" },
      h("dl", { class: "kv" },
        h("dt", {}, "File"), h("dd", {}, state.fileName || "Not saved yet"),
        h("dt", {}, "Format"), h("dd", {}, `${SPEC.app.extension} v${SPEC.app.format_version}`),
        h("dt", {}, "Created"), h("dd", { class: "mono" }, (p.metadata.created_at || "").replace("T", " "))),
      h("p", { class: "brand-sub" }, "Files saved here open in the desktop program, and desktop .rcproj files open here."),
      h("div", { class: "actions" },
        h("button", { class: "btn", type: "button", onclick: openProject }, "Open..."),
        h("button", { class: "btn primary", type: "button", onclick: saveProject }, "Save"),
        h("button", { class: "btn danger", type: "button", onclick: resetData }, "Reset")));
    const right = h("div", { class: "out-stack" },
      h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Members"), counts),
      h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Project File"), fileBox),
      h("button", { class: "btn primary", type: "button", onclick: () => go("design") }, "Go to Design Selection →"));
    wrap.append(h("div", { class: "two" }, left, right));
    return wrap;
  }

  // ================================================================ design selection
  function renderSelection() {
    const wrap = h("div");
    wrap.append(h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Select Design Type"),
      h("p", {}, "เลือกประเภทโครงสร้างที่ต้องการออกแบบ"))));
    const cards = h("div", { class: "cards" });
    for (const dt of dtList()) {
      const n = RC.members(state.project, dt.value).length;
      cards.append(h("button", { class: "card", type: "button", onclick: () => go(dt.value) },
        h("div", { class: "icon", svg: icon(dt.value, 64) }),
        h("div", {},
          h("h2", {}, dt.title.toUpperCase()),
          h("p", { class: "en" }, dt.description),
          h("p", { class: "th" }, dt.description_th),
          h("div", { class: "meta" }, `${n} ${n === 1 ? "member" : "members"}`))));
    }
    wrap.append(cards);
    return wrap;
  }

  // ================================================================ editor
  function currentMember(dtValue) {
    const list = RC.members(state.project, dtValue);
    let m = list.find((x) => x.member_id === state.selected[dtValue]);
    if (!m && list.length) { m = list[0]; state.selected[dtValue] = m.member_id; }
    return m || null;
  }

  function memberIssues(dtValue, m) {
    const v = RC.validateMember(state.project, dtValue, m);
    if (m.name.trim() && RC.nameTaken(state.project, dtValue, m.name, m.member_id)) {
      v.errors.push(`${dtByValue(dtValue).title} name '${m.name.trim()}' is already used.`);
    }
    return v;
  }

  function renderEditor(dtValue) {
    const dt = dtByValue(dtValue);
    const p = state.project;
    const list = RC.members(p, dtValue);
    const member = currentMember(dtValue);
    const wrap = h("div");
    wrap.append(h("div", { class: "view-head" },
      h("div", { class: "icon", svg: icon(dtValue, 44) }),
      h("div", {}, h("h1", {}, `${dt.title} Design`),
        h("p", {}, `${dt.description} · ${p.design_settings.design_standard} · ${p.design_settings.unit_system}`))));

    // ---- member list
    const listEl = h("ul", { class: "member-list", "aria-label": `${dt.title}s` });
    for (const m of list) {
      listEl.append(h("li", {}, h("button", {
        class: "member-btn", type: "button", "aria-current": member && m.member_id === member.member_id ? "true" : "false",
        "data-id": m.member_id, onclick: () => { state.selected[dtValue] = m.member_id; render(); },
      }, h("span", { class: "dot" + (m.result ? " done" : ""), title: m.result ? "Calculated" : "Not calculated" }),
      h("span", { class: "mname" }, m.name || "(no name)"))));
    }
    const addMember = () => {
      const m = RC.newMember(p, dtValue);
      list.push(m);
      state.selected[dtValue] = m.member_id;
      markModified();
      render();
      const name = document.getElementById("m-name");
      if (name) { name.focus(); name.select(); }
    };
    const tools = h("div", { class: "member-tools" },
      h("button", { class: "btn small", type: "button", onclick: addMember }, "Add"),
      h("button", { class: "btn small", type: "button", disabled: !member, onclick: () => {
        const copy = JSON.parse(JSON.stringify(member));
        Object.assign(copy, { member_id: RC.uid(), name: RC.nextMemberName(p, dtValue), created_at: RC.nowIso(), modified_at: RC.nowIso() });
        list.push(copy);
        state.selected[dtValue] = copy.member_id;
        markModified(); render();
      } }, "Duplicate"),
      h("button", { class: "btn small danger", type: "button", disabled: !member, onclick: () => {
        confirmBox(`Delete ${dt.value} ${member.name}?`, "This removes the member and its results from the project.", "Delete", () => {
          list.splice(list.indexOf(member), 1);
          state.selected[dtValue] = null;
          markModified(); render();
        });
      } }, "Delete"));
    const members = h("aside", { class: "panel members" },
      h("div", { class: "panel-head" }, `${dt.title}s`, h("span", { class: "hint num" }, list.length)),
      list.length ? listEl : h("div", { class: "empty" }, `No ${dt.value} yet.`), tools);

    if (!member) {
      wrap.append(h("div", { class: "editor" }, members,
        h("section", { class: "panel" }, h("div", { class: "empty" },
          h("p", {}, `Add the first ${dt.value} to start.`),
          h("button", { class: "btn primary", type: "button", onclick: addMember }, `Add ${dt.title}`)))));
      return wrap;
    }

    // ---- form
    const form = h("section", { class: "panel" });
    const issuesEl = h("ul", { class: "issues", hidden: true });
    const outStack = h("div", { class: "out-stack" });
    const drawing = h("div", { class: "drawing" });

    // Field errors show live next to each input; the list below repeats them
    // (plus cross-field checks) after Validate / Calculate. Warnings always show.
    const refreshIssues = (showAll) => {
      const v = memberIssues(dtValue, member);
      issuesEl.replaceChildren(
        ...(showAll ? v.errors : []).map((e) => h("li", { class: "e" }, e)),
        ...v.warnings.map((w) => h("li", { class: "w" }, w)));
      issuesEl.hidden = issuesEl.childElementCount === 0;
      return v;
    };

    const invalidate = () => {
      if (member.result) {
        member.result = null;
        renderResults(outStack, dtValue, member);
        const dot = document.querySelector(`.member-btn[data-id="${member.member_id}"] .dot`);
        if (dot) dot.classList.remove("done");
      }
      member.modified_at = RC.nowIso();
      markModified();
    };

    // member group
    const nameRow = h("div", { class: "row" },
      h("label", { for: "m-name" }, "Name / Mark ", h("span", { class: "req" }, "*")),
      h("div", { class: "input-wrap" }, h("input", { id: "m-name", value: member.name, maxlength: 40, oninput: (e) => {
        member.name = e.target.value.trim();
        const label = document.querySelector(`.member-btn[data-id="${member.member_id}"] .mname`);
        if (label) label.textContent = member.name || "(no name)";
        let err = "";
        if (!member.name) err = `${dt.title} name is required.`;
        else if (RC.nameTaken(p, dtValue, member.name, member.member_id)) err = `${dt.title} name '${member.name}' is already used.`;
        nameRow.classList.toggle("invalid", !!err);
        nameErr.hidden = !err; nameErr.textContent = err;
        member.modified_at = RC.nowIso();
        markModified();
      } })));
    const nameErr = h("div", { class: "err", hidden: true });
    nameRow.append(nameErr);
    const notes = h("textarea", { id: "m-notes", rows: 2, maxlength: 2000, oninput: (e) => { member.notes = e.target.value; markModified(); } });
    notes.value = member.notes || "";
    form.append(h("div", { class: "panel-head" }, `${dt.title} ${member.name}`, h("span", { class: "hint" }, "* required")));
    form.append(h("div", { class: "group" }, h("h3", {}, "Member"), h("div", { class: "rows" }, nameRow,
      h("div", { class: "row" }, h("label", { for: "m-notes" }, "Notes"), h("div", { class: "input-wrap" }, notes)))));

    // materials group
    const matSelect = (id, label, attr, options) => h("div", { class: "row" },
      h("label", { for: id }, label),
      h("div", { class: "input-wrap" }, h("select", { id, onchange: (e) => { member[attr] = e.target.value; invalidate(); refreshIssues(false); } },
        (options.includes(member[attr]) ? options : [member[attr], ...options]).map((o) =>
          h("option", { value: o, selected: o === member[attr] ? true : null }, o)))));
    form.append(h("div", { class: "group" }, h("h3", {}, "Materials"), h("div", { class: "rows" },
      matSelect("m-concrete", "Concrete", "concrete", p.materials.concrete.map((c) => c.name)),
      matSelect("m-main", "Main reinforcement", "main_rebar", p.reinforcement.grades.map((g) => g.name)),
      matSelect("m-tie", "Ties / stirrups", "tie_rebar", p.reinforcement.grades.map((g) => g.name)))));

    // input groups from the shared field spec
    const rowEls = {};
    const updateVisibility = () => {
      for (const f of dt.fields) rowEls[f.key].hidden = !RC.isActive(f, member.inputs);
    };
    const setFieldError = (f) => {
      const row = rowEls[f.key];
      const errs = RC.isActive(f, member.inputs) ? RC.checkField(dt, f, member.inputs[f.key], units()) : [];
      row.classList.toggle("invalid", errs.length > 0);
      const err = row.querySelector(".err");
      err.hidden = !errs.length; err.textContent = errs.join(" ");
    };
    const groups = {};
    for (const f of dt.fields) {
      if (!groups[f.group]) {
        groups[f.group] = h("div", { class: "rows" });
        form.append(h("div", { class: "group" }, h("h3", {}, f.group), groups[f.group]));
      }
      const id = `f-${f.key}`;
      const value = member.inputs[f.key] ?? f.default;
      let control;
      if (f.kind === "choice") {
        control = h("select", { id, onchange: (e) => {
          member.inputs[f.key] = e.target.value;
          updateVisibility(); invalidate(); refreshIssues(false); drawPreview(drawing, dtValue, member.inputs);
        } }, f.choices.map((c) => h("option", { value: c, selected: c === value ? true : null }, c)));
      } else {
        const allowsNegative = f.minimum === null || f.minimum === undefined || f.minimum < 0;
        control = h("input", { id, class: "numeric", inputmode: allowsNegative ? "text" : "decimal",
          autocomplete: "off", autocorrect: "off", autocapitalize: "off", spellcheck: "false", enterkeyhint: "next",
          value: typeof value === "number" ? RC.g(value) : String(value ?? ""),
          oninput: (e) => {
            member.inputs[f.key] = RC.numberOrText(e.target.value);
            setFieldError(f); invalidate(); refreshIssues(false); drawPreview(drawing, dtValue, member.inputs);
          } });
      }
      const unit = RC.fieldUnit(f, units());
      const row = h("div", { class: "row", title: f.tooltip || null },
        h("label", { for: id }, f.label, f.required && f.kind !== "choice" ? h("span", { class: "req" }, " *") : null),
        h("div", { class: "input-wrap" }, control, unit ? h("span", { class: "unit" }, unit) : null),
        h("div", { class: "err", hidden: true }));
      rowEls[f.key] = row;
      groups[f.group].append(row);
    }

    const calcBar = h("div", { class: "calc-bar" },
      h("button", { class: "btn", type: "button", onclick: () => {
        const v = refreshIssues(true);
        dt.fields.forEach(setFieldError);
        if (!v.errors.length && !v.warnings.length) toast("All inputs are valid.");
      } }, "Validate"),
      h("span", { class: "spacer" }),
      h("button", { class: "btn", type: "button", onclick: () => openReport(dtValue, member) }, "Report"),
      h("button", { class: "btn primary", id: "btn-calculate", type: "button", title: "Calculate (Ctrl/⌘ + Enter)", onclick: () => {
        const v = refreshIssues(true);
        dt.fields.forEach(setFieldError);
        if (v.errors.length) { toast("Invalid input. Fix the highlighted fields.", true); return; }
        const out = RC.calculate(p, dtValue, member);
        if (!out.ok) { toast(out.errors[0], true); return; }
        renderResults(outStack, dtValue, member);
        const dot = document.querySelector(`.member-btn[data-id="${member.member_id}"] .dot`);
        if (dot) dot.classList.add("done");
        markModified();
        toast(`${dt.title} ${member.name} calculated.`);
      } }, "Calculate"));
    form.append(issuesEl, calcBar);

    // ---- output
    outStack.append(h("section", { class: "panel", id: "sketch" },
      h("div", { class: "panel-head" }, "Geometry Sketch", h("span", { class: "hint" }, "not to scale for loads")), drawing));
    renderResults(outStack, dtValue, member);

    wrap.append(h("div", { class: "editor" }, members, form, outStack));
    updateVisibility();
    dt.fields.forEach((f) => { if (member.inputs[f.key] !== undefined) setFieldError(f); });
    refreshIssues(false);
    drawPreview(drawing, dtValue, member.inputs);
    return wrap;
  }

  function renderResults(stack, dtValue, member) {
    const old = stack.querySelector("#results");
    const r = member.result || { status: "not_calculated", items: [], messages: [] };
    const body = r.items && r.items.length
      ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, h("th", {}, "Item"), h("th", { style: "text-align:right" }, "Value"), h("th", {}, "Unit"))),
        h("tbody", {}, r.items.map((it) => h("tr", {},
          h("td", {}, it.label, it.note ? h("span", { class: "note" }, it.note) : null),
          h("td", { class: "v" }, RC.formatValue(it.value)),
          h("td", { class: "u" }, it.unit))))))
      : h("div", { class: "empty" }, "Press Calculate to compute this member.");
    const panel = h("section", { class: "panel", id: "results" },
      h("div", { class: "panel-head" }, "Results",
        h("span", { class: "hint" }, h("span", { class: "status " + r.status }, RC.STATUS_LABELS[r.status] || r.status))),
      body,
      r.messages && r.messages.length ? h("ul", { class: "msgs" }, r.messages.map((m) => h("li", {}, m))) : null);
    if (old) old.replaceWith(panel); else stack.append(panel);
  }

  // ================================================================ drawings
  function drawPreview(container, dtValue, raw) {
    const W = 340, H = 240, PAD = 34;
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Geometry sketch" });
    const v = {};
    for (const [k, val] of Object.entries(raw)) v[k] = RC.parseNumber(val);
    const pos = (...keys) => keys.every((k) => v[k] !== null && v[k] > 0);
    const fit = (w, hgt) => {
      const scale = Math.min((W - 2 * PAD) / w, (H - 2 * PAD - 14) / hgt);
      return { scale, x0: (W - w * scale) / 2, y0: 20 + (H - 20 - hgt * scale) / 2 };
    };
    const title = (t) => svg.append(s("text", { x: W / 2, y: 16, "text-anchor": "middle", class: "title" }, t));
    const fail = () => {
      svg.replaceChildren(s("text", { x: W / 2, y: H / 2, "text-anchor": "middle", class: "title" }, "Sketch unavailable — check the inputs"));
    };
    const dimH = (x1, x2, y, label) => {
      svg.append(s("path", { d: `M${x1} ${y}H${x2}M${x1} ${y - 4}v8M${x2} ${y - 4}v8`, class: "dim" }));
      svg.append(s("text", { x: (x1 + x2) / 2, y: y + 13, "text-anchor": "middle" }, label));
    };
    const dimV = (x, y1, y2, label) => {
      svg.append(s("path", { d: `M${x} ${y1}V${y2}M${x - 4} ${y1}h8M${x - 4} ${y2}h8`, class: "dim" }));
      svg.append(s("text", { x: x - 6, y: (y1 + y2) / 2, "text-anchor": "end", "dominant-baseline": "middle" }, label));
    };
    try {
      if (dtValue === "column" && raw.shape === "Circular") {
        if (!pos("width")) return container.replaceChildren(svg), fail();
        const d = v.width, f = fit(d, d), r = d * f.scale / 2, cx = W / 2, cy = f.y0 + r;
        svg.append(s("circle", { cx, cy, r, class: "shape" }));
        if (v.cover > 0 && v.cover < d / 2) svg.append(s("circle", { cx, cy, r: r - v.cover * f.scale, class: "inner" }));
        title(`Circular column D = ${RC.g(d)} mm`);
        dimH(cx - r, cx + r, cy + r + 10, `${RC.g(d)}`);
      } else if (dtValue === "column" || dtValue === "beam") {
        if (!pos("width", "depth")) return container.replaceChildren(svg), fail();
        const b = v.width, d = v.depth, f = fit(b, d), x = f.x0, y = f.y0, w = b * f.scale, hh = d * f.scale;
        svg.append(s("rect", { x, y, width: w, height: hh, class: "shape" }));
        const c = v.cover || 0;
        if (c > 0 && 2 * c < Math.min(b, d)) svg.append(s("rect", { x: x + c * f.scale, y: y + c * f.scale, width: w - 2 * c * f.scale, height: hh - 2 * c * f.scale, class: "inner" }));
        title(`${dtValue === "beam" ? "Beam" : "Column"} section ${RC.g(b)} × ${RC.g(d)} mm`);
        dimH(x, x + w, y + hh + 10, RC.g(b));
        dimV(x - 10, y, y + hh, RC.g(d));
      } else if (dtValue === "slab") {
        if (!pos("short_span", "long_span")) return container.replaceChildren(svg), fail();
        const lx = v.short_span, ly = v.long_span, f = fit(ly, lx), w = ly * f.scale, hh = lx * f.scale;
        svg.append(s("rect", { x: f.x0, y: f.y0, width: w, height: hh, class: "shape" }));
        title(`${raw.slab_type || ""} slab plan`);
        dimH(f.x0, f.x0 + w, f.y0 + hh + 10, `Ly = ${RC.g(ly)} m`);
        dimV(f.x0 - 10, f.y0, f.y0 + hh, `Lx = ${RC.g(lx)} m`);
      } else if (dtValue === "stair") {
        if (!pos("floor_height", "riser", "tread")) return container.replaceChildren(svg), fail();
        const n = Math.max(1, Math.ceil(v.floor_height / v.riser - 1e-9));
        if (n > 200) return container.replaceChildren(svg), fail();
        const actual = v.floor_height / n, run = Math.max((n - 1) * v.tread, v.tread);
        const f = fit(run, v.floor_height), X = (x) => f.x0 + x * f.scale, Y = (y) => f.y0 + (v.floor_height - y) * f.scale;
        let x = 0, y = 0, d = `M${X(0)} ${Y(0)}`;
        for (let i = 0; i < n; i++) { y += actual; d += `L${X(x)} ${Y(y)}`; if (i < n - 1) { x += v.tread; d += `L${X(x)} ${Y(y)}`; } }
        d += `L${X(x)} ${Y(y - actual * 0.6)}L${X(v.tread * 0.6)} ${Y(0)}Z`;
        svg.append(s("path", { d, class: "shape" }));
        title(`${n} risers × ${actual.toFixed(0)} mm, tread ${RC.g(v.tread)} mm`);
      } else if (dtValue === "footing") {
        if (!pos("width", "length")) return container.replaceChildren(svg), fail();
        const B = v.width, L = v.length, f = fit(B, L), w = B * f.scale, hh = L * f.scale;
        svg.append(s("rect", { x: f.x0, y: f.y0, width: w, height: hh, class: "shape" }));
        const cx = (v.column_width || 0) / 1000, cy = (v.column_depth || 0) / 1000;
        if (cx > 0 && cy > 0 && cx < B && cy < L) {
          svg.append(s("rect", { x: f.x0 + (B - cx) / 2 * f.scale, y: f.y0 + (L - cy) / 2 * f.scale, width: cx * f.scale, height: cy * f.scale, class: "col" }));
        }
        title(`Footing plan ${RC.g(B)} × ${RC.g(L)} m`);
        dimH(f.x0, f.x0 + w, f.y0 + hh + 10, `B = ${RC.g(B)} m`);
        dimV(f.x0 - 10, f.y0, f.y0 + hh, `L = ${RC.g(L)}`);
      }
    } catch (e) {
      fail();
    }
    container.replaceChildren(svg);
  }

  // ================================================================ materials view
  function renderMaterials() {
    const p = state.project;
    const k = SPEC.app.ksc_to_mpa;
    const ds = p.design_settings;
    const fmt = (x) => (x === null || x === undefined || x === "" ? "by standard" : RC.g(Number(x)));
    const table = (heads, rows, numeric) => h("div", { class: "table-wrap" }, h("table", {},
      h("thead", {}, h("tr", {}, heads.map((t, i) => h("th", { style: numeric.includes(i) ? "text-align:right" : null }, t)))),
      h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c, i) => h("td", { class: numeric.includes(i) ? "v" : null }, c)))))));
    const tags = (name, kind) => {
      const out = [];
      if (kind === "concrete" && ds.default_concrete === name) out.push("default");
      if (kind === "rebar_grade" && ds.default_main_rebar === name) out.push("default main");
      if (kind === "rebar_grade" && ds.default_tie_rebar === name) out.push("default ties");
      const n = RC.materialUsage(p, kind, name);
      if (n) out.unshift(`${n} member(s)`);
      return out.join(", ") || "—";
    };
    return h("div", {},
      h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Project Materials"),
        h("p", {}, "Materials stored in this project file. To create or edit materials, use Tools → Material Database in the desktop program."))),
      h("div", { class: "out-stack" },
        h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Concrete"),
          table(["Name", "f'c (ksc)", "f'c (MPa)", "Unit wt (kg/m³)", "Ec (ksc)", "Used by"],
            p.materials.concrete.map((c) => [c.name, RC.g(c.fc_ksc), (c.fc_ksc * k).toFixed(2), RC.g(c.unit_weight_kg_m3 ?? 2400), fmt(c.ec_ksc), tags(c.name, "concrete")]),
            [1, 2, 3, 4])),
        h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Reinforcement Grades"),
          table(["Name", "Bar type", "fy (ksc)", "fy (MPa)", "fu (ksc)", "Es (ksc)", "Product standard", "Used by"],
            p.reinforcement.grades.map((g) => [g.name, g.bar_type, RC.g(g.fy_ksc), (g.fy_ksc * k).toFixed(1), g.fu_ksc ? RC.g(g.fu_ksc) : "—", fmt(g.es_ksc), g.standard || "", tags(g.name, "rebar_grade")]),
            [2, 3, 4, 5])),
        h("section", { class: "panel" }, h("div", { class: "panel-head" }, "Bar Sizes"),
          table(["Designation", "Bar type", "Diameter (mm)", "Area (mm²)"],
            p.reinforcement.sizes.map((b) => [b.designation, b.bar_type, RC.g(b.diameter_mm), (Math.PI * b.diameter_mm ** 2 / 4).toFixed(1)]),
            [2, 3])),
        h("p", { class: "brand-sub" }, "1 ksc = 0.0980665 MPa · bar area = π·d²/4 · Ec / Es “by standard” will be taken from the selected design standard in a later phase.")));
  }

  // ================================================================ help
  function renderHelp() {
    return h("div", { class: "prose" },
      h("div", { class: "view-head" }, h("div", {}, h("h1", {}, "Help"), h("p", {}, `${SPEC.app.name} v${SPEC.app.version} · ${SPEC.app.phase} · Web`))),
      h("div", { class: "banner" }, h("b", {}, "Phase notice."),
        h("span", {}, "Only geometric quantities are calculated. Structural design checks according to the selected standard are not implemented yet. Do not use the results for construction.")),
      h("h2", {}, "1. Start a project"),
      h("ol", {}, h("li", {}, "Press New, enter the Project Name and choose the design standard and unit system."),
        h("li", {}, "Open the Design tab and pick Column, Beam, Slab, Stair or Footing."),
        h("li", {}, "Add a member, fill in the form (fields with * are required) and press Calculate."),
        h("li", {}, "Report shows the calculation sheet; you can copy it or save it as a .txt file.")),
      h("h2", {}, "2. Save and open"),
      h("ul", {}, h("li", {}, "Save gives you a file named like project.rcproj.json. The desktop program opens it directly."),
        h("li", {}, "Open accepts .rcproj files from the desktop program and .rcproj.json files saved here."),
        h("li", {}, "Your work is also kept in this browser between visits, but only on this device. Save a file to keep it safe or move it to another device.")),
      h("h2", {}, "3. Units"),
      h("p", {}, "Section dimensions are in mm and spans in m. Loads follow the unit system of the project (SI: kN, kN·m, kN/m² · MKS: kgf, kgf·m, kgf/m²). Changing the unit system later does not convert values already entered."),
      h("h2", {}, "4. Same engine as the desktop program"),
      h("p", {}, "Input fields, limits, units and built-in materials are generated from the desktop program's Python code. The web calculations are tested against the Python results."),
      h("h2", {}, "5. Reset"),
      h("p", {}, "Reset closes the current project and deletes the copy kept in this browser, so you can start a new job. Saved project files are not affected."),
      h("button", { class: "btn danger", type: "button", onclick: resetData }, "Reset this browser's data"));
  }

  // ================================================================ modals
  function modal(title, body, buttons, narrow) {
    const root = document.getElementById("modal-root");
    let back = null;
    // Only close this dialog; a button may already have opened the next one.
    const close = () => {
      document.removeEventListener("keydown", onKey);
      if (back && back.isConnected) root.replaceChildren();
    };
    const onKey = (e) => { if (e.key === "Escape") close(); };
    document.addEventListener("keydown", onKey);
    const footer = h("footer", {}, buttons.map(([label, cls, fn]) =>
      h("button", { class: "btn " + (cls || ""), type: "button", onclick: () => { if (fn() !== false) close(); } }, label)));
    const box = h("div", { class: "modal" + (narrow ? " narrow" : ""), role: "dialog", "aria-modal": "true", "aria-label": title },
      h("header", {}, h("h2", {}, title)), h("div", { class: "body" }, body), footer);
    back = h("div", { class: "modal-back", onclick: (e) => { if (e.target === back) close(); } }, box);
    root.replaceChildren(back);
    const first = box.querySelector("input, select, textarea, button.primary");
    if (first) first.focus();
    return close;
  }

  function confirmBox(title, text, okLabel, onOk) {
    modal(title, h("p", {}, text), [["Cancel", "", () => {}], [okLabel, "primary", () => { onOk(); }]], true);
  }

  function confirmDiscard(next) {
    if (!state.project || !state.modified) { next(); return; }
    confirmBox("Unsaved changes",
      `The project “${state.project.project_information.project_name || "Untitled"}” has changes that are not saved to a file. Continue without saving?`,
      "Continue without saving", next);
  }

  function newProjectDialog() {
    const info = RC.emptyInfo();
    const settings = Object.assign({}, SPEC.default_settings);
    const err = h("p", { class: "err", hidden: true });
    const grid = h("div", { class: "form-grid" });
    for (const [key, label, required] of INFO_FIELDS) {
      grid.append(textField(`new-${key}`, label, info[key], (value) => { info[key] = value; },
        { required, type: key === "project_date" ? "date" : "text" }));
    }
    grid.append(
      selectField("new-standard", "Design Standard", SPEC.standards.map((x) => [x.value, x.label]), settings.design_standard, (v) => { settings.design_standard = v; }),
      selectField("new-units", "Unit System", SPEC.units.map((x) => [x.value, x.label]), settings.unit_system, (v) => { settings.unit_system = v; }));
    modal("New Project", h("div", {}, grid, err), [
      ["Cancel", "", () => {}],
      ["Create", "primary", () => {
        if (!info.project_name.trim()) {
          err.hidden = false; err.textContent = "Project Name is required.";
          const f = document.getElementById("new-project_name");
          const field = f.closest(".field");
          field.classList.add("invalid");
          const fieldErr = field.querySelector(".err");
          fieldErr.hidden = false; fieldErr.textContent = "Project Name is required.";
          f.focus();
          return false;
        }
        for (const k of Object.keys(info)) info[k] = String(info[k]).trim();
        state.project = RC.newProject(info, settings);
        state.fileName = ""; state.modified = true; state.selected = {};
        go("design");
        toast("New project created. Select a design type.");
        return true;
      }]]);
  }

  async function openReport(dtValue, member) {
    const text = RC.buildReport(state.project, dtValue, member);
    const pre = h("pre", { class: "report" }, text);
    const base = `${dtValue}_${member.name || "member"}`.replace(/[^\w\-]+/g, "_");
    modal(`${dtByValue(dtValue).title} ${member.name} — Calculation Report`, pre, [
      ["Copy", "", () => { copyText(text, pre); return false; }],
      ["Save as .txt", "", () => { saveFile(`${base}_report.txt`, text, "Report saved."); return false; }],
      ["Close", "primary", () => {}]]);
  }

  async function copyText(text, fallbackEl) {
    try {
      await navigator.clipboard.writeText(text);
      toast("Copied to clipboard.");
    } catch (e) {
      if (fallbackEl) {
        const range = document.createRange();
        range.selectNodeContents(fallbackEl);
        const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(range);
      }
      toast("Copy is blocked here. The text is selected; press Ctrl+C.", true);
    }
  }

  // ================================================================ file operations
  let downloadsPromise = null;
  function downloads() {
    if (!downloadsPromise) {
      downloadsPromise = (window.claude && typeof window.claude.use === "function")
        ? window.claude.use("downloads").catch(() => null)
        : Promise.resolve(null);
    }
    return downloadsPromise;
  }

  async function saveFile(filename, data, okMessage) {
    const dl = await downloads();
    if (!dl) { showRawFile(filename, data); return false; }
    try {
      await dl.save({ filename, data });
      toast(okMessage);
      return true;
    } catch (e) {
      const code = e && e.code;
      if (code === "declined") toast("Save cancelled.");
      else if (code === "rate_limited") toast("A save prompt is already open.", true);
      else showRawFile(filename, data);
      return false;
    }
  }

  function showRawFile(filename, data) {
    const ta = h("textarea", { class: "raw", readonly: true });
    ta.value = data;
    modal("Save manually", h("div", {},
      h("p", {}, `Saving files is not available in this view. Copy the text below and save it as “${filename}”.`), ta), [
      ["Copy", "", () => { copyText(data, null); ta.select(); return false; }],
      ["Close", "primary", () => {}]]);
  }

  function projectFileName() {
    if (state.fileName) {
      return state.fileName.toLowerCase().endsWith(".json") ? state.fileName : state.fileName + ".json";
    }
    const name = (state.project.project_information.project_name || "Untitled").replace(/[\\/:*?"<>|]+/g, "_").trim();
    return `${name || "Untitled"}${SPEC.app.extension}.json`;
  }

  async function saveProject() {
    if (!state.project) return;
    const filename = projectFileName();
    const data = JSON.stringify(RC.serialize(state.project), null, 2) + "\n";
    const ok = await saveFile(filename, data, `Saved ${filename}`);
    if (ok) {
      state.fileName = filename; state.modified = false;
      updateChrome(); persist();
      if (state.view === "project") render();
    }
  }

  function openProject() {
    confirmDiscard(() => document.getElementById("file-input").click());
  }

  function onFileChosen(e) {
    const file = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const project = RC.deserialize(JSON.parse(String(reader.result)));
        state.project = project; state.fileName = file.name; state.modified = false; state.selected = {};
        go("design");
        toast(`Opened ${file.name}`);
      } catch (err) {
        const msg = err instanceof SyntaxError
          ? `“${file.name}” is corrupted or is not a valid project file.` : err.message;
        modal("Open Project", h("p", {}, "The project could not be opened.", h("br"), msg), [["OK", "primary", () => {}]], true);
      }
    };
    reader.onerror = () => toast("The file could not be read.", true);
    reader.readAsText(file);
  }

  // ================================================================ start
  // iPad / iPhone: unknown extensions such as .rcproj are greyed out in the
  // Files picker when "accept" is set, so only filter on other systems.
  function isAppleTouch() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent)
      || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  }

  // Hardware keyboard shortcuts (iPad Magic Keyboard, desktop browsers).
  function onShortcut(e) {
    const mod = e.metaKey || e.ctrlKey;
    if (!mod) return;
    const key = e.key.toLowerCase();
    if (key === "s" && state.project) { e.preventDefault(); saveProject(); }
    else if (key === "enter") {
      const btn = document.getElementById("btn-calculate");
      if (btn) { e.preventDefault(); btn.click(); }
    }
  }

  function start() {
    if (!isAppleTouch()) document.getElementById("file-input").setAttribute("accept", ".rcproj,.json,application/json");
    document.addEventListener("keydown", onShortcut);
    const restored = restore();
    if (!restored) { state.project = null; state.view = "start"; }
    const fromHash = location.hash.replace("#", "");
    if (VIEWS.includes(fromHash)) state.view = fromHash;
    if (!state.project && state.view !== "help") state.view = "start";
    document.getElementById("btn-new").addEventListener("click", () => confirmDiscard(newProjectDialog));
    document.getElementById("btn-open").addEventListener("click", openProject);
    document.getElementById("btn-save").addEventListener("click", saveProject);
    document.getElementById("file-input").addEventListener("change", onFileChosen);
    window.addEventListener("pagehide", flushStore);
    document.addEventListener("visibilitychange", () => { if (document.hidden) flushStore(); });
    window.addEventListener("hashchange", () => {
      const v = location.hash.replace("#", "");
      if (VIEWS.includes(v) && v !== state.view) go(v);
    });
    render();
    downloads();
    if (restored) toast("Restored your last session from this browser.");
  }

  start();
})();
