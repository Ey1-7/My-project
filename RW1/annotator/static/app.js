(() => {
  const $ = (id) => document.getElementById(id);

  const board = $("board");
  const ctx = board.getContext("2d");
  const canvasWrap = $("canvasWrap");
  const statusEl = $("status");

  let config = null;
  let hole = "上钻孔";
  let images = [];
  let idx = 0;
  let imgEl = new Image();
  let imgNatural = { w: 1, h: 1 };

  /** @type {'nav'|'rect'|'measure'} */
  let mode = "nav";
  let evidenceKey = "crack";

  let imageLabel = "未碎裂";
  let regions = [];
  let measurements = [];
  let notes = "";
  let annotator = "";

  let userZoom = 1;
  let panX = 0;
  let panY = 0;

  let layout = { ox: 0, oy: 0, scale: 1 };

  /** draft rect in image coords */
  let rectDraft = null;
  /** draft measure points image coords */
  let measureDraft = [];

  let dragging = false;
  let dragStartScreen = null;
  let panning = false;
  let panStart = null;

  function setStatus(msg, err) {
    statusEl.textContent = msg || "";
    statusEl.style.color = err ? "#e57373" : "";
  }

  function api(path, opt) {
    return fetch(path, opt).then((r) => {
      if (!r.ok) throw new Error(r.statusText);
      const ct = r.headers.get("content-type") || "";
      if (ct.includes("application/json")) return r.json();
      return r.text();
    });
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function computeLayout() {
    const nw = imgNatural.w;
    const nh = imgNatural.h;
    const W = board.width;
    const H = board.height;
    const base = Math.min(W / nw, H / nh);
    const scale = base * userZoom;
    const dw = nw * scale;
    const dh = nh * scale;
    const ox = (W - dw) / 2 + panX;
    const oy = (H - dh) / 2 + panY;
    layout = { ox, oy, scale, dw, dh, nw, nh };
  }

  function screenToImage(sx, sy) {
    const { ox, oy, scale } = layout;
    return [(sx - ox) / scale, (sy - oy) / scale];
  }

  function imageToScreen(ix, iy) {
    const { ox, oy, scale } = layout;
    return [ox + ix * scale, oy + iy * scale];
  }

  function redraw() {
    const W = board.width;
    const H = board.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#111";
    ctx.fillRect(0, 0, W, H);
    if (!imgEl.complete || imgEl.naturalWidth === 0) return;
    computeLayout();
    const { ox, oy, dw, dh } = layout;
    ctx.drawImage(imgEl, ox, oy, dw, dh);

    ctx.lineWidth = 2;
    ctx.font = "13px Segoe UI,sans-serif";
    for (const r of regions) {
      const [x1, y1, x2, y2] = r.geometry.xyxy;
      const p1 = imageToScreen(x1, y1);
      const p2 = imageToScreen(x2, y2);
      ctx.strokeStyle = "#5c9ded";
      ctx.strokeRect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1]);
      ctx.fillStyle = "rgba(92,157,237,0.85)";
      ctx.fillText(r.evidence, p1[0] + 4, p1[1] + 16);
    }

    for (const m of measurements) {
      ctx.strokeStyle = "#81c784";
      ctx.fillStyle = "#81c784";
      const pts = m.points;
      if (pts.length < 2) continue;
      ctx.beginPath();
      const p0 = imageToScreen(pts[0][0], pts[0][1]);
      ctx.moveTo(p0[0], p0[1]);
      for (let i = 1; i < pts.length; i++) {
        const p = imageToScreen(pts[i][0], pts[i][1]);
        ctx.lineTo(p[0], p[1]);
      }
      ctx.stroke();
      for (const pt of pts) {
        const p = imageToScreen(pt[0], pt[1]);
        ctx.beginPath();
        ctx.arc(p[0], p[1], 4, 0, Math.PI * 2);
        ctx.fill();
      }
      const last = imageToScreen(pts[pts.length - 1][0], pts[pts.length - 1][1]);
      ctx.fillText(`${m.length_px}px`, last[0] + 6, last[1] - 6);
    }

    if (rectDraft) {
      const [x1, y1, x2, y2] = rectDraft;
      const p1 = imageToScreen(x1, y1);
      const p2 = imageToScreen(x2, y2);
      ctx.strokeStyle = "#ffb74d";
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(p1[0], p1[1], p2[0] - p1[0], p2[1] - p1[1]);
      ctx.setLineDash([]);
    }

    if (measureDraft.length) {
      ctx.strokeStyle = "#ffb74d";
      ctx.fillStyle = "#ffb74d";
      const pts = measureDraft;
      if (pts.length >= 2) {
        ctx.beginPath();
        const p0 = imageToScreen(pts[0][0], pts[0][1]);
        ctx.moveTo(p0[0], p0[1]);
        for (let i = 1; i < pts.length; i++) {
          const p = imageToScreen(pts[i][0], pts[i][1]);
          ctx.lineTo(p[0], p[1]);
        }
        ctx.stroke();
      }
      for (const pt of pts) {
        const p = imageToScreen(pt[0], pt[1]);
        ctx.beginPath();
        ctx.arc(p[0], p[1], 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  function polylineLengthPx(points) {
    let s = 0;
    for (let i = 1; i < points.length; i++) {
      const dx = points[i][0] - points[i - 1][0];
      const dy = points[i][1] - points[i - 1][1];
      s += Math.hypot(dx, dy);
    }
    return Math.round(s * 10) / 10;
  }

  function resizeCanvas() {
    const r = canvasWrap.getBoundingClientRect();
    board.width = Math.floor(r.width);
    board.height = Math.floor(r.height);
    redraw();
  }

  function syncLists() {
    const rl = $("regionList");
    rl.innerHTML = "";
    regions.forEach((r) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `<span>${r.evidence} · ${r.geometry.xyxy.join(",")}</span>`;
      const del = document.createElement("button");
      del.type = "button";
      del.textContent = "删";
      const rid = r.id;
      del.onclick = () => {
        regions = regions.filter((x) => x.id !== rid);
        syncLists();
        redraw();
      };
      row.appendChild(del);
      rl.appendChild(row);
    });

    const ml = $("measureList");
    ml.innerHTML = "";
    measurements.forEach((m) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.innerHTML = `<span>${m.length_px}px · ${m.points.length}点</span>`;
      const del = document.createElement("button");
      del.type = "button";
      del.textContent = "删";
      const mid = m.id;
      del.onclick = () => {
        measurements = measurements.filter((x) => x.id !== mid);
        syncLists();
        redraw();
      };
      row.appendChild(del);
      ml.appendChild(row);
    });
  }

  function genId(prefix) {
    return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
  }

  function normalizeRect(x1, y1, x2, y2) {
    const nx1 = Math.round(Math.min(x1, x2));
    const ny1 = Math.round(Math.min(y1, y2));
    const nx2 = Math.round(Math.max(x1, x2));
    const ny2 = Math.round(Math.max(y1, y2));
    return [nx1, ny1, nx2, ny2];
  }

  function applyAnnotation(data) {
    regions = [];
    measurements = [];
    notes = "";
    annotator = "";
    imageLabel = "未碎裂";
    if (!data) {
      $("notes").value = "";
      $("annotator").value = "";
      syncLabelButtons();
      syncLists();
      return;
    }
    imageLabel = data.image_label || "未碎裂";
    regions = Array.isArray(data.regions) ? data.regions.slice() : [];
    measurements = Array.isArray(data.measurements) ? data.measurements.slice() : [];
    notes = data.notes || "";
    annotator = data.annotator || "";
    $("notes").value = notes;
    $("annotator").value = annotator;
    syncLabelButtons();
    syncLists();
  }

  function syncLabelButtons() {
    document.querySelectorAll(".label-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.label === imageLabel);
    });
  }

  function loadCurrentAnnotation() {
    const path = images[idx];
    if (!path) return Promise.resolve();
    return api(`/api/annotation?path=${encodeURIComponent(path)}`).then((data) => {
      applyAnnotation(data);
      redraw();
    });
  }

  function loadImage() {
    const path = images[idx];
    setStatus("");
    if (!path) {
      imgEl = new Image();
      redraw();
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const im = new Image();
      im.onload = () => {
        imgEl = im;
        imgNatural = { w: im.naturalWidth, h: im.naturalHeight };
        userZoom = 1;
        panX = 0;
        panY = 0;
        redraw();
        resolve();
      };
      im.onerror = () => reject(new Error("图片加载失败"));
      im.src = `/api/image?path=${encodeURIComponent(path)}`;
    })
      .then(() => loadCurrentAnnotation())
      .catch((e) => {
        setStatus(e.message || String(e), true);
      });
  }

  function updateNav() {
    $("navInfo").textContent = images.length
      ? `${idx + 1} / ${images.length} · ${images[idx] || ""}`
      : "无图片";
  }

  function loadImages() {
    return api(`/api/images?hole=${encodeURIComponent(hole)}`).then((data) => {
      images = data.images || [];
      idx = clamp(idx, 0, Math.max(0, images.length - 1));
      updateNav();
      return loadImage();
    });
  }

  function wireModes() {
    document.querySelectorAll(".mode").forEach((btn) => {
      btn.addEventListener("click", () => {
        mode = btn.dataset.mode;
        document.querySelectorAll(".mode").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        rectDraft = null;
        measureDraft = [];
        $("btnFinishMeasure").disabled = mode !== "measure";
        board.style.cursor = mode === "nav" ? "grab" : "crosshair";
        redraw();
      });
    });
  }

  function wireZoomPan() {
    board.addEventListener(
      "wheel",
      (ev) => {
        ev.preventDefault();
        const rect = board.getBoundingClientRect();
        const sx = ev.clientX - rect.left;
        const sy = ev.clientY - rect.top;
        computeLayout();
        const before = screenToImage(sx, sy);
        const factor = ev.deltaY > 0 ? 0.9 : 1.1;
        userZoom = clamp(userZoom * factor, 0.2, 8);
        computeLayout();
        const after = screenToImage(sx, sy);
        const sc = layout.scale;
        panX += (before[0] - after[0]) * sc;
        panY += (before[1] - after[1]) * sc;
        redraw();
      },
      { passive: false }
    );

    board.addEventListener("mousedown", (ev) => {
      const rect = board.getBoundingClientRect();
      const sx = ev.clientX - rect.left;
      const sy = ev.clientY - rect.top;
      if (mode === "nav" || ev.button === 1) {
        panning = true;
        panStart = { sx, sy, px: panX, py: panY };
        board.style.cursor = "grabbing";
        return;
      }
      if (mode === "rect") {
        dragging = true;
        const ij = screenToImage(sx, sy);
        rectDraft = [ij[0], ij[1], ij[0], ij[1]];
        dragStartScreen = [sx, sy];
      }
    });

    window.addEventListener("mouseup", () => {
      if (panning) {
        panning = false;
        board.style.cursor = mode === "nav" ? "grab" : "crosshair";
      }
      if (dragging && mode === "rect" && rectDraft) {
        const [x1, y1, x2, y2] = rectDraft;
        if (Math.abs(x2 - x1) > 4 && Math.abs(y2 - y1) > 4) {
          const xyxy = normalizeRect(x1, y1, x2, y2);
          regions.push({
            id: genId("r"),
            evidence: evidenceKey,
            geometry: { type: "rect", xyxy },
          });
          syncLists();
        }
        rectDraft = null;
        dragging = false;
        redraw();
      }
      dragging = false;
    });

    board.addEventListener("mousemove", (ev) => {
      const rect = board.getBoundingClientRect();
      const sx = ev.clientX - rect.left;
      const sy = ev.clientY - rect.top;
      if (panning && panStart) {
        panX = panStart.px + (sx - panStart.sx);
        panY = panStart.py + (sy - panStart.sy);
        redraw();
        return;
      }
      if (dragging && mode === "rect" && rectDraft) {
        const ij = screenToImage(sx, sy);
        rectDraft[2] = ij[0];
        rectDraft[3] = ij[1];
        redraw();
      }
    });

    board.addEventListener("click", (ev) => {
      if (mode !== "measure") return;
      const rect = board.getBoundingClientRect();
      const sx = ev.clientX - rect.left;
      const sy = ev.clientY - rect.top;
      const ij = screenToImage(sx, sy);
      ij[0] = clamp(ij[0], 0, imgNatural.w);
      ij[1] = clamp(ij[1], 0, imgNatural.h);
      measureDraft.push([Math.round(ij[0] * 10) / 10, Math.round(ij[1] * 10) / 10]);
      $("btnFinishMeasure").disabled = measureDraft.length < 2;
      redraw();
    });
  }

  function collectPayload() {
    const image_path = images[idx];
    return {
      schema_version: "1.0",
      image_path,
      drill_hole: hole,
      image_label: imageLabel,
      regions,
      measurements,
      notes: $("notes").value.trim(),
      annotator: $("annotator").value.trim(),
    };
  }

  function save() {
    const path = images[idx];
    if (!path) {
      setStatus("当前无图片", true);
      return;
    }
    const body = collectPayload();
    api("/api/annotation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(() => setStatus("已保存"))
      .catch((e) => setStatus(String(e), true));
  }

  async function boot() {
    config = await api("/api/config");
    const hs = $("holeSelect");
    hs.innerHTML = "";
    for (const h of config.holes) {
      const o = document.createElement("option");
      o.value = h;
      o.textContent = h;
      hs.appendChild(o);
    }
    hs.value = hole;

    const evSel = $("evidenceSelect");
    evSel.innerHTML = "";
    for (const e of config.evidence) {
      const o = document.createElement("option");
      o.value = e.key;
      o.textContent = `${e.label} (${e.key})`;
      evSel.appendChild(o);
    }
    evidenceKey = config.evidence[0].key;
    evSel.value = evidenceKey;
    evSel.addEventListener("change", () => {
      evidenceKey = evSel.value;
    });

    const lb = $("labelButtons");
    lb.innerHTML = "";
    for (const lab of config.labels) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "label-btn";
      b.dataset.label = lab;
      b.textContent = lab;
      b.onclick = () => {
        imageLabel = lab;
        syncLabelButtons();
      };
      lb.appendChild(b);
    }
    syncLabelButtons();

    hs.addEventListener("change", () => {
      hole = hs.value;
      idx = 0;
      loadImages().catch((e) => setStatus(String(e), true));
    });

    $("btnPrev").onclick = () => {
      if (idx <= 0) return;
      idx -= 1;
      updateNav();
      loadImage().catch(() => {});
    };
    $("btnNext").onclick = () => {
      if (idx >= images.length - 1) return;
      idx += 1;
      updateNav();
      loadImage().catch(() => {});
    };
    $("btnSave").onclick = save;

    $("btnFinishMeasure").onclick = () => {
      if (measureDraft.length < 2) return;
      const len = polylineLengthPx(measureDraft);
      measurements.push({
        id: genId("m"),
        points: measureDraft.map((p) => [p[0], p[1]]),
        length_px: len,
      });
      measureDraft = [];
      $("btnFinishMeasure").disabled = true;
      syncLists();
      redraw();
    };

    $("btnClearDraft").onclick = () => {
      rectDraft = null;
      measureDraft = [];
      $("btnFinishMeasure").disabled = mode !== "measure";
      redraw();
    };

    wireModes();
    wireZoomPan();

    new ResizeObserver(() => resizeCanvas()).observe(canvasWrap);
    resizeCanvas();

    window.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowLeft") $("btnPrev").click();
      if (ev.key === "ArrowRight") $("btnNext").click();
      if (ev.key === "s" && (ev.ctrlKey || ev.metaKey)) {
        ev.preventDefault();
        save();
      }
    });

    await loadImages();
  }

  boot().catch((e) => setStatus(String(e), true));
})();
