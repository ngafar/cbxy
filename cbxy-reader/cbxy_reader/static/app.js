const PAD = 0.04;
const TURN_MS = 420;

const state = {
  book: null,
  pageIndex: 0,
  // -1 = full page view; 0..n-1 = panel zoom
  panelIndex: -1,
  // After the last panel we return to a full-page "outro" before the next page.
  outro: false,
  turning: false,
  guided: true,
};

const els = {
  title: document.getElementById("title"),
  status: document.getElementById("status"),
  viewport: document.getElementById("viewport"),
  turn: document.getElementById("turn"),
  camera: document.getElementById("camera"),
  page: document.getElementById("page"),
  guided: document.getElementById("guided"),
  prev: document.getElementById("prev"),
  next: document.getElementById("next"),
};

function currentPage() {
  return state.book.pages[state.pageIndex];
}

function panels() {
  return currentPage().panels || [];
}

function updateStatus() {
  const total = state.book.pages.length;
  if (!state.guided) {
    els.status.textContent = `Page ${state.pageIndex + 1}/${total}`;
    return;
  }
  const p = panels();
  const view =
    state.panelIndex < 0
      ? `panel 0/${p.length}`
      : `panel ${state.panelIndex + 1}/${p.length}`;
  els.status.textContent = `Page ${state.pageIndex + 1}/${total} · ${view}`;
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

function applyCamera({ animate = true } = {}) {
  const img = els.page;
  const vw = els.viewport.clientWidth;
  const vh = els.viewport.clientHeight;
  const iw = img.naturalWidth;
  const ih = img.naturalHeight;
  if (!iw || !ih || !vw || !vh) return;

  const panel = activePanel();
  const t = panel
    ? panelTransform(vw, vh, iw, ih, panel)
    : fitPageTransform(vw, vh, iw, ih);

  const transition = animate ? "" : "none";
  els.camera.style.transition = transition;
  els.page.style.transition = transition;

  els.camera.style.transform = `translate(${t.tx}px, ${t.ty}px) scale(${t.scale})`;
  els.page.style.clipPath = maskInset(panel);

  updateStatus();
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

  if (!state.guided) {
    if (state.pageIndex < state.book.pages.length - 1) {
      showPage(state.pageIndex + 1, {
        resetPanel: true,
        outro: false,
        direction: 1,
      });
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
  }
}

function goPrev() {
  if (state.turning) return;

  if (!state.guided) {
    if (state.pageIndex > 0) {
      showPage(state.pageIndex - 1, {
        resetPanel: true,
        outro: false,
        direction: -1,
      });
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
  }
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
  els.viewport.addEventListener("click", goNext);

  window.addEventListener("keydown", (e) => {
    if (e.key === "g" || e.key === "G") {
      e.preventDefault();
      setGuided(!state.guided);
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
