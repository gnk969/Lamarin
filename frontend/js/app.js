const $ = (id) => document.getElementById(id);
const form = $("form");
const textarea = $("teks");
const resultBox = $("result");
const submitBtn = $("submit");
const tabs = { teks: $("tab-teks"), gambar: $("tab-gambar") };
const panels = { teks: $("panel-teks"), gambar: $("panel-gambar") };

const TESSERACT_URL = "https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js";
const MAX_BYTES = 15 * 1024 * 1024; // batas file asli; gambar besar diperkecil sebelum dikirim
const SEND_BYTES = 1.5 * 1024 * 1024; // di atas ini gambar diperkecil (batas body hosting gratis sekitar 4,5 MB)
const MAX_SIDE = 2000;

let mode = "teks";
let image = null; // { base64, mime }
let aiOn = false;

const esc = (v) => String(v ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#39;");

const sign = (heavy) => `<svg class="sign${heavy ? " sign--merah" : ""}" viewBox="0 0 22 20" aria-hidden="true"><path d="M11 1.5 20.5 18.5H1.5Z"/><path d="M11 7.5v5M11 15.3v.2"/></svg>`;

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(path, options);
  } catch {
    throw new Error("Tidak bisa terhubung ke server. Periksa koneksi lalu coba lagi.");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    let d = data?.detail;
    if (Array.isArray(d)) d = d.map((x) => x.msg).join(" ");
    throw new Error(d || `Server mengembalikan galat ${res.status}.`);
  }
  return data;
}

// ---------- tema ----------
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  $("theme-btn").textContent = t === "dark" ? "Tema terang" : "Tema gelap";
}
$("theme-btn").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  try { localStorage.setItem("rambu.tema", next); } catch { /* abaikan */ }
  applyTheme(next);
});
applyTheme(document.documentElement.dataset.theme || "light");

// ---------- tab ----------
function selectTab(name, focus = false) {
  mode = name;
  for (const key of Object.keys(tabs)) {
    const on = key === name;
    tabs[key].setAttribute("aria-selected", String(on));
    tabs[key].tabIndex = on ? 0 : -1;
    panels[key].hidden = !on;
  }
  if (focus) tabs[name].focus();
}
tabs.teks.addEventListener("click", () => selectTab("teks"));
tabs.gambar.addEventListener("click", () => selectTab("gambar"));
document.querySelector('[role="tablist"]').addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
    e.preventDefault();
    selectTab(mode === "teks" ? "gambar" : "teks", true);
  }
});

// ---------- gambar ----------
const drop = $("drop");
const fileInput = $("file");

function setImage(file) {
  if (!file) return;
  if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) {
    showError("Format gambar harus PNG, JPG, atau WEBP.");
    return;
  }
  if (file.size > MAX_BYTES) {
    showError("Gambar terlalu besar. Maksimal 15 MB.");
    return;
  }
  const reader = new FileReader();
  reader.onload = async () => {
    let url = String(reader.result);
    let mime = file.type;
    try {
      ({ url, mime } = await shrink(url, mime, file.size));
    } catch {
      /* bila gagal diperkecil, kirim apa adanya */
    }
    image = { base64: url.split(",")[1], mime, dataUrl: url };
    if (resultBox.querySelector(".error")) {
      resultBox.hidden = true; // hapus pesan galat lama setelah gambar valid dipilih
      resultBox.innerHTML = "";
    }
    $("preview").src = url;
    $("preview").hidden = false;
    $("clear-img").hidden = false;
    $("drop-empty").hidden = true;
  };
  reader.readAsDataURL(file);
}

// Perkecil tangkapan layar besar (sisi terpanjang maks 2000 px, JPEG) agar upload cepat dan muat di batas server.
function shrink(url, mime, size) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height));
      if (scale === 1 && size <= SEND_BYTES) return resolve({ url, mime });
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      const ctx = c.getContext("2d");
      ctx.fillStyle = "#fff";
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.drawImage(img, 0, 0, c.width, c.height);
      resolve({ url: c.toDataURL("image/jpeg", 0.88), mime: "image/jpeg" });
    };
    img.onerror = reject;
    img.src = url;
  });
}

