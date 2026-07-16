const state = {
  book: null,
  pageIndex: 0,
  selected: -1,
  dirty: false,
};

const els = {
  title: document.getElementById("title"),
  meta: document.getElementById("meta"),
  pageList: document.getElementById("pageList"),
  panelList: document.getElementById("panelList"),
  stage: document.getElementById("stage"),
  pageImage: document.getElementById("pageImage"),
  overlays: document.getElementById("overlays"),
  add: document.getElementById("add"),
  delete: document.getElementById("delete"),
  save: document.getElementById("save"),
};

function currentPage() {
  return state.book.pages[state.pageIndex];
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function markDirty() {
  state.dirty = true;
  state.book.dirty = true;
  updateMeta();
  els.save.classList.add("dirty");
}

function updateMeta() {
  const side = state.book.sidecar_exists
    ? state.book.sidecar
    : `${state.book.sidecar} (new)`;
  const dirty = state.dirty ? " · unsaved" : "";
  els.meta.textContent = `${side}${dirty}`;
}

function renderPageList() {
  const existing = els.pageList.querySelectorAll(".page-item");
  if (existing.length === state.book.pages.length) {
    existing.forEach((btn, i) => {
      btn.classList.toggle("selected", i === state.pageIndex);
      const count = btn.querySelector(".count");
      if (count) {
        count.textContent = `${state.book.pages[i].panels.length} panels`;
      }
    });
    return;
  }

  els.pageList.innerHTML = "<h2>Pages</h2>";
  state.book.pages.forEach((page, i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className =
      "item page-item" + (i === state.pageIndex ? " selected" : "");
    btn.innerHTML = `
      <img class="thumb" src="${page.image}" alt="" loading="lazy" draggable="false" />
      <span class="page-meta">
        <span class="num">${i + 1}</span>
        <span class="count">${page.panels.length} panels</span>
      </span>`;
    btn.title = page.name;
    btn.addEventListener("click", () => selectPage(i));
    els.pageList.appendChild(btn);
  });
}

function renderPanelList() {
  const page = currentPage();
  els.panelList.innerHTML = "<h2>Reading order</h2>";

  const actions = document.createElement("div");
  actions.className = "panel-actions";
  const up = document.createElement("button");
  up.type = "button";
  up.textContent = "↑";
  up.title = "Move earlier";
  up.disabled = state.selected < 0;
  up.addEventListener("click", () => moveSelected(-1));
  const down = document.createElement("button");
  down.type = "button";
  down.textContent = "↓";
  down.title = "Move later";
  down.disabled = state.selected < 0;
  down.addEventListener("click", () => moveSelected(1));
  actions.append(up, down);
  els.panelList.appendChild(actions);

  page.panels.forEach((panel, i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "item" + (i === state.selected ? " selected" : "");
    btn.innerHTML = `<span class="num">${i + 1}</span><span class="label">x=${panel.x.toFixed(2)} y=${panel.y.toFixed(2)}<br>w=${panel.w.toFixed(2)} h=${panel.h.toFixed(2)}</span>`;
    btn.addEventListener("click", () => selectPanel(i));
    els.panelList.appendChild(btn);
  });

  els.delete.disabled = state.selected < 0;
}

function renderBoxes() {
  els.overlays.innerHTML = "";
  const page = currentPage();
  page.panels.forEach((panel, i) => {
    const box = document.createElement("div");
    box.className = "box" + (i === state.selected ? " selected" : "");
    box.style.left = `${panel.x * 100}%`;
    box.style.top = `${panel.y * 100}%`;
    box.style.width = `${panel.w * 100}%`;
    box.style.height = `${panel.h * 100}%`;
    box.dataset.index = String(i);

    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = String(i + 1);
    box.appendChild(badge);

    if (i === state.selected) {
      for (const h of ["nw", "n", "ne", "e", "se", "s", "sw", "w"]) {
        const handle = document.createElement("div");
        handle.className = `handle ${h}`;
        handle.dataset.handle = h;
        box.appendChild(handle);
      }
    }

    box.addEventListener("pointerdown", onBoxPointerDown);
    els.overlays.appendChild(box);
  });
}

function refresh() {
  renderPageList();
  renderPanelList();
  renderBoxes();
  updateMeta();
}

function selectPage(index) {
  state.pageIndex = index;
  state.selected = -1;
  const page = currentPage();
  const img = els.pageImage;

  const show = () => {
    refresh();
  };

  if (img.dataset.src === page.image && img.complete) {
    show();
    return;
  }

  img.onload = show;
  img.dataset.src = page.image;
  img.src = page.image;
  img.alt = page.name;
}

function selectPanel(index) {
  state.selected = index;
  refresh();
}

function moveSelected(delta) {
  const page = currentPage();
  const i = state.selected;
  const j = i + delta;
  if (i < 0 || j < 0 || j >= page.panels.length) return;
  const tmp = page.panels[i];
  page.panels[i] = page.panels[j];
  page.panels[j] = tmp;
  state.selected = j;
  markDirty();
  refresh();
}

function addPanel() {
  const page = currentPage();
  page.panels.push({ x: 0.1, y: 0.1, w: 0.35, h: 0.3 });
  state.selected = page.panels.length - 1;
  markDirty();
  refresh();
}

function deleteSelected() {
  const page = currentPage();
  if (state.selected < 0) return;
  page.panels.splice(state.selected, 1);
  state.selected = Math.min(state.selected, page.panels.length - 1);
  if (page.panels.length === 0) state.selected = -1;
  markDirty();
  refresh();
}

function stageRect() {
  return els.stage.getBoundingClientRect();
}

function clientToNorm(clientX, clientY) {
  const r = stageRect();
  return {
    x: clamp((clientX - r.left) / r.width, 0, 1),
    y: clamp((clientY - r.top) / r.height, 0, 1),
  };
}

let drag = null;

function onBoxPointerDown(e) {
  const box = e.currentTarget;
  const index = Number(box.dataset.index);
  const handle = e.target.dataset.handle || null;

  if (state.selected !== index) {
    state.selected = index;
    refresh();
  }

  e.preventDefault();
  e.stopPropagation();

  const page = currentPage();
  const panel = { ...page.panels[index] };
  const start = clientToNorm(e.clientX, e.clientY);

  drag = {
    index,
    handle,
    start,
    origin: panel,
    pointerId: e.pointerId,
  };
  box.setPointerCapture(e.pointerId);
  box.addEventListener("pointermove", onBoxPointerMove);
  box.addEventListener("pointerup", onBoxPointerUp);
  box.addEventListener("pointercancel", onBoxPointerUp);
}

function onBoxPointerMove(e) {
  if (!drag || e.pointerId !== drag.pointerId) return;
  const cur = clientToNorm(e.clientX, e.clientY);
  const dx = cur.x - drag.start.x;
  const dy = cur.y - drag.start.y;
  const o = drag.origin;
  let { x, y, w, h } = o;

  if (!drag.handle) {
    x = clamp(o.x + dx, 0, 1 - o.w);
    y = clamp(o.y + dy, 0, 1 - o.h);
  } else {
    const hdl = drag.handle;
    if (hdl.includes("w")) {
      const nx = clamp(o.x + dx, 0, o.x + o.w - 0.02);
      w = o.w + (o.x - nx);
      x = nx;
    }
    if (hdl.includes("e")) {
      w = clamp(o.w + dx, 0.02, 1 - o.x);
    }
    if (hdl.includes("n")) {
      const ny = clamp(o.y + dy, 0, o.y + o.h - 0.02);
      h = o.h + (o.y - ny);
      y = ny;
    }
    if (hdl.includes("s")) {
      h = clamp(o.h + dy, 0.02, 1 - o.y);
    }
  }

  currentPage().panels[drag.index] = { x, y, w, h };
  // Live update without rebuilding handles mid-drag.
  const el = els.overlays.children[drag.index];
  if (el) {
    el.style.left = `${x * 100}%`;
    el.style.top = `${y * 100}%`;
    el.style.width = `${w * 100}%`;
    el.style.height = `${h * 100}%`;
  }
  markDirty();
}

function onBoxPointerUp(e) {
  if (!drag || e.pointerId !== drag.pointerId) return;
  const box = e.currentTarget;
  box.releasePointerCapture(e.pointerId);
  box.removeEventListener("pointermove", onBoxPointerMove);
  box.removeEventListener("pointerup", onBoxPointerUp);
  box.removeEventListener("pointercancel", onBoxPointerUp);
  drag = null;
  renderPanelList();
}

async function save() {
  els.save.disabled = true;
  try {
    const res = await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pages: state.book.pages }),
    });
    if (!res.ok) throw new Error(`Save failed (${res.status})`);
    const data = await res.json();
    state.book = data.book;
    state.dirty = false;
    els.save.classList.remove("dirty");
    updateMeta();
    renderPageList();
  } catch (err) {
    alert(String(err));
  } finally {
    els.save.disabled = false;
  }
}

async function boot() {
  const res = await fetch("/api/book");
  state.book = await res.json();
  state.dirty = !!state.book.dirty;
  els.title.textContent = state.book.title;
  document.title = `${state.book.title} · cbxy editor`;

  els.add.addEventListener("click", addPanel);
  els.delete.addEventListener("click", deleteSelected);
  els.save.addEventListener("click", save);

  window.addEventListener("keydown", (e) => {
    if ((e.key === "s" || e.key === "S") && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      save();
    } else if (e.key === "Delete" || e.key === "Backspace") {
      if (document.activeElement && document.activeElement.tagName === "INPUT") return;
      if (state.selected >= 0) {
        e.preventDefault();
        deleteSelected();
      }
    } else if (e.key === "n" || e.key === "N") {
      if (e.metaKey || e.ctrlKey) return;
      addPanel();
    }
  });

  window.addEventListener("beforeunload", (e) => {
    if (!state.dirty) return;
    e.preventDefault();
    e.returnValue = "";
  });

  selectPage(0);
}

boot().catch((err) => {
  els.title.textContent = "Failed to load";
  els.meta.textContent = String(err);
  console.error(err);
});
