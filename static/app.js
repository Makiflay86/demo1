/* ═══════════════════════════════════════════════════════════════════
   Hotel Lumière — Frontend Logic
═══════════════════════════════════════════════════════════════════ */

const API = '';
let currentFilter = '';
let pendingDeleteId = null;

// ── Clock ─────────────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleDateString('es-ES', { weekday:'long', day:'2-digit', month:'long', year:'numeric' }) +
    '  ·  ' +
    now.toLocaleTimeString('es-ES');
}
updateClock();
setInterval(updateClock, 1000);

// ── API helpers ───────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ── Stats ─────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const s = await apiFetch('/api/stats');
    animateCount('stat-total',        s.total);
    animateCount('stat-disponible',   s.disponible);
    animateCount('stat-ocupada',      s.ocupada);
    animateCount('stat-mantenimiento',s.mantenimiento);
    document.getElementById('stat-ingresos').textContent =
      '€' + s.ingresos_estimados.toLocaleString('es-ES', { minimumFractionDigits:0, maximumFractionDigits:0 });
  } catch (_) {}
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  const start = parseInt(el.textContent) || 0;
  const diff = target - start;
  const dur = 500;
  const begin = performance.now();
  function step(now) {
    const t = Math.min((now - begin) / dur, 1);
    el.textContent = Math.round(start + diff * easeOut(t));
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

// ── Rooms ─────────────────────────────────────────────────────────
async function loadRooms() {
  const url = currentFilter ? `/api/rooms?status=${currentFilter}` : '/api/rooms';
  try {
    const rooms = await apiFetch(url);
    renderRooms(rooms);
  } catch (e) {
    showToast('Error cargando habitaciones: ' + e.message, 'error');
  }
}

function renderRooms(rooms) {
  const grid = document.getElementById('rooms-grid');
  const empty = document.getElementById('empty-state');
  grid.innerHTML = '';

  if (rooms.length === 0) {
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');

  rooms.forEach((r, i) => {
    const card = document.createElement('div');
    card.className = 'room-card';
    card.dataset.status = r.status;
    card.style.animationDelay = `${i * 50}ms`;

    const typeBadge = { suite: 'badge-suite', doble: 'badge-doble', individual: 'badge-individual' }[r.type];
    const typeLabel = { suite: 'Suite', doble: 'Doble', individual: 'Individual' }[r.type];
    const statusPill = `pill-${r.status}`;
    const statusLabel = { disponible: 'Disponible', ocupada: 'Ocupada', mantenimiento: 'Mantenimiento' }[r.status];

    // Action buttons based on current status
    let actions = '';
    if (r.status !== 'ocupada') {
      actions += `<button class="action-btn reserve" data-id="${r.id}" data-action="ocupada">Reservar</button>`;
    }
    if (r.status !== 'disponible') {
      actions += `<button class="action-btn release" data-id="${r.id}" data-action="disponible">Liberar</button>`;
    }
    if (r.status !== 'mantenimiento') {
      actions += `<button class="action-btn maintain" data-id="${r.id}" data-action="mantenimiento">Mantenimiento</button>`;
    }
    actions += `<button class="action-btn del" data-id="${r.id}" data-num="${r.number}" data-action="delete">✕</button>`;

    card.innerHTML = `
      <div class="card-header">
        <div class="card-number">
          ${r.number}
          <small>Habitación</small>
        </div>
        <span class="card-type-badge ${typeBadge}">${typeLabel}</span>
      </div>
      <div class="card-body">
        <div class="card-price">€${r.price.toLocaleString('es-ES')}<span> / noche</span></div>
        <span class="status-pill ${statusPill}">${statusLabel}</span>
      </div>
      <div class="card-footer">${actions}</div>
    `;
    grid.appendChild(card);
  });

  // Delegate events
  grid.querySelectorAll('.action-btn').forEach(btn => {
    btn.addEventListener('click', handleCardAction);
  });
}

async function handleCardAction(e) {
  const { id, action, num } = e.currentTarget.dataset;
  if (action === 'delete') {
    pendingDeleteId = parseInt(id);
    document.getElementById('delete-room-num').textContent = `#${num}`;
    openModal('modal-delete');
    return;
  }
  try {
    await apiFetch(`/api/rooms/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: action }),
    });
    showToast(
      action === 'ocupada'      ? `Habitación reservada ✓` :
      action === 'disponible'   ? `Habitación liberada ✓` :
                                  `En mantenimiento ✓`,
      'success'
    );
    await refresh();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── Create modal ──────────────────────────────────────────────────
document.getElementById('btn-add-room').addEventListener('click', () => openModal('modal-create'));
document.getElementById('close-create').addEventListener('click', () => closeModal('modal-create'));

document.getElementById('form-create').addEventListener('submit', async (e) => {
  e.preventDefault();
  const errEl = document.getElementById('create-error');
  errEl.classList.add('hidden');

  const data = {
    number: document.getElementById('f-number').value.trim(),
    type:   document.getElementById('f-type').value,
    price:  parseFloat(document.getElementById('f-price').value),
    status: document.getElementById('f-status').value,
  };

  try {
    await apiFetch('/api/rooms', { method: 'POST', body: JSON.stringify(data) });
    closeModal('modal-create');
    e.target.reset();
    showToast(`Habitación ${data.number} creada ✓`, 'success');
    await refresh();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  }
});

// ── Delete modal ──────────────────────────────────────────────────
document.getElementById('cancel-delete').addEventListener('click', () => {
  pendingDeleteId = null;
  closeModal('modal-delete');
});
document.getElementById('confirm-delete').addEventListener('click', async () => {
  if (!pendingDeleteId) return;
  try {
    await apiFetch(`/api/rooms/${pendingDeleteId}`, { method: 'DELETE' });
    showToast('Habitación eliminada', 'success');
    closeModal('modal-delete');
    pendingDeleteId = null;
    await refresh();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ── Filters ───────────────────────────────────────────────────────
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.status;
    loadRooms();
  });
});

// ── Modal helpers ─────────────────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}
function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
  document.body.style.overflow = '';
}
// Close on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.classList.add('hidden');
      document.body.style.overflow = '';
      pendingDeleteId = null;
    }
  });
});

// ── Toast ─────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  t.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3000);
}

// ── Init ──────────────────────────────────────────────────────────
async function refresh() {
  await Promise.all([loadStats(), loadRooms()]);
}

refresh();
// Auto-refresh every 30s
setInterval(refresh, 30000);