function clearImage() {
  image = null;
  fileInput.value = "";
  $("preview").hidden = true;
  $("clear-img").hidden = true;
  $("drop-empty").hidden = false;
  $("pick-btn").focus();
}

$("pick-btn").addEventListener("click", () => fileInput.click());
$("clear-img").addEventListener("click", clearImage);
fileInput.addEventListener("change", () => setImage(fileInput.files[0]));
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.dataset.over = "true"; });
drop.addEventListener("dragleave", () => { drop.dataset.over = "false"; });
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.dataset.over = "false";
  selectTab("gambar");
  setImage(e.dataTransfer.files[0]);
});
document.addEventListener("paste", (e) => {
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) {
    selectTab("gambar");
    setImage(item.getAsFile());
  }
});

// Pembaca teks di peramban (gratis) dipakai bila AI belum aktif.
let tesseractLoading = null;
function loadTesseract() {
  if (window.Tesseract) return Promise.resolve(window.Tesseract);
  tesseractLoading ??= new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = TESSERACT_URL;
    s.onload = () => resolve(window.Tesseract);
    s.onerror = () => reject(new Error("Pembaca teks gambar gagal dimuat. Tempel teks lowongannya saja."));
    document.head.appendChild(s);
  });
  return tesseractLoading;
}

async function ocrInBrowser(dataUrl, onProgress) {
  const T = await loadTesseract();
  const { data } = await T.recognize(dataUrl, "ind", {
    logger: (m) => m.status === "recognizing text" && onProgress(Math.round(m.progress * 100)),
  });
  return data.text;
}

// ---------- hasil ----------
function showLoading(text) {
  resultBox.hidden = false;
  resultBox.innerHTML = `<div class="loading"><i></i><i></i><i></i><span>${esc(text)}</span></div>`;
}

function showError(msg) {
  resultBox.hidden = false;
  resultBox.innerHTML = `<div class="error" role="alert">${esc(msg)}</div>`;
}

const LEVEL_TEXT = {
  tinggi: "Banyak tanda penipuan. Jangan lanjutkan sebelum memastikan ke saluran resmi.",
  waspada: "Ada tanda yang perlu dicek. Pastikan dulu ke saluran resmi perusahaan.",
  rendah: "Tanda penipuan yang umum tidak ditemukan. Tetap cek ke saluran resmi.",
};

const FACT_LABELS = {
  perusahaan: "Perusahaan", posisi: "Posisi", lokasi_kerja: "Lokasi kerja", gaji: "Gaji",
  biaya_disebut: "Biaya yang disebut", saluran_lamaran: "Cara melamar", kontak: "Kontak", tautan: "Tautan",
};

