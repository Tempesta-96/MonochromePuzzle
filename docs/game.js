'use strict';
const $ = id => document.getElementById(id);
let saved = {};
try { saved = JSON.parse(localStorage.getItem('monochrome-progress') || '{}') || {}; } catch {}
let current = Number.isInteger(saved.level) ? Math.max(0, Math.min(100, saved.level)) : 1;
const completed = new Set(Array.isArray(saved.completed) ? saved.completed.filter(n => Number.isInteger(n) && n >= 0 && n <= 100) : []);
let data, positions, selected = null, hint = null, showSolution = false, drag = null;
let scrollFrame = null;
let wasSolved = false, celebrationTimer = null;
function clearCelebration() {
  clearTimeout(celebrationTimer);
  document.getElementById('celebration')?.remove();
}
function celebrate() {
  clearCelebration();
  const overlay = document.createElement('div');
  overlay.id = 'celebration'; overlay.setAttribute('aria-hidden', 'true');
  const card = document.createElement('div'); card.className = 'success-card';
  const badge = document.createElement('span'); badge.className = 'success-badge'; badge.textContent = '✓';
  const message = document.createElement('div');
  const title = document.createElement('strong'); title.textContent = 'Pattern matched!';
  const detail = document.createElement('span'); detail.textContent = `Level ${current} complete. Nicely done.`;
  message.append(title, detail); card.append(badge, message); overlay.append(card);
  const colors = ['#24231f', '#719b87', '#cf973e', '#fffdf8'];
  for (let i = 0; i < 28; i++) {
    const confetti = document.createElement('span'); confetti.className = 'confetti';
    confetti.style.setProperty('--x', `${4 + Math.random() * 92}vw`);
    confetti.style.setProperty('--drift', `${(Math.random() - .5) * 160}px`);
    confetti.style.setProperty('--spin', `${(Math.random() - .5) * 900}deg`);
    confetti.style.setProperty('--delay', `${Math.random() * .3}s`);
    confetti.style.background = colors[i % colors.length]; overlay.append(confetti);
  }
  document.body.append(overlay);
  celebrationTimer = setTimeout(clearCelebration, 3400);
}
function persist() {
  try { localStorage.setItem('monochrome-progress', JSON.stringify({level: current, completed: [...completed]})); } catch {}
}
function computeGrid(level, placements) {
  const grid = Array.from({length: level.grid_size}, () => Array(level.grid_size).fill(0));
  level.pieces.forEach((cells, i) => {
    const p = placements[i];
    if (p) cells.forEach(([r, c]) => { grid[r + p[1]][c + p[0]] ^= 1; });
  });
  return grid;
}
function bounds(cells) { return [Math.max(...cells.map(c => c[1])) + 1, Math.max(...cells.map(c => c[0])) + 1]; }
function matches(a, b) { return a.every((row, r) => row.every((v, c) => v === b[r][c])); }
function fits(i, p) {
  if (!p) return false;
  const [w, h] = bounds(data.pieces[i]);
  return p[0] >= 0 && p[1] >= 0 && p[0] + w <= data.grid_size && p[1] + h <= data.grid_size;
}
function drawGrid(el, grid, interactive = false) {
  el.replaceChildren(); el.style.setProperty('--size', grid.length);
  grid.forEach((row, r) => row.forEach((v, c) => {
    const cell = document.createElement(interactive ? 'button' : 'div');
    cell.className = 'cell' + (v ? ' black' : '');
    if (interactive) {
      cell.setAttribute('aria-label', `Row ${r + 1}, column ${c + 1}: ${v ? 'black' : 'white'}`);
      // Retain a keyboard alternative without requiring pointer users to select pieces.
      cell.onclick = e => { if (e.detail === 0 && selected !== null) place(c, r); };
    }
    el.append(cell);
  }));
}
function point(x, y) {
  const rect = $('board').getBoundingClientRect();
  if (x < rect.left || y < rect.top || x >= rect.right || y >= rect.bottom) return null;
  return [Math.floor((x - rect.left) / rect.width * data.grid_size), Math.floor((y - rect.top) / rect.height * data.grid_size)];
}
function drawBoard(placements = positions) {
  drawGrid($('board'), computeGrid(data, placements), true);
  const overlays = showSolution ? data.pieces.map((_, i) => i) : hint === null ? [] : [hint];
  overlays.forEach(i => {
    const [x, y] = data.solution[i];
    data.pieces[i].forEach(([r, c]) => $('board').children[(y + r) * data.grid_size + x + c].classList.add('hint'));
    $('board').children[y * data.grid_size + x].classList.add('origin');
  });
}
function makeShape(cells) {
  const shape = document.createElement('span'); shape.className = 'shape';
  const [w, h] = bounds(cells); shape.style.gridTemplateColumns = `repeat(${w}, var(--pixel, 16px))`;
  for (let r = 0; r < h; r++) for (let c = 0; c < w; c++) {
    const pixel = document.createElement('span');
    pixel.className = 'pixel' + (cells.some(([dr, dc]) => dr === r && dc === c) ? ' filled' : '');
    shape.append(pixel);
  }
  return shape;
}
function render() {
  drawGrid($('target'), data.target); drawBoard(); $('pieces').replaceChildren();
  data.pieces.forEach((cells, i) => {
    const btn = document.createElement('button');
    btn.className = 'piece' + (selected === i ? ' selected' : '') + (positions[i] ? ' placed' : '');
    btn.setAttribute('aria-pressed', String(selected === i));
    btn.setAttribute('aria-label', `Piece ${i + 1}. ${positions[i] ? 'On canvas. Drag to move or return.' : 'Drag onto canvas.'}`);
    const shape = makeShape(cells), label = document.createElement('span');
    label.textContent = `${i + 1} · ${positions[i] ? 'On canvas' : 'Drag me'}`; btn.append(shape, label);
    btn.onclick = e => {
      if (e.detail !== 0) return;
      if (selected === i && positions[i]) { positions[i] = null; selected = null; }
      else selected = selected === i ? null : i;
      render();
    };
    btn.onpointerdown = e => {
      if (e.button !== 0 || drag) return;
      const rect = shape.getBoundingClientRect();
      const [w, h] = bounds(cells);
      const step = rect.width / w;
      let c = Math.max(0, Math.min(w - 1, Math.floor((e.clientX - rect.left) / step)));
      let r = Math.max(0, Math.min(h - 1, Math.floor((e.clientY - rect.top) / (rect.height / h))));
      if (!cells.some(([dr, dc]) => dr === r && dc === c)) [r, c] = cells[0];
      beginDrag(e, i, c, r, btn);
    };
    $('pieces').append(btn);
  });
  const solved = positions.every(Boolean) && matches(computeGrid(data, positions), data.target);
  if (solved) { completed.add(current); persist(); }
  if (solved && !wasSolved) celebrate();
  if (!solved && wasSolved) clearCelebration();
  wasSolved = solved;
  $('status').textContent = solved ? 'Pattern matched. Beautiful! Choose the next level when you are ready.'
    : hint !== null ? `Hint: drag piece ${hint + 1} so its top-left corner matches the dashed cell.`
    : selected !== null ? `Piece ${selected + 1} selected. Use the keyboard to choose a canvas cell.` : 'Drag a piece onto the canvas to begin.';
  $('progress').textContent = `${completed.size} / 101 levels solved`;
  $('count').textContent = `${positions.filter(Boolean).length} / ${data.pieces.length} placed`;
  $('dimensions').textContent = `${data.grid_size} × ${data.grid_size}`;
  $('level').value = current; $('prev').disabled = current === 0; $('next').disabled = current === 100;
  $('solution').setAttribute('aria-pressed', String(showSolution));
}
function beginDrag(e, i, grabCol, grabRow, source) {
  e.preventDefault();
  source.setPointerCapture(e.pointerId);
  const ghost = document.createElement('div'); ghost.className = 'drag-ghost'; ghost.setAttribute('aria-hidden', 'true');
  ghost.append(makeShape(data.pieces[i])); document.body.append(ghost);
  drag = {i, grabCol, grabRow, pointerId: e.pointerId, source, ghost, x: e.clientX, y: e.clientY, startX: e.clientX, startY: e.clientY, moved: false, candidate: null};
  source.classList.add('drag-source'); document.body.classList.add('dragging'); selected = null;
  updateDrag(e.clientX, e.clientY);
  scrollFrame = requestAnimationFrame(autoScroll);
}
function updateDrag(x, y) {
  if (!drag) return;
  drag.x = x; drag.y = y;
  if (Math.hypot(x - drag.startX, y - drag.startY) > 5) drag.moved = true;
  const rect = $('board').getBoundingClientRect(), cell = rect.width / data.grid_size;
  const p = point(x, y);
  drag.candidate = p ? [p[0] - drag.grabCol, p[1] - drag.grabRow] : null;
  const valid = fits(drag.i, drag.candidate);
  const preview = positions.map((pos, i) => i === drag.i ? (valid ? drag.candidate : null) : pos);
  drawBoard(preview);
  if (valid) data.pieces[drag.i].forEach(([r, c]) => $('board').children[(drag.candidate[1] + r) * data.grid_size + drag.candidate[0] + c].classList.add('drop-preview'));
  drag.ghost.style.setProperty('--pixel', `${cell - 1}px`);
  drag.ghost.style.left = `${valid ? rect.left + drag.candidate[0] * cell : x - (drag.grabCol + .5) * cell}px`;
  drag.ghost.style.top = `${valid ? rect.top + drag.candidate[1] * cell : y - (drag.grabRow + .5) * cell}px`;
  drag.ghost.classList.toggle('snapped', valid);
  drag.ghost.classList.toggle('invalid', Boolean(p) && !valid);
  $('status').textContent = valid ? 'Release to place. Overlapping black cells cancel out.' : p ? 'Move inward: the whole piece must fit.' : 'Drag onto the canvas, or drop outside to return the piece.';
}
function autoScroll() {
  if (!drag) return;
  const edge = 90, y = drag.y;
  const speed = y < edge ? -Math.ceil((edge - y) / 6) : y > innerHeight - edge ? Math.ceil((y - innerHeight + edge) / 6) : 0;
  if (speed) { window.scrollBy(0, speed); updateDrag(drag.x, drag.y); }
  scrollFrame = requestAnimationFrame(autoScroll);
}
function finishDrag(cancelled = false) {
  if (!drag) return;
  const d = drag; drag = null; cancelAnimationFrame(scrollFrame);
  d.ghost.remove(); d.source.classList.remove('drag-source'); document.body.classList.remove('dragging');
  if (d.source.hasPointerCapture(d.pointerId)) d.source.releasePointerCapture(d.pointerId);
  let invalid = false;
  if (!cancelled && d.moved) {
    if (fits(d.i, d.candidate)) { positions[d.i] = d.candidate; hint = null; }
    else if (!d.candidate) positions[d.i] = null;
    else invalid = true; // Restore the previous placement after an out-of-bounds drop.
  }
  render();
  if (invalid) $('status').textContent = 'The whole piece must fit. Try dropping it farther inside the canvas.';
}
$('board').onpointerdown = e => {
  if (e.button !== 0 || drag) return;
  const p = point(e.clientX, e.clientY); if (!p) return;
  for (let i = positions.length - 1; i >= 0; i--) {
    const pos = positions[i]; if (!pos) continue;
    const c = p[0] - pos[0], r = p[1] - pos[1];
    if (data.pieces[i].some(([dr, dc]) => dr === r && dc === c)) { beginDrag(e, i, c, r, $('board')); return; }
  }
};
window.addEventListener('pointermove', e => { if (drag && e.pointerId === drag.pointerId) { e.preventDefault(); updateDrag(e.clientX, e.clientY); } }, {passive: false});
window.addEventListener('pointerup', e => { if (drag && e.pointerId === drag.pointerId) { updateDrag(e.clientX, e.clientY); finishDrag(); } });
window.addEventListener('pointercancel', e => { if (drag && e.pointerId === drag.pointerId) finishDrag(true); });
window.addEventListener('blur', () => finishDrag(true));
function place(x, y) {
  if (selected === null) return;
  if (!fits(selected, [x, y])) { $('status').textContent = 'The whole piece must fit inside the canvas.'; return; }
  positions[selected] = [x, y]; selected = null; hint = null; render();
}
function load(level) {
  finishDrag(true); clearCelebration(); wasSolved = false; current = Math.max(0, Math.min(100, level)); data = LEVELS[current];
  positions = data.pieces.map(() => null); selected = null; hint = null; showSolution = false; persist(); render();
}
for (let i = 0; i <= 100; i++) { const o = document.createElement('option'); o.value = i; o.textContent = i; $('level').append(o); }
$('level').onchange = e => load(Number(e.target.value)); $('prev').onclick = () => load(current - 1); $('next').onclick = () => load(current + 1); $('reset').onclick = () => load(current);
$('solution').onclick = () => { showSolution = !showSolution; render(); };
$('hint').onclick = () => { hint = data.solution.findIndex((p, i) => !positions[i] || p.some((v, j) => v !== positions[i][j])); if (hint === -1) hint = null; render(); };
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') { finishDrag(true); selected = null; hint = null; showSolution = false; render(); return; }
  if (['SELECT', 'BUTTON', 'INPUT'].includes(e.target.tagName)) return;
  const key = e.key.toLowerCase();
  if (key === 'arrowleft') { e.preventDefault(); load(current - 1); }
  if (key === 'arrowright') { e.preventDefault(); load(current + 1); }
  if (key === 'r') load(current); if (key === 's') $('solution').click();
});
load(current);
