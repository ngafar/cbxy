const PAD = 0.04;
const TURN_MS = 420;
const USER_ZOOM_MIN = 0.4;
const USER_ZOOM_MAX = 5;
const DRAG_PX = 6;
const MIN_VISIBLE = 64;

const state = {
  book: null,
  pageIndex: 0,
  // -1 = full page view; 0..n-1 = panel zoom
  panelIndex: -1,
  // After the last panel we return to a full-page "outro" before the next page.
  outro: false,
  turning: false,
  guided: true,
  userZoom: 1,
  panX: 0,
  panY: 0,
};

const els = {
  title: document.getElementById("title"),
  status: document.getElementById("status"),
  viewport: document.getElementById("viewport"),
  turn: document.getElementById("turn"),
  camera: document.getElementById("camera"),
  page: document.getElementById("page"),
  guided: document.getElementById("guided"),
  zoomOut: document.getElementById("zoomOut"),
  zoomIn: document.getElementById("zoomIn"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
};

function currentPage() {
  return state.book.pages[state.pageIndex];
}

function panels() {
  return currentPage().panels || [];
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

function cameraOverridden() {
  return state.userZoom !== 1 || state.panX !== 0 || state.panY !== 0;
}

function resetView() {
  state.userZoom = 1;
  state.panX = 0;
  state.panY = 0;
}

function updateStatus() {
  const total = state.book.pages.length;
  let text;
  if (!state.guided) {
    text = `Page ${state.pageIndex + 1}/${total}`;
  } else {
    const p = panels();
    const view =
      state.panelIndex < 0
        ? `panel 0/${p.length}`
        : `panel ${state.panelIndex + 1}/${p.length}`;
    text = `Page ${state.pageIndex + 1}/${total} · ${view}`;
  }
  if (cameraOverridden()) {
    text += ` · ${Math.round(state.userZoom * 100)}%`;
  }
  els.status.textContent = text;
}

function activePanel() {
  if (!state.guided) return null;
  const p = panels();
  if (state.panelIndex < 0 || !p.length) return null;
  return p[state.panelIndex];
}

function syncGuidedButton() {
  els.guided.classList.toggle("active", state.guided);
  els.guided.setAttribute("aria-pressed", state.guided ? "true" : "false");
}

function setGuided(enabled) {
  if (state.turning) return;
  state.guided = enabled;
  state.panelIndex = -1;
  state.outro = false;
  resetView();
  syncGuidedButton();
  applyCamera({ animate: true });
}

function fitPageTransform(vw, vh, iw, ih) {
  const scale = Math.min(vw / iw, vh / ih);
  const tx = (vw - iw * scale) / 2;
  const ty = (vh - ih * scale) / 2;
  return { tx, ty, scale };
}

function panelTransform(vw, vh, iw, ih, panel) {
  const x = panel.x * iw;
  const y = panel.y * ih;
  const w = panel.w * iw;
  const h = panel.h * ih;
  const padX = panel.w * PAD * iw;
  const padY = panel.h * PAD * ih;
  const bx = Math.max(0, x - padX);
  const by = Math.max(0, y - padY);
  const bw = Math.min(iw - bx, w + padX * 2);
  const bh = Math.min(ih - by, h + padY * 2);
  const scale = Math.min(vw / bw, vh / bh);
  const cx = (bx + bw / 2) * scale;
  const cy = (by + bh / 2) * scale;
  return {
    tx: vw / 2 - cx,
    ty: vh / 2 - cy,
    scale,
  };
}

function maskInset(panel) {
  if (!panel) return "inset(0% 0% 0% 0%)";
  const top = panel.y * 100;
  const right = (1 - panel.x - panel.w) * 100;
  const bottom = (1 - panel.y - panel.h) * 100;
  const left = panel.x * 100;
  return `inset(${top}% ${right}% ${bottom}% ${left}%)`;
}

function cameraSize() {
  return {
    vw: els.viewport.clientWidth,
    vh: els.viewport.clientHeight,
    iw: els.page.naturalWidth,
    ih: els.page.naturalHeight,
  };
}

function baseTransform() {
  const { vw, vh, iw, ih } = cameraSize();
  if (!iw || !ih || !vw || !vh) return null;
  const panel = activePanel();
  return panel
    ? panelTransform(vw, vh, iw, ih, panel)
    : fitPageTransform(vw, vh, iw, ih);
}

function composedTransform(base) {
  const { vw, vh } = cameraSize();
  const z = state.userZoom;
  return {
    tx: base.tx * z + (vw / 2) * (1 - z) + state.panX,
    ty: base.ty * z + (vh / 2) * (1 - z) + state.panY,
    scale: base.scale * z,
  };
}

function clampPan(base) {
  const { vw, vh, iw, ih } = cameraSize();
  const z = state.userZoom;
  const scale = base.scale * z;
  const tx0 = base.tx * z + (vw / 2) * (1 - z);
  const ty0 = base.ty * z + (vh / 2) * (1 - z);
  const minTx = MIN_VISIBLE - iw * scale;
  const maxTx = vw - MIN_VISIBLE;
  const minTy = MIN_VISIBLE - ih * scale;
  const maxTy = vh - MIN_VISIBLE;
  if (minTx <= maxTx) {
    state.panX = clamp(state.panX, minTx - tx0, maxTx - tx0);
  }
  if (minTy <= maxTy) {
    state.panY = clamp(state.panY, minTy - ty0, maxTy - ty0);
  }
}

function applyCamera({ animate = true } = {}) {
  const base = baseTransform();
  if (!base) return;
  clampPan(base);
  const t = composedTransform(base);
  const panel = activePanel();

  const transition = animate ? "" : "none";
  els.camera.style.transition = transition;
  els.page.style.transition = transition;

  els.camera.style.transform = `translate(${t.tx}px, ${t.ty}px) scale(${t.scale})`;
  // Lift the panel mask while panning/zooming so a tight box can be corrected.
  els.page.style.clipPath = cameraOverridden() ? "inset(0% 0% 0% 0%)" : maskInset(panel);

  updateStatus();
}

function zoomAt(vx, vy, factor) {
  const base = baseTransform();
  if (!base) return;
  const { vw, vh } = cameraSize();
  const z0 = state.userZoom;
  const z1 = clamp(z0 * factor, USER_ZOOM_MIN, USER_ZOOM_MAX);
  if (z1 === z0) return;

  const tx0 = base.tx * z0 + (vw / 2) * (1 - z0) + state.panX;
  const ty0 = base.ty * z0 + (vh / 2) * (1 - z0) + state.panY;
  const s0 = base.scale * z0;
  const s1 = base.scale * z1;
  if (s0 <= 0) return;

  const qx = (vx - tx0) / s0;
  const qy = (vy - ty0) / s0;
  state.userZoom = z1;
  state.panX = vx - qx * s1 - base.tx * z1 - (vw / 2) * (1 - z1);
  state.panY = vy - qy * s1 - base.ty * z1 - (vh / 2) * (1 - z1);
  applyCamera({ animate: false });
}

function zoomBy(factor) {
  zoomAt(els.viewport.clientWidth / 2, els.viewport.clientHeight / 2, factor);
}

function waitOpacity(el) {
  return new Promise((resolve) => {
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      el.removeEventListener("transitionend", onEnd);
      resolve();
    };
    const onEnd = (e) => {
      if (e.target === el && e.propertyName === "opacity") finish();
    };
    el.addEventListener("transitionend", onEnd);
    setTimeout(finish, TURN_MS + 80);
  });
}

function setTurnStyle({ opacity, xPercent, scale, animate }) {
  els.turn.style.transition = animate ? "" : "none";
  els.turn.style.opacity = String(opacity);
  els.turn.style.transform = `translateX(${xPercent}%) scale(${scale})`;
}

function loadPageImage() {
  const page = currentPage();
  const img = els.page;

  return new Promise((resolve) => {
    const finish = () => {
      applyCamera({ animate: false });
      resolve();
    };

    if (img.dataset.src === page.image && img.complete && img.naturalWidth) {
      finish();
      return;
    }

    const onLoad = () => {
      img.removeEventListener("load", onLoad);
      finish();
    };
    img.addEventListener("load", onLoad);
    img.dataset.src = page.image;
    img.src = page.image;
    img.alt = page.name;
  });
}

async function showPage(
  index,
  { resetPanel = true, outro = false, direction = null } = {},
) {
  const pages = state.book.pages;
  const nextIndex = Math.max(0, Math.min(index, pages.length - 1));
  const animateTurn = direction === 1 || direction === -1;

  if (animateTurn) {
    if (state.turning) return;
    state.turning = true;

    // Exit: drift toward the turn direction and fade out.
    setTurnStyle({
      opacity: 0,
      xPercent: direction > 0 ? -7 : 7,
      scale: 0.96,
      animate: true,
    });
    await waitOpacity(els.turn);

    resetView();
    state.pageIndex = nextIndex;
    if (resetPanel) {
      state.panelIndex = -1;
      state.outro = outro;
    }
    await loadPageImage();

    // Enter from the opposite side, then settle.
    setTurnStyle({
      opacity: 0,
      xPercent: direction > 0 ? 7 : -7,
      scale: 0.96,
      animate: false,
    });
    void els.turn.offsetWidth;
    setTurnStyle({
      opacity: 1,
      xPercent: 0,
      scale: 1,
      animate: true,
    });
    await waitOpacity(els.turn);
    state.turning = false;
    return;
  }

  resetView();
  state.pageIndex = nextIndex;
  if (resetPanel) {
    state.panelIndex = -1;
    state.outro = outro;
  }
  await loadPageImage();
  setTurnStyle({ opacity: 1, xPercent: 0, scale: 1, animate: false });
}

function goNext() {
  if (state.turning) return;
  resetView();

  if (!state.guided) {
    if (state.pageIndex < state.book.pages.length - 1) {
      showPage(state.pageIndex + 1, {
        resetPanel: true,
        outro: false,
        direction: 1,
      });
    } else {
      applyCamera({ animate: true });
    }
    return;
  }

  const p = panels();

  if (state.panelIndex < 0 && !state.outro && p.length) {
    state.panelIndex = 0;
    applyCamera({ animate: true });
    return;
  }

  if (state.panelIndex >= 0 && state.panelIndex < p.length - 1) {
    state.panelIndex += 1;
    applyCamera({ animate: true });
    return;
  }

  if (state.panelIndex === p.length - 1 && p.length) {
    state.panelIndex = -1;
    state.outro = true;
    applyCamera({ animate: true });
    return;
  }

  if (state.pageIndex < state.book.pages.length - 1) {
    showPage(state.pageIndex + 1, {
      resetPanel: true,
      outro: false,
      direction: 1,
    });
  } else {
    applyCamera({ animate: true });
  }
}

function goPrev() {
  if (state.turning) return;
  resetView();

  if (!state.guided) {
    if (state.pageIndex > 0) {
      showPage(state.pageIndex - 1, {
        resetPanel: true,
        outro: false,
        direction: -1,
      });
    } else {
      applyCamera({ animate: true });
    }
    return;
  }

  const p = panels();

  if (state.panelIndex < 0 && state.outro && p.length) {
    state.outro = false;
    state.panelIndex = p.length - 1;
    applyCamera({ animate: true });
    return;
  }

  if (state.panelIndex > 0) {
    state.panelIndex -= 1;
    applyCamera({ animate: true });
    return;
  }
  if (state.panelIndex === 0) {
    state.panelIndex = -1;
    state.outro = false;
    applyCamera({ animate: true });
    return;
  }

  if (state.pageIndex > 0) {
    const prevIndex = state.pageIndex - 1;
    const prevPanels = state.book.pages[prevIndex].panels || [];
    showPage(prevIndex, {
      resetPanel: true,
      outro: prevPanels.length > 0,
      direction: -1,
    });
  } else {
    applyCamera({ animate: true });
  }
}

function viewportPoint(e) {
  const r = els.viewport.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}

function bindPanZoom() {
  const pointers = new Map();
  let pan = null;
  let pinch = null;
  let suppressClick = false;

  function pinchMetrics() {
    const pts = [...pointers.values()];
    const dx = pts[1].x - pts[0].x;
    const dy = pts[1].y - pts[0].y;
    return {
      dist: Math.hypot(dx, dy) || 1,
      x: (pts[0].x + pts[1].x) / 2,
      y: (pts[0].y + pts[1].y) / 2,
    };
  }

  els.viewport.addEventListener("pointerdown", (e) => {
    if (state.turning || e.button > 0) return;
    const p = viewportPoint(e);
    pointers.set(e.pointerId, p);
    els.viewport.setPointerCapture(e.pointerId);

    if (pointers.size === 2) {
      pan = null;
      pinch = pinchMetrics();
      suppressClick = true;
      return;
    }

    pan = { id: e.pointerId, x: p.x, y: p.y, moved: false };
  });

  els.viewport.addEventListener("pointermove", (e) => {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, viewportPoint(e));

    if (pointers.size >= 2 && pinch) {
      const now = pinchMetrics();
      zoomAt(now.x, now.y, now.dist / pinch.dist);
      state.panX += now.x - pinch.x;
      state.panY += now.y - pinch.y;
      pinch = now;
      applyCamera({ animate: false });
      els.viewport.classList.add("is-panning");
      return;
    }

    if (!pan || e.pointerId !== pan.id) return;
    const p = pointers.get(e.pointerId);
    const dx = p.x - pan.x;
    const dy = p.y - pan.y;
    if (!pan.moved && Math.hypot(dx, dy) < DRAG_PX) return;
    pan.moved = true;
    suppressClick = true;
    state.panX += dx;
    state.panY += dy;
    pan.x = p.x;
    pan.y = p.y;
    els.viewport.classList.add("is-panning");
    applyCamera({ animate: false });
  });

  function endPointer(e) {
    pointers.delete(e.pointerId);
    if (pan && e.pointerId === pan.id) pan = null;
    if (pointers.size < 2) pinch = null;
    if (pointers.size === 0) {
      els.viewport.classList.remove("is-panning");
      try {
        els.viewport.releasePointerCapture(e.pointerId);
      } catch {
        /* already released */
      }
    }
  }

  els.viewport.addEventListener("pointerup", endPointer);
  els.viewport.addEventListener("pointercancel", endPointer);

  els.viewport.addEventListener("click", (e) => {
    if (suppressClick) {
      suppressClick = false;
      e.preventDefault();
      return;
    }
    goNext();
  });

  els.viewport.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      if (state.turning) return;
      const p = viewportPoint(e);
      zoomAt(p.x, p.y, Math.exp(-e.deltaY * 0.0015));
    },
    { passive: false },
  );
}