function renderResult(r) {
  const flags = r.rambu.length
    ? `<ul class="flags">${r.rambu.map((f) => `
        <li class="flag${f.bobot >= 30 ? " flag--berat" : ""}">
          ${sign(f.bobot >= 30)}
          <div>
            <h3>${esc(f.judul)} <span class="weight">+${f.bobot}</span></h3>
            <p>${esc(f.penjelasan)}</p>
            <blockquote class="quote">"${esc(f.bukti)}"</blockquote>
            ${f.alasan_ai ? `<p>Catatan AI: ${esc(f.alasan_ai)}</p>` : ""}
            <div class="src">${f.sumber.map((s) => `<span>${s === "ai" ? "AI" : "Aturan"}</span>`).join("")}</div>
          </div>
        </li>`).join("")}</ul>`
    : `<p class="none">Tidak ada rambu dari daftar periksa yang cocok dengan teks ini.</p>`;

  const facts = Object.entries(FACT_LABELS)
    .map(([k, label]) => {
      let v = r.fakta?.[k];
      if (Array.isArray(v)) v = v.join(", ");
      return v ? `<dt>${label}</dt><dd>${esc(v)}</dd>` : "";
    })
    .join("");

  const modeText = r.mode === "aturan+ai" ? "Diperiksa dengan daftar aturan dan AI (Gemini)." : "Diperiksa dengan daftar aturan saja.";
  resultBox.hidden = false;
  resultBox.innerHTML = `
    <div class="verdict">
      ${r.level === "rendah" ? '<span aria-hidden="true"></span>' : sign(r.level === "tinggi")}
      <div>
        <h2>${esc(r.label)}</h2>
        <p>${esc(LEVEL_TEXT[r.level])}</p>
      </div>
      <div class="score">${r.skor}<small>skor risiko dari 100</small></div>
    </div>
    <div class="meter" data-level="${r.level}" aria-hidden="true"><span></span><span></span><span></span></div>
    <div class="meter-labels" aria-hidden="true"><span>0</span><span>20 waspada</span><span>50 risiko tinggi</span></div>
    ${r.ringkasan_ai ? `<p class="summary">${esc(r.ringkasan_ai)}</p>` : ""}
    <p class="meta" style="color:var(--ink-soft);font-size:.85rem;margin-top:12px">${modeText}</p>
    ${r.peringatan.map((w) => `<p class="warn">${esc(w)}</p>`).join("")}

    <h2 class="section-title">Rambu yang ditemukan (${r.rambu.length})</h2>
    ${flags}

    ${facts ? `<h2 class="section-title">Yang terbaca dari lowongan</h2><dl class="facts">${facts}</dl>` : ""}

    <h2 class="section-title">Langkah aman</h2>
    <ol class="steps">${r.langkah.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
    <p class="note">Skor dihitung dari bobot tetap tiap rambu. AI hanya boleh menambah rambu bila mengutip bagian lowongan yang benar-benar ada.</p>`;
  resultBox.querySelector("h2")?.focus?.();
  resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---------- kirim ----------
async function submit() {
  let teks = textarea.value.trim();
  const body = {};
  if (mode === "gambar") {
    if (!image) {
      showError("Unggah gambar lowongan dulu, atau pindah ke tab Teks.");
      return;
    }
    if (aiOn) {
      body.gambar = image.base64;
      body.mime = image.mime;
    } else {
      showLoading("Membaca teks di gambar (di perangkatmu)");
      try {
        teks = (await ocrInBrowser(image.dataUrl, (p) => showLoading(`Membaca teks di gambar: ${p}%`))).trim();
      } catch (e) {
        showError(e.message);
        return;
      }
      if (teks.length < 15) {
        showError("Teks di gambar tidak terbaca. Coba gambar yang lebih jelas atau tempel teksnya.");
        return;
      }
      body.teks = teks;
    }
  } else {
    if (teks.length < 15) {
      showError("Tempel isi lowongan selengkapnya (minimal satu kalimat).");
      textarea.focus();
      return;
    }
    body.teks = teks;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Memeriksa";
  showLoading(aiOn ? "Memeriksa rambu dengan aturan dan AI" : "Memeriksa rambu");
  try {
    const r = await api("/api/periksa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    renderResult(r);
  } catch (e) {
    showError(e.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Periksa lowongan";
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  submit();
});

// ---------- status & contoh ----------
async function init() {
  try {
    const s = await api("/api/status");
    aiOn = s.ai_tersedia;
    $("ai-line").textContent = aiOn
      ? "AI aktif: membaca gambar dan konteks lowongan."
      : "Mode aturan. Gambar dibaca di perangkatmu.";
  } catch {
    $("ai-line").textContent = "Server tidak terhubung.";
  }
  try {
    const items = await api("/api/contoh");
    if (items.length) {
      const counter = { penipuan: 0, asli: 0 };
      $("example-list").innerHTML = items
        .map((x, i) => {
          counter[x.label] += 1;
          const name = x.label === "penipuan" ? "Kasus penipuan" : "Lowongan resmi";
          return `<li><button type="button" data-i="${i}" title="${esc(x.judul)}">${name} ${counter[x.label]}</button></li>`;
        })
        .join("");
      $("examples").hidden = false;
      $("example-list").addEventListener("click", (e) => {
        const b = e.target.closest("button[data-i]");
        if (!b) return;
        const x = items[Number(b.dataset.i)];
        selectTab("teks");
        textarea.value = x.teks;
        textarea.focus();
        $("ai-line").innerHTML = `Contoh dimuat. Sumber: <a href="${esc(x.sumber)}" target="_blank" rel="noopener">${esc(new URL(x.sumber).hostname)}</a>`;
      });
    }
  } catch {
    /* contoh opsional */
  }
}
init();