async function boot() {
  const res = await fetch("/api/book");
  state.book = await res.json();
  els.title.textContent = state.book.title;
  document.title = `${state.book.title} · cbxy`;
  syncGuidedButton();

  els.guided.addEventListener("click", (e) => {
    e.stopPropagation();
    setGuided(!state.guided);
  });
  els.next.addEventListener("click", (e) => {
    e.stopPropagation();
    goNext();
  });
  els.prev.addEventListener("click", (e) => {
    e.stopPropagation();
    goPrev();
  });
  els.zoomIn.addEventListener("click", (e) => {
    e.stopPropagation();
    zoomBy(1.2);
  });
  els.zoomOut.addEventListener("click", (e) => {
    e.stopPropagation();
    zoomBy(1 / 1.2);
  });

  bindPanZoom();

  window.addEventListener("keydown", (e) => {
    if (e.key === "g" || e.key === "G") {
      e.preventDefault();
      setGuided(!state.guided);
      return;
    }
    if (e.key === "+" || e.key === "=") {
      e.preventDefault();
      zoomBy(1.2);
      return;
    }
    if (e.key === "-" || e.key === "_") {
      e.preventDefault();
      zoomBy(1 / 1.2);
      return;
    }
    if (e.key === "0") {
      e.preventDefault();
      resetView();
      applyCamera({ animate: true });
      return;
    }
    if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") {
      e.preventDefault();
      goNext();
    } else if (e.key === "ArrowLeft" || e.key === "Backspace") {
      e.preventDefault();
      goPrev();
    }
  });

  window.addEventListener("resize", () => {
    if (!state.turning) applyCamera({ animate: false });
  });

  await showPage(0, { resetPanel: true, outro: false });
}

boot().catch((err) => {
  els.title.textContent = "Failed to load book";
  els.status.textContent = String(err);
  console.error(err);
});
