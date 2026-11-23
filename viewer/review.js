// The review app: Look (tap a part, see its sizes drawn on it, leave a note), Measurements (one size at a time, right / wrong /
// not sure) and Templates. All feedback is shared (everyone sees everyone's) and saved by store.js; the Feedback drawer
// lists it with the general comments. The old tools live in workbench.html.
import * as S from './scene.js'
import * as store from './store.js'
import { inch, mmText, parse, MM } from './inches.js'

const $ = (id) => document.getElementById(id)
const phone = () => matchMedia('(max-width: 700px)').matches
const PARTS = new URL('../parts/', location.href)
const TEMPLATES = new URL('../templates/out/', location.href)
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const st = {
  tab: 'look', version: null, dims: [], questions: [], items: [], records: [], ready: false,
  sel: null, row: null, note: null, lookView: null, mIdx: 0, photo: null, cams: null, keys: [], pi: 0, wipe: 0.5, mode: 'solid',
  sheet: null,
}

// ------------------------------------------------------------------ boot
async function findModel() {                // the newest model that has a dimensions file
  let best = null
  for (let v = 24; v < 80; v++) {
    const r = await fetch(new URL(`model_v${v}_dimensions.json`, PARTS), { cache: 'no-cache' }).catch(() => null)
    if (!r || !r.ok) { if (best) break; continue }
    best = { v, data: await r.json() }
  }
  return best
}

async function boot() {
  S.init($('c3d'), $('stage'), { onFrame: overlay })
  wire()
  st.records = await store.all().catch(() => [])
  setInterval(() => { if (!document.hidden) refresh() }, 60000)
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh() })
  const m = await findModel()
  if (!m) { $('loading').textContent = 'Could not find the model. Check the connection and reload.'; $('loading').classList.add('err'); return }
  st.version = m.v; st.dims = m.data.dimensions; st.questions = m.data.questions || []
  st.items = [...st.dims.map((d) => ({ kind: 'dim', id: d.id, group: d.group, order: d.order, d })),
    ...st.questions.map((q, i) => ({ kind: 'q', id: q.id, group: q.group, order: 10.5 + i, q }))].sort((a, b) => a.group - b.group || a.order - b.order)
  try { await S.loadModel(new URL(`model_v${m.v}.glb`, PARTS).href) } catch (e) {
    $('loading').textContent = 'The chair did not load. Reload to try again.'; $('loading').classList.add('err'); return
  }
  $('loading').hidden = true; st.ready = true
  renderTemplates(); refresh(); route()
}

// ------------------------------------------------------------------ routing and screen IDs
function route() {
  const [tab, arg] = (location.hash.slice(1) || 'look').split('/')
  if (['feedback', 'notes', 'comments'].includes(tab)) { openDrawer(); return }
  go(['look', 'measure', 'templates'].includes(tab) ? tab : 'look', arg, true)
}
addEventListener('hashchange', route)

function go(tab, arg, fromHash) {
  if (st.tab === 'look' && tab !== 'look') { st.lookView = S.getView(); if (st.photo) exitPhoto() }
  const was = st.tab; st.tab = tab
  document.body.dataset.tab = tab
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('on', t.dataset.t === tab))
  if (tab === 'look') {
    $('lookStage').appendChild($('stage'))
    S.setMode(st.mode); S.select(st.sel?.name || null)
    if (was !== 'look' && st.lookView) S.setView(st.lookView, true)
  } else if (tab === 'measure') {
    $('measureStage').appendChild($('stage'))
    S.setMode('solid')
    const i = arg ? st.items.findIndex((x) => x.id === arg) : -1
    showItem(i >= 0 ? i : (was === 'measure' ? st.mIdx : firstOpen()), true)
  }
  if (!fromHash) history.replaceState(null, '', '#' + tab + (tab === 'measure' && st.items[st.mIdx] ? '/' + st.items[st.mIdx].id : ''))
  setScreen(); S.request()
}

function setScreen() {
  let id = 'er.' + st.tab
  if (st.tab === 'look') id += st.photo ? '.photo' : !$('cardNote').hidden ? '.note' : !$('cardPart').hidden ? '.part' : ''
  if (st.tab === 'measure' && !$('sheet').hidden) id += '.wrong'
  if (!$('drawer').hidden) id = 'er.feedback'
  if (!$('who').hidden) id = 'er.who'
  document.body.dataset.screen = id; $('sid').textContent = id
  document.body.classList.toggle('card-open', !$('cardPart').hidden || !$('cardNote').hidden)
}

// ------------------------------------------------------------------ records (everyone's)
const isAns = (r, id) => (r.type === 'answer' && r.dimId === id) || (r.type === 'question' && r.qid === id)
const answersTo = (id) => st.records.filter((r) => isAns(r, id))
function answerOf(id) { return st.records.find((r) => r.mine && isAns(r, id)) }   // your own answer
const kindOf = (a) => (a.type === 'question' ? (a.choice === 'unsure' ? 'q' : 'ok') : ({ right: 'ok', wrong: 'no', unsure: 'q' }[a.verdict] || ''))
function status(item) {               // what most people said: ok / no / q; a tie goes to "wrong", then "not sure"
  const n = { ok: 0, no: 0, q: 0 }; for (const a of answersTo(item.id)) n[kindOf(a)]++
  const best = Math.max(n.ok, n.no, n.q); if (!best) return ''
  return n.no === best ? 'no' : n.q === best ? 'q' : 'ok'
}
const notes = () => st.records.filter((r) => r.type === 'note')
const people = () => new Set(st.records.map((r) => r.who)).size
async function refresh() {
  st.records = await store.all().catch(() => st.records)
  const done = st.items.filter((x) => answersTo(x.id).length).length
  $('count').textContent = `${done} of ${st.items.length}`
  $('notesN').textContent = st.records.length
  renderList(); if (st.tab === 'measure') renderAsk()
  if (!$('drawer').hidden) renderDrawer()
  S.request()
}
// Save one piece of feedback under the reader's name (asked once). Returns the saved record, or null.
async function submit(rec, photos = []) {
  const who = await ensureName(); if (!who) return null
  try { return await store.save({ ...rec, who, model: `v${st.version}` }, photos) } catch (e) {
    if (e.status === 429) toast('Slow down a little. Wait a few minutes, then try again.')
    else if (e.status === 403) { store.state.postingEnabled = false; toast('Feedback is closed for now.'); renderDrawer() }
    else toast(e.message || 'That did not save. Try again in a moment.')
    return null
  }
}
function toast(msg) {
  const t = $('toast'); t.textContent = msg; t.hidden = false
  clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true }, 2600)
}

// ------------------------------------------------------------------ sizes and dimension lines
const twin = (n) => n.replace(/(L|R)$/, (m) => (m === 'L' ? 'R' : 'L'))
const flip = (p) => [-p[0], p[1], p[2]]
function view(d, mirrored) {          // a dimension as drawn: end points (mirrored for the left twin)
  let p1 = d.p1, p2 = d.p2
  if (d.kind === 'height') p2 = [p1[0], p1[1], 0]
  if (mirrored) { p1 = flip(p1); p2 = flip(p2) }
  const look = d.look_from ? (mirrored ? flip(d.look_from) : d.look_from) : null
  return { d, p1, p2, look, part: mirrored ? twin(d.part) : d.part }
}
function dimsFor(name) {
  const own = st.dims.filter((d) => d.part === name).map((d) => view(d, false))
  const mir = st.dims.filter((d) => d.mirror && d.part !== name && twin(d.part) === name && twin(d.part) !== d.part).map((d) => view(d, true))
  return [...own, ...mir].sort((a, b) => a.d.order - b.d.order)
}
function valueText(d, { mm = true } = {}) {
  if (d.kind === 'radius' && d.value_mm < 0.5) return { big: 'sharp', word: true }
  const v = inch(d.value_mm)
  return { big: d.kind === 'radius' ? `R ${v}` : v, small: mm ? mmText(d.value_mm) : '' }
}
const labelOf = (d) => (d.kind === 'radius' && d.value_mm < 0.5 ? 'sharp?' : (d.kind === 'radius' ? 'R ' : '') + inch(d.value_mm))

// One dimension line in screen space: extension lines, arrows and a vermilion label, off to the side away from the part.
const hits = (r, placed) => placed.some((q) => r.x < q.x + q.w && q.x < r.x + r.w && r.y < q.y + q.h && q.y < r.y + r.h)
function place(placed, x, y, w, h, dx, dy) {   // nudge a label along (dx, dy) until it clears the labels already drawn
  const W = placed.W || S.size().w, H = placed.H || S.size().h
  for (let k = 0; k < 10; k++) {
    x = Math.min(Math.max(x, w / 2 + 6), W - w / 2 - 6); y = Math.min(Math.max(y, h / 2 + 6), H - h / 2 - 6)
    const r = { x: x - w / 2 - 4, y: y - h / 2 - 3, w: w + 8, h: h + 6 }
    if (!hits(r, placed)) { placed.push(r); return [x, y, k] }
    x += dx * (h + 6); y += dy * (h + 6)
  }
  return [Math.min(Math.max(x, w / 2 + 6), W - w / 2 - 6), Math.min(Math.max(y, h / 2 + 6), H - h / 2 - 6), 10]
}
function dimSVG(project, v, { n = null, hi = true, dimmed = false, centre, placed = [] }) {
  const a = project(v.p1), b = project(v.p2), c = project(centre)
  if (a.behind || b.behind) return ''
  const op = dimmed ? 0.32 : 1, sw = hi ? 3.2 : 2.2, col = '#d2451e', label = labelOf(v.d)
  const tw = label.length * 11.4 + 22, th = 34
  const badge = n != null ? `<circle r="15" fill="#fff" stroke="${col}" stroke-width="2.5"/><text y="5.5" text-anchor="middle" font-family="IBM Plex Mono" font-weight="500" font-size="16" fill="${col}">${n}</text>` : ''
  if (v.d.kind === 'radius') {
    const dx = a.x - c.x, dy = a.y - c.y, L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L
    const ex = a.x + ux * 56, side = ux >= 0 ? 1 : -1, bw = n != null ? 36 : 0
    const [lx0, ey] = place(placed, ex + side * (tw / 2 + 8) - side * bw / 2, a.y + uy * 56, tw + bw, th, 0, uy >= 0 ? 1 : -1)
    const lx = lx0 - side * bw / 2
    return `<g opacity="${op}"><circle cx="${a.x}" cy="${a.y}" r="7" fill="none" stroke="${col}" stroke-width="${sw}"/>
      <path d="M${a.x + ux * 9} ${a.y + uy * 9}L${ex} ${ey}H${ex + side * 8}" stroke="${col}" stroke-width="${sw}" fill="none"/>
      <g transform="translate(${lx} ${ey})"><rect x="${-tw / 2}" y="${-th / 2}" width="${tw}" height="${th}" rx="8" fill="${col}"/>
      <text y="7" text-anchor="middle" font-family="IBM Plex Mono" font-weight="500" font-size="19" fill="#fff">${esc(label)}</text>
      ${n != null ? `<g transform="translate(${side * (tw / 2 + 20)} 0)">${badge}</g>` : ''}</g></g>`
  }
  let dx = b.x - a.x, dy = b.y - a.y; const L = Math.hypot(dx, dy)
  if (L < 3) return ''
  const ux = dx / L, uy = dy / L; let nx = -uy, ny = ux
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2
  if ((mx - c.x) * nx + (my - c.y) * ny < 0) { nx = -nx; ny = -ny }
  const off = 30, gap = 5, over = 8
  const A = [a.x + nx * off, a.y + ny * off], B = [b.x + nx * off, b.y + ny * off]
  const ext = (p) => `M${p.x + nx * gap} ${p.y + ny * gap}L${p.x + nx * (off + over)} ${p.y + ny * (off + over)}`
  const ah = 13, aw = 5.5, inside = L > 2 * ah + 8
  const arrow = (P, sx, sy) => { // tip at P, pointing along (sx, sy)
    const bx = P[0] - sx * ah, by = P[1] - sy * ah
    return `M${P[0]} ${P[1]}L${bx + -sy * aw} ${by + sx * aw}L${bx - -sy * aw} ${by - sx * aw}Z`
  }
  const arrows = inside ? arrow(A, -ux, -uy) + arrow(B, ux, uy) : arrow(A, ux, uy) + arrow(B, -ux, -uy)
  const tails = inside ? '' : `M${A[0]} ${A[1]}L${A[0] - ux * 26} ${A[1] - uy * 26}M${B[0]} ${B[1]}L${B[0] + ux * 26} ${B[1] + uy * 26}`
  // label: centred beyond the line, pushed out far enough to clear it whatever the line's angle
  const push = Math.abs(nx) * (tw / 2) + Math.abs(ny) * (th / 2) + 8
  const bw = n != null ? 36 : 0, cx = (A[0] + B[0]) / 2, cy = (A[1] + B[1]) / 2
  const [px, ly, moved] = place(placed, cx + nx * push - bw / 2, cy + ny * push, tw + bw, th, nx, ny)
  const lx = px + bw / 2
  const lead = moved ? `<path d="M${cx} ${cy}L${lx - nx * (Math.abs(nx) * tw / 2 + Math.abs(ny) * th / 2)} ${ly - ny * (Math.abs(nx) * tw / 2 + Math.abs(ny) * th / 2)}" stroke="${col}" stroke-width="1.4" stroke-dasharray="3 3" fill="none"/>` : ''
  return `<g opacity="${op}"><path d="${ext(a)}${ext(b)}" stroke="${col}" stroke-width="1.6" fill="none"/>
    <path d="M${A[0]} ${A[1]}L${B[0]} ${B[1]}${tails}" stroke="${col}" stroke-width="${sw}" fill="none"/><path d="${arrows}" fill="${col}"/>${lead}
    <g transform="translate(${lx} ${ly})"><rect x="${-tw / 2}" y="${-th / 2}" width="${tw}" height="${th}" rx="8" fill="${col}"/>
    <text y="7" text-anchor="middle" font-family="IBM Plex Mono" font-weight="500" font-size="19" fill="#fff">${esc(label)}</text>
    ${n != null ? `<g transform="translate(${-(tw / 2 + 20)} 0)">${badge}</g>` : ''}</g></g>`
}

function overlay() {                  // runs after every rendered frame
  const svg = $('dims'); let h = ''
  if (!st.ready) return
  if (st.tab === 'look' && st.sel && !st.photo && $('cardNote').hidden) {
    const list = dimsFor(st.sel.name), centre = S.partCenter(st.sel.name), placed = []
    const k = list.findIndex((v) => v.d.id === st.row)
    const top = k >= 0 ? dimSVG(S.project, list[k], { n: k + 1, hi: true, centre, placed }) : ''
    list.forEach((v, i) => { if (i !== k) h += dimSVG(S.project, v, { n: i + 1, hi: false, dimmed: k >= 0, centre, placed }) })
    h += top
  }
  if (st.tab === 'measure') {
    const it = st.items[st.mIdx]
    if (it?.kind === 'dim') {
      const v = view(it.d, false), placed = []
      for (const el of [$('howto'), $('printBtn')]) {   // keep the label clear of the text box and the print button
        const r = el.getBoundingClientRect(), o = $('stage').getBoundingClientRect()
        if (r.width) placed.push({ x: r.left - o.left, y: r.top - o.top, w: r.width, h: r.height })
      }
      h += dimSVG(S.project, v, { hi: true, centre: S.partCenter(v.part), placed })
    }
  }
  svg.innerHTML = h
  // pins
  let p = ''
  if (st.tab === 'look') {
    const list = [...notes()]; if (st.note?.point) list.push({ ...st.note, draft: true })
    for (const r of list) {
      if (!r.point) continue
      const q = S.project(r.point); if (q.behind) continue
      p += r.draft ? `<div class="pin new" style="left:${q.x}px;top:${q.y}px"><b>${r.n}</b></div>`
        : `<button class="pin" data-note="${esc(r.id)}" style="left:${q.x}px;top:${q.y}px" aria-label="Note ${r.n} from ${esc(r.who)}" title="Note ${r.n} · ${esc(r.who)}"><b>${r.n}</b></button>`
    }
  }
  $('pins').innerHTML = p
}

// ------------------------------------------------------------------ Look: tap a part
function openPart(name, point) {
  st.sel = { name, point }; st.row = null; S.select(name)
  $('partTitle').textContent = S.partName(name)
  const list = dimsFor(name)
  $('partSizes').innerHTML = list.length ? list.map((v, i) => {
    const t = valueText(v.d)
    return `<li data-id="${v.d.id}"><span class="n">${i + 1}</span><span class="t">${esc(v.d.name)}</span><span><b>${esc(t.big)}</b>${t.small ? `<i>${t.small}</i>` : ''}</span></li>`
  }).join('') : '<li class="empty">No sizes listed for this part. If something looks off, leave a note.</li>'
  $('cardNote').hidden = true; $('cardPart').hidden = false; $('hint').hidden = true; $('showAs').hidden = true
  S.framePart(name, null, phone() ? -0.5 : 0); setScreen(); S.request()
}
function closeCards() {
  st.sel = null; st.row = null; cancelNote(); S.select(null)
  $('cardPart').hidden = true; $('cardNote').hidden = true; $('hint').hidden = false; $('showAs').hidden = false
  setScreen(); S.request()
}
function pickRow(id) {
  st.row = st.row === id ? null : id
  document.querySelectorAll('#partSizes li').forEach((li) => li.classList.toggle('on', li.dataset.id === st.row))
  const v = dimsFor(st.sel.name).find((x) => x.d.id === st.row)
  if (v) S.lookAtSpan([v.p1, v.p2], v.look || S.viewDir(), { min: v.d.kind === 'radius' ? 360 : 260, lift: phone() ? -0.55 : 0 })
  S.request()
}

// notes
function openNote(part, point, camera = null) {
  const n = notes().length + 1
  st.note = { n, part, point, camera, what: null, text: '', photos: [] }
  $('noteLbl').textContent = `Note ${n}${part ? ' · ' + S.partName(part) : ''}`
  document.querySelectorAll('#noteWhat .btn').forEach((b) => b.classList.remove('on'))
  $('noteText').value = ''; renderShots()
  $('cardPart').hidden = true; $('cardNote').hidden = false; $('hint').hidden = true; $('showAs').hidden = true
  setScreen(); S.request()
}
function cancelNote() { st.note = null }
async function renderShots() {
  const box = $('noteShots'); box.querySelectorAll('.th').forEach((e) => e.remove())
  for (const p of st.note?.photos || []) {
    const d = document.createElement('div'); d.className = 'th'
    d.innerHTML = `<img alt="" src="${p.url}"><button aria-label="Remove photo" data-ph="${p.id}">×</button>`
    box.insertBefore(d, box.lastElementChild)
  }
}
async function saveNote() {
  const n = st.note; if (!n) return
  n.text = $('noteText').value.trim()
  if (!n.what && !n.text && !n.photos.length) { toast('Pick what is off, or type a word or two.'); return }
  $('noteSave').disabled = true
  const saved = await submit({ id: store.newId('note'), type: 'note', part: n.part, point: n.point, camera: n.camera,
    what: n.what, text: n.text, view: S.viewDir() }, n.photos)
  $('noteSave').disabled = false
  if (!saved) return
  st.note = null; toast(`Saved note ${n.n}. Everyone can see it.`)
  if (st.photo) { $('cardNote').hidden = true; setScreen() } else closeCards()
  refresh()
}

// ------------------------------------------------------------------ Next to a photo
function describe(c) {
  const C = S.CEN, d = [c.C[0] - C.x, c.C[1] - C.y, c.C[2] - C.z]
  const az = Math.atan2(d[0], d[1]) * 180 / Math.PI, el = Math.atan2(d[2], Math.hypot(d[0], d[1])) * 180 / Math.PI
  const a = Math.abs(az)
  const side = a < 22 ? 'front' : a > 158 ? 'back' : a < 68 ? (az > 0 ? 'front right' : 'front left') : a < 112 ? (az > 0 ? 'right side' : 'left side') : (az > 0 ? 'back right' : 'back left')
  return { side: el > 55 ? 'Above' : `From the ${side}`, sub: `${el > 55 ? 'looking down' : `${Math.round(el)}° up`} · ${(Math.hypot(...d) / 1000).toFixed(1)} m away`, az }
}
async function enterPhoto() {
  if (!st.cams) {
    try { st.cams = await (await fetch('photos/cameras.json')).json() } catch { toast('The photos did not load.'); return }
    st.keys = Object.keys(st.cams).sort((a, b) => describe(st.cams[a]).az - describe(st.cams[b]).az)
  }
  const v = S.viewDir(); let best = 0, bd = -2
  st.keys.forEach((k, i) => { const c = st.cams[k].C; const d = [c[0] - S.CEN.x, c[1] - S.CEN.y, c[2] - S.CEN.z]; const L = Math.hypot(...d); const e = (d[0] * v[0] + d[1] * v[1] + d[2] * v[2]) / L; if (e > bd) { bd = e; best = i } })
  st.lookView = S.getView(); closeCards()
  st.photo = true; document.body.classList.add('photo'); $('photoLeft').hidden = false; $('photoRight').hidden = false; $('wipebar').hidden = false
  showPhoto(best)
}
function showPhoto(i) {
  st.pi = (i + st.keys.length) % st.keys.length; const k = st.keys[st.pi], c = st.cams[k]
  st.photoKey = k
  $('photoImg').src = `photos/${k}.jpg`
  const d = describe(c); $('photoNum').textContent = `Photo ${st.pi + 1} of ${st.keys.length}`; $('photoDir').textContent = d.side; $('photoSub').textContent = d.sub
  S.setPhoto(c); layoutPhoto(); setScreen()
}
function layoutPhoto() {
  if (!st.photo) return
  const c = st.cams[st.photoKey], box = $('lookStage'), W = box.clientWidth, H = box.clientHeight
  const k = Math.min(W / c.w, H / c.h), w = c.w * k, h = c.h * k, s = $('stage').style
  Object.assign(s, { width: w + 'px', height: h + 'px', left: (W - w) / 2 + 'px', top: (H - h) / 2 + 'px' })
  Object.assign($('pframe').style, { inset: '0' })
  wipeTo(st.wipe)
  S.resize()
}
function wipeTo(f) {
  st.wipe = Math.min(0.98, Math.max(0.02, f))
  $('c3d').style.clipPath = st.photo ? `inset(0 0 0 ${st.wipe * 100}%)` : ''
  $('wipebar').querySelector('.bar').style.left = st.wipe * 100 + '%'
}
function exitPhoto() {
  st.photo = false; document.body.classList.remove('photo')
  $('photoLeft').hidden = true; $('photoRight').hidden = true; $('wipebar').hidden = true; $('cardNote').hidden = true; cancelNote()
  $('stage').removeAttribute('style'); $('c3d').style.clipPath = ''
  S.setPhoto(null); S.resize(); if (st.lookView) S.setView(st.lookView, true)
  document.querySelectorAll('#showAs .btn').forEach((b) => b.classList.toggle('on', b.dataset.m === st.mode))
  setScreen()
}

// ------------------------------------------------------------------ Measurements
const firstOpen = () => { const i = st.items.findIndex((x) => !answerOf(x.id)); return i < 0 ? 0 : i }
function renderList() {
  let h = '', g = null
  st.items.forEach((it, i) => {
    if (it.group !== g) {
      g = it.group; const n = st.items.filter((x) => x.group === g).length
      h += `<span class="lbl">${esc((it.d || {}).group_name || 'Check these first · we guessed')} · ${n}</span>`
    }
    const s = status(it), mark = { ok: '✓', no: '✕', q: '?' }[s] || ''
    const name = it.kind === 'dim' ? it.d.name : it.q.name
    let em = it.kind === 'dim' ? labelOf(it.d).replace('?', '') : it.q.model
    const all = answersTo(it.id), wrong = all.filter((a) => a.verdict === 'wrong' && a.value_mm).pop()
    if (s === 'no' && wrong) em = inch(wrong.value_mm)
    if (it.kind === 'q' && s === 'ok') { const c = topChoice(all); if (c) em = c }
    h += `<button class="item${i === st.mIdx && st.tab === 'measure' ? ' on' : ''}" data-i="${i}"><span class="dot ${s}">${mark}</span>${esc(name)}<em>${esc(em)}</em></button>`
  })
  $('mList').innerHTML = h
}
function showItem(i, instant) {
  st.mIdx = Math.max(0, Math.min(st.items.length - 1, i)); const it = st.items[st.mIdx]; if (!it) return
  history.replaceState(null, '', `#measure/${it.id}`)
  if (it.kind === 'dim') {
    const v = view(it.d, false); S.setMode(v.part.startsWith('DOMINO') ? 'ghost' : 'solid'); S.select(v.part)
    S.lookAtSpan([v.p1, v.p2], v.look || [0.9, 0.9, 0.5], { min: it.d.kind === 'radius' ? 380 : 280, lift: 0.2 })
  } else {
    S.setMode('solid'); S.select(it.q.part); S.lookAtSpan([[-260, -170, 640], [260, -100, 1000]], [0.0001, 0.2, 1], { lift: 0.2 })
  }
  renderList(); renderAsk()
  $('mList').querySelector('.item.on')?.scrollIntoView({ block: 'nearest' })
  S.request()
}
function topChoice(all) {
  const n = {}; for (const a of all) if (a.choice && a.choice !== 'unsure') n[a.choice] = (n[a.choice] || 0) + 1
  return Object.keys(n).sort((x, y) => n[y] - n[x])[0] || ''
}
function tallyHTML(it) {               // what everyone said about this one
  const all = answersTo(it.id)
  if (!all.length) return '<span class="none">No one has answered yet.</span>'
  const by = (pred) => all.filter(pred), names = (xs) => xs.map((a) => esc(a.mine ? 'you' : a.who)).join(', ')
  const part = (cls, mark, label, xs, extra = '') => xs.length ? `<span class="t ${cls}"><i>${mark}</i><b>${xs.length}</b> ${label}<em>${names(xs)}${extra}</em></span>` : ''
  if (it.kind === 'q') {
    return it.q.choices.map(([k, label]) => part('ok', '✓', esc(label), by((a) => a.choice === k))).join('') + part('q', '?', 'not sure', by((a) => a.choice === 'unsure'))
  }
  const wrong = by((a) => a.verdict === 'wrong')
  return part('ok', '✓', 'right', by((a) => a.verdict === 'right')) +
    (wrong.length ? `<span class="t no"><i>✕</i><b>${wrong.length}</b> wrong<em>${wrong.map((a) => `${esc(a.mine ? 'you' : a.who)} <span class="mono">${a.value_mm ? inch(a.value_mm) : '?'}</span>`).join(', ')}</em></span>` : '') +
    part('q', '?', 'not sure', by((a) => a.verdict === 'unsure'))
}
function srcText(d) {
  const tol = d.tolerance_mm ? ` Good to about ${inch(d.tolerance_mm)}.` : ''
  let s = { taped: '<b>Taped on the chair.</b>', photos: `<b>Worked out from the photos.</b>${tol}`, guess: '<b>Our guess.</b> No photo shows it well.' }[d.source] || ''
  if (d.tape_mm) s += ` The tape said ${inch(d.tape_mm)}.`
  return s
}
function renderAsk() {
  const it = st.items[st.mIdx]; if (!it) return
  const a = answerOf(it.id)
  $('pgN').textContent = `${st.mIdx + 1} of ${st.items.length}`
  $('askTally').innerHTML = tallyHTML(it)
  $('pgPrev').disabled = st.mIdx === 0; $('pgNext').disabled = st.mIdx === st.items.length - 1
  if (it.kind === 'dim') {
    const d = it.d, t = valueText(d)
    $('askName').textContent = d.name; $('askSrc').innerHTML = srcText(d)
    $('askVal').hidden = false; $('askVal').className = 'val' + (t.word ? ' word' : ''); $('askVal').innerHTML = `${esc(t.big)}${t.small ? `<small>${t.small}</small>` : ''}`
    const on = (v) => (a?.verdict === v ? ' on' : '')
    $('askAns').innerHTML = `<button class="btn pri${on('right')} okk" data-a="right">✓ Right</button><button class="btn${on('wrong')} nok" data-a="wrong">✕ Wrong</button><button class="btn${on('unsure')} qq" data-a="unsure">Not sure</button>`
    $('howto').innerHTML = `<p>${esc(d.note)}</p>` + (a?.verdict === 'wrong' ? `<p style="color:var(--ink);margin-top:8px">You said <b class="mono">${inch(a.value_mm)}</b> (${mmText(a.value_mm)}).</p>` : '')
  } else {
    const q = it.q
    $('askName').textContent = q.name; $('askSrc').innerHTML = `<b>Our guess:</b> ${esc((q.choices.find((c) => c[0] === q.model)?.[1] || q.model).toLowerCase())}. The photos can’t tell.`
    $('askVal').className = 'val'; $('askVal').hidden = true
    $('askAns').innerHTML = q.choices.map(([k, label]) => `<button class="btn wide${a?.choice === k ? ' on' : ''}" data-c="${k}">${esc(label)}</button>`).join('') +
      `<button class="btn${a?.choice === 'unsure' ? ' on qq' : ''}" data-c="unsure">Not sure</button>`
    $('howto').innerHTML = `<p>${esc(q.note)}</p>${slatSketch(q)}`
  }
}
function slatSketch(q) {               // plan view, seen from above: flat vs turned side slats, centre slat between
  const deg = q.turn_deg?.[0] || 7
  const slat = (x, w, rot, col) => `<rect x="${x - w / 2}" y="-5" width="${w}" height="10" rx="2" fill="${col}" transform="rotate(${rot} ${x} 0)"/>`
  const row = (y, turned, label) => `<g transform="translate(0 ${y})">${slat(70, 46, turned ? -deg : 0, '#7b5136')}${slat(150, 86, 0, '#7b5136')}${slat(230, 46, turned ? deg : 0, '#7b5136')}
    <text x="290" y="6" font-family="Inter" font-size="15" fill="#1d2126">${label}</text></g>`
  return `<svg viewBox="0 0 400 112" width="400" height="112" aria-label="Seen from above">
    <text x="16" y="22" font-family="Inter" font-weight="600" font-size="11" letter-spacing="1.2" fill="#6b6f76">SEEN FROM ABOVE · FRONT IS DOWN</text>
    ${row(52, false, 'Flat')}${row(88, true, 'Turned')}</svg>`
}
async function answer(v) {
  const it = st.items[st.mIdx]
  if (v === 'wrong') { openSheet(it.d); return }
  if (!await submit({ id: `answer-${it.id}`, type: 'answer', dimId: it.id, name: it.d.name, verdict: v, value_mm: it.d.value_mm, model_mm: it.d.value_mm })) return
  await refresh(); next()
}
async function choose(c) {
  const it = st.items[st.mIdx]
  if (!await submit({ id: `question-${it.id}`, type: 'question', qid: it.id, name: it.q.name, choice: c })) return
  await refresh(); next()
}
function next() {
  const after = st.items.findIndex((x, i) => i > st.mIdx && !answerOf(x.id))
  setTimeout(() => showItem(after >= 0 ? after : Math.min(st.mIdx + 1, st.items.length - 1)), 220)
}

// the "wrong" sheet: whole inches -/+, eighths in one row, finer 1/16 and 1/32, or type it
const FR = ['0', '1/8', '1/4', '3/8', '1/2', '5/8', '3/4', '7/8']
function openSheet(d) {
  const t = Math.round(d.value_mm / MM * 32), r = t % 32
  st.sheet = { d, whole: Math.floor(t / 32), e: Math.floor(r / 4), s16: (r % 4) >= 2, s32: r % 2 === 1, typed: null }
  $('fine').hidden = !(st.sheet.s16 || st.sheet.s32); $('finerBtn').classList.toggle('on', !$('fine').hidden)
  $('shType').value = ''; $('shType').classList.remove('bad')
  $('shLbl').textContent = `${d.name} · we have ${inch(d.value_mm)}`
  $('fracs').innerHTML = FR.map((f, i) => `<button class="btn" data-e="${i}">${f === '0' ? '0' : f}</button>`).join('')
  $('sheet').hidden = false; renderSheet(); setScreen()
}
const sheetMM = () => { const s = st.sheet; return s.typed ?? (s.whole + s.e / 8 + (s.s16 ? 1 / 16 : 0) + (s.s32 ? 1 / 32 : 0)) * MM }
function renderSheet() {
  const s = st.sheet, mm = sheetMM()
  $('shVal').innerHTML = `${inch(mm)}<small>${mmText(mm)}</small>`
  $('inWhole').textContent = s.typed != null ? Math.floor(mm / MM + 1e-9) : s.whole
  $('inMinus').disabled = s.whole <= 0 && s.typed == null
  $('fracs').querySelectorAll('.btn').forEach((b) => b.classList.toggle('on', s.typed == null && +b.dataset.e === s.e))
  $('add16').classList.toggle('on', s.typed == null && s.s16); $('add32').classList.toggle('on', s.typed == null && s.s32)
  $('shSave').textContent = `Save ${inch(mm)}`
}
function untype() { st.sheet.typed = null; $('shType').value = ''; $('shType').classList.remove('bad') }
function closeSheet() { $('sheet').hidden = true; st.sheet = null; setScreen() }
async function saveSheet() {
  const s = st.sheet, mm = sheetMM(), it = st.items[st.mIdx]
  if (!await submit({ id: `answer-${it.id}`, type: 'answer', dimId: it.id, name: s.d.name, verdict: 'wrong', value_mm: Math.round(mm * 100) / 100,
    model_mm: s.d.value_mm, typed: s.typed != null ? $('shType').value.trim() : null })) return
  closeSheet(); toast(`Saved ${inch(mm)} for ${s.d.name.toLowerCase()}`); await refresh(); next()
}

// print the whole list: one small picture per size, the line drawn on it, and a blank for the reading
async function printList() {
  const out = document.createElement('div'); out.className = 'printout'
  const mode = S.selected(); S.setMode('solid')
  let h = `<h1>Essick rocker · sizes to check (model v${st.version})</h1><p>Write the real size next to each one. Inches to the nearest 1/32.</p><div class="pg">`
  for (const it of st.items) {
    if (it.kind !== 'dim') { h += `<div class="pc"><h3>${esc(it.q.name)}</h3><p>${esc(it.q.note)}</p><p class="blank">☐ Flat &nbsp; ☐ Turned &nbsp; ☐ Not sure</p></div>`; continue }
    const v = view(it.d, false); S.select(v.part)
    const w = 360, hh = 230, pic = S.still(w, hh, [v.p1, v.p2], v.look || [0.9, 0.9, 0.5])
    const placed = []; placed.W = w; placed.H = hh
    const svg = dimSVG(pic.project, v, { hi: true, centre: S.partCenter(v.part), placed })
    h += `<div class="pc"><div class="pim"><img src="${pic.url}" alt=""><svg viewBox="0 0 ${w} ${hh}">${svg}</svg></div><h3>${esc(it.d.name)}: ${esc(labelOf(it.d))} (${mmText(it.d.value_mm)})</h3><p>${esc(it.d.note)}</p><p class="blank">Real size: ______________</p></div>`
  }
  out.innerHTML = h + '</div>'; document.body.appendChild(out)
  S.select(mode); showItem(st.mIdx)
  await Promise.all([...out.querySelectorAll('img')].map((i) => i.decode().catch(() => {})))
  addEventListener('afterprint', () => out.remove(), { once: true })
  window.print()
}

// ------------------------------------------------------------------ Templates (drawn by templates/*.py against the model; files on main)
const TPL = [
  ['rocker_template', 'Rocker', `${inch(1118.4)} long, tip to tip`, 7],
  ['rocker_bending_form', 'Rocker bending form', 'Two-part form for the laminations', 14],
  ['slat_template', 'Back slats', `Centre slat ×1, side slat ×2 · ${inch(711.8)} long`, 8],
  ['slat_bending_form', 'Slat bending form', 'One form for all three slats', 10],
  ['seat_plan', 'Seat, from above', `${inch(537.1)} wide × ${inch(548.6)} deep`, 12],
  ['seat_sections', 'Seat dish, cross-sections', 'The dish shape at five stations, front to back', 9],
  ['crest_plan', 'Crest rail, from above', `Blank ${inch(526.3)} long`, 3],
  ['crest_back', 'Crest rail, from the back', 'The arch over the slats', 3],
  ['crest_sections', 'Crest rail, cross-sections', 'Shape across the rail', 2],
  ['arms_plan', 'Arms, from above', `${inch(463.9)} long, along the curve`, 3],
  ['arms_side', 'Arms, from the side', 'Thickness and slope', 3],
  ['legs_front', 'Front legs', 'Both faces, left and right', 8],
  ['legs_back', 'Back legs', 'Both faces, left and right', 18],
]
async function renderTemplates() {
  const rows = await Promise.all(TPL.map(async ([base, title, meta, sheets]) => {
    const ok = await fetch(new URL(`${base}_preview.png`, TEMPLATES), { method: 'HEAD' }).then((r) => r.ok).catch(() => false)
    return { base, title, meta, sheets, ok }
  }))
  const u = (f) => new URL(f, TEMPLATES).href
  const drawn = rows.filter((r) => r.ok), not = rows.filter((r) => !r.ok)
  $('tpl').innerHTML = `<p class="lead">Print a template at full size and lay it on the real part. If it does not match, say so on the Look page.
    <b>All of these are drawn from the current model (v${st.version}).</b> If your readings change the model, they will be drawn again.</p>` +
    drawn.map((r) => `<div class="trow"><a class="pv" href="${u(r.base + '_preview.png')}" target="_blank" rel="noopener"><img loading="lazy" alt="" src="${u(r.base + '_preview.png')}"></a>
      <div><h3>${esc(r.title)}<span class="badge">MODEL V${st.version}</span></h3><div class="meta">${esc(r.meta)} · <span class="mono">${r.sheets}</span> Letter sheets</div></div>
      <div class="acts"><a class="btn pri" href="${u(r.base + '_tiled_letter.pdf')}" target="_blank" rel="noopener">Print on Letter paper</a>
      <a class="btn" href="${u(r.base + '_full_1to1.pdf')}" target="_blank" rel="noopener">One big sheet</a><a class="cnc" href="${u(r.base + '.dxf')}" download>DXF for CNC</a></div></div>`).join('') +
    `<div class="todo"><b>Not drawn yet:</b> ${[...not.map((r) => r.title.toLowerCase()), 'joint layout'].join(' · ')}</div>`
}

// ------------------------------------------------------------------ Feedback: everyone's notes, answers and comments
const FILTERS = [['all', 'All'], ['note', 'Notes'], ['size', 'Sizes'], ['comment', 'Comments']]
const group = (r) => (r.type === 'note' || r.type === 'comment' ? r.type : 'size')
const fmtDay = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
function when(ms) {
  const mins = (Date.now() - ms) / 60000; if (!(mins >= 0)) return ''
  if (mins < 1) return 'just now'
  if (mins < 60) return `${Math.floor(mins)} min ago`
  if (mins < 60 * 24) return `${Math.floor(mins / 60)} h ago`
  return fmtDay.format(new Date(ms))
}
function openDrawer(focus) {
  if (focus) st.filter = 'all'
  st.focus = focus || null
  $('drawer').hidden = false; renderDrawer(); setScreen()
  $('cName').value = store.getName()
  if (!focus) { const l = $('dList'); l.scrollTop = l.scrollHeight }
}
function closeDrawer() {
  $('drawer').hidden = true
  if (['#notes', '#feedback', '#comments'].includes(location.hash)) history.replaceState(null, '', '#' + st.tab)
  setScreen()
}
function rowHTML(r, urls) {
  let k, title, body = ''
  if (r.type === 'note') { k = `<span class="k pin">${r.n}</span>`; title = `${r.part ? S.partName(r.part) : 'Note'}${r.what ? ': ' + r.what : ''}`; body = r.text ? `<p class="say">${esc(r.text)}</p>` : ''; if (r.camera) body += `<p>Next to photo ${esc(r.camera)}</p>` }
  else if (r.type === 'comment') { k = '<span class="k cm" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4A1.5 1.5 0 0 1 4 14.5z"/></svg></span>'; title = ''; body = `<p class="say">${esc(r.text)}</p>` }
  else if (r.type === 'answer') { const c = kindOf(r); k = `<span class="k ${c}">${{ ok: '✓', no: '✕', q: '?' }[c]}</span>`; title = r.name; body = `<p>${r.verdict === 'wrong' ? `Should be <span class="v">${inch(r.value_mm)}</span> (${mmText(r.value_mm)}); model has ${inch(r.model_mm)}` : r.verdict === 'right' ? `Right: <span class="v">${inch(r.value_mm)}</span>` : 'Not sure'}</p>` }
  else if (r.type === 'question') { k = `<span class="k ${r.choice === 'unsure' ? 'q' : 'ok'}">${r.choice === 'unsure' ? '?' : '✓'}</span>`; title = r.name; body = `<p>${r.choice === 'unsure' ? 'Not sure' : esc(r.choice)}</p>` }
  else { k = '<span class="k ok">✓</span>'; title = `${S.partName(r.part)} looks right`; body = '' }
  const ths = (r.photos || []).filter((p) => urls[p]).map((p) => `<a href="${urls[p]}" target="_blank" rel="noopener"><img alt="Photo" loading="lazy" src="${urls[p]}"></a>`).join('')
  const head = `<div class="dwho"><b>${esc(r.mine ? `${r.who} (you)` : r.who)}</b><time>${esc(when(r.at))}</time></div>`
  return `<li class="drow${r.id === st.focus ? ' fresh' : ''}" data-id="${esc(r.id)}">${k}<div>${head}${title ? `<h4>${esc(title)}</h4>` : ''}${body}${ths ? `<div class="ths">${ths}</div>` : ''}</div>` +
    (r.mine ? `<button class="del" data-del="${esc(r.id)}">Delete</button>` : '<span></span>') + '</li>'
}
async function renderDrawer() {
  const rs = st.records, f = st.filter || 'all', n = rs.length, ppl = people()
  $('drawSub').textContent = store.SHARED
    ? (n ? `${n} from ${ppl} ${ppl === 1 ? 'person' : 'people'}. Everyone with the link can see these.` : 'Everyone with the link can see these.')
    : 'Preview: kept on this device only. On the live page everyone sees everyone’s.'
  $('dFilter').innerHTML = FILTERS.map(([k, label]) => {
    const c = k === 'all' ? n : rs.filter((r) => group(r) === k).length
    return `<button class="btn${f === k ? ' on' : ''}" data-f="${k}">${label}<b>${c}</b></button>`
  }).join('')
  const show = rs.filter((r) => f === 'all' || group(r) === f)
  const closed = !store.state.postingEnabled
  $('cForm').hidden = closed; $('cClosed').hidden = !closed
  if (store.state.loadError && !n) { $('dList').innerHTML = '<div class="dempty"><b>Could not load the feedback</b>Check your connection. It will try again in a minute.</div>'; return }
  if (!show.length) {
    const msg = { all: 'Tap a part on the Look page, answer a few on Measurements, or leave a comment below.', note: 'Tap a part on the Look page, then “Something is off here”.',
      size: 'Answer a few on Measurements, or tap a part and “Looks right”.', comment: 'Say what you think of the chair, or ask Joe a question.' }[f]
    $('dList').innerHTML = `<div class="dempty"><b>Nothing yet</b>${msg}</div>`; return
  }
  const urls = {}
  for (const r of show) for (const p of r.photos || []) { const u = await store.photoURL(p).catch(() => null); if (u) urls[p] = u }
  $('dList').innerHTML = `<ol class="dl">${show.map((r) => rowHTML(r, urls)).join('')}</ol>`
  if (st.focus) { $('dList').querySelector(`[data-id="${CSS.escape(st.focus)}"]`)?.scrollIntoView({ block: 'center' }); st.focus = null }
}
function cStatus(kind, text) { const s = $('cStatus'); s.className = 'cstatus' + (kind ? ' ' + kind : ''); s.textContent = text || '' }
async function postComment(e) {
  e.preventDefault()
  const name = $('cName').value.trim(), body = $('cBody').value.trim()
  if (!name) { cStatus('warn', 'Add your name first.'); $('cName').focus(); return }
  if (!body) { cStatus('warn', 'Write a comment first.'); $('cBody').focus(); return }
  store.setName(name)
  $('cPost').disabled = true; $('cPost').textContent = 'Posting…'; cStatus('', '')
  let saved = null
  try { saved = await store.save({ id: store.newId('comment'), type: 'comment', who: name, text: body, website: $('cWebsite').value, model: `v${st.version}` }) } catch (err) {
    if (err.status === 403) store.state.postingEnabled = false
    cStatus(err.status === 429 ? 'warn' : 'err', err.status === 429 ? 'Slow down a little. Wait a few minutes, then post again.' : err.message || 'That did not post. Try again in a moment.')
  }
  $('cPost').disabled = false; $('cPost').textContent = 'Post'
  if (!saved) { if (!store.state.postingEnabled) renderDrawer(); return }
  $('cBody').value = ''; cStatus('ok', 'Posted. Thanks!')
  await refresh(); st.focus = null
  const l = $('dList'); l.scrollTop = l.scrollHeight
}

// ------------------------------------------------------------------ your name, asked once, shown next to everything you give
function ensureName() {
  const have = store.getName(); if (have) return Promise.resolve(have)
  return new Promise((done) => {
    $('who').hidden = false; $('whoName').value = ''; setScreen()
    setTimeout(() => $('whoName').focus(), 30)
    const finish = (v) => { $('who').hidden = true; $('whoForm').onsubmit = null; $('whoCancel').onclick = null; setScreen(); done(v) }
    $('whoForm').onsubmit = (e) => {
      e.preventDefault(); const v = $('whoName').value.trim()
      if (!v) { $('whoName').focus(); return }
      store.setName(v); finish(store.getName())
    }
    $('whoCancel').onclick = () => finish(null)
  })
}

// ------------------------------------------------------------------ wiring
function wire() {
  document.querySelectorAll('.tab').forEach((t) => t.addEventListener('click', () => { closeDrawer(); go(t.dataset.t) }))
  $('notesBtn').onclick = () => openDrawer(); $('drawClose').onclick = closeDrawer
  $('drawer').addEventListener('click', async (e) => {
    if (e.target === $('drawer')) closeDrawer()
    const f = e.target.closest('[data-f]'); if (f) { st.filter = f.dataset.f; renderDrawer(); return }
    const del = e.target.closest('[data-del]')
    if (del) {
      del.disabled = true
      try { await store.remove(del.dataset.del) } catch { toast('That did not delete. Try again in a moment.') }
      await refresh()
    }
  })
  $('cForm').addEventListener('submit', postComment)
  $('cBody').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) postComment(e) })
  $('cName').addEventListener('change', () => { if ($('cName').value.trim()) store.setName($('cName').value) })
  for (const id of ['cName', 'cBody']) $(id).addEventListener('input', () => { if (/warn|ok/.test($('cStatus').className)) cStatus('', '') })
  $('pins').addEventListener('click', (e) => { const b = e.target.closest('[data-note]'); if (b) openDrawer(b.dataset.note) })
  addEventListener('keydown', (e) => { if (e.key === 'Escape') { if (!$('who').hidden) $('whoCancel').click(); else if (!$('drawer').hidden) closeDrawer(); else if (!$('sheet').hidden) closeSheet(); else if (st.tab === 'look') closeCards() } })

  // taps on the 3D view (a short press without a drag)
  let down = null
  $('stage').addEventListener('pointerdown', (e) => { down = e.target.closest('.bar, .pin') ? null : { x: e.clientX, y: e.clientY, t: performance.now() } })
  $('stage').addEventListener('pointerup', (e) => {
    if (!down || !st.ready) return; const moved = Math.hypot(e.clientX - down.x, e.clientY - down.y), dt = performance.now() - down.t; down = null
    if (moved > 7 || dt > 600 || st.tab !== 'look') return
    const hit = S.pick(e.clientX, e.clientY)
    if (st.photo) {
      const r = $('stage').getBoundingClientRect()
      if (hit && (e.clientX - r.left) / r.width > st.wipe) openNote(hit.part, hit.point, st.photoKey)
      else toast('Tap on the model side of the bar.')
      return
    }
    if (!$('cardNote').hidden) { if (hit && st.note) { st.note.point = hit.point; st.note.part = hit.part; $('noteLbl').textContent = `Note ${st.note.n} · ${S.partName(hit.part)}`; S.request() } return }
    if (hit) openPart(hit.part, hit.point); else if (st.sel) closeCards()
  })
  // the wipe bar
  const bar = $('wipebar').querySelector('.bar')
  bar.addEventListener('pointerdown', (e) => { bar.setPointerCapture(e.pointerId); e.stopPropagation() })
  bar.addEventListener('pointermove', (e) => { if (!bar.hasPointerCapture(e.pointerId)) return; const r = $('stage').getBoundingClientRect(); wipeTo((e.clientX - r.left) / r.width) })
  new ResizeObserver(() => layoutPhoto()).observe($('lookStage'))

  $('views').addEventListener('click', (e) => {
    const b = e.target.closest('[data-v]'); if (!b) return
    document.querySelectorAll('#views .btn').forEach((x) => x.classList.toggle('on', x === b)); S.goView(b.dataset.v)
  })
  $('showAs').addEventListener('click', (e) => {
    const b = e.target.closest('[data-m]'); if (!b) return
    if (b.dataset.m === 'photo') { enterPhoto(); return }
    st.mode = b.dataset.m; S.setMode(st.mode)
    document.querySelectorAll('#showAs .btn').forEach((x) => x.classList.toggle('on', x === b))
  })
  $('startOver').onclick = () => {
    closeCards(); st.mode = 'solid'; S.setMode('solid')
    document.querySelectorAll('#showAs .btn').forEach((x) => x.classList.toggle('on', x.dataset.m === 'solid'))
    document.querySelectorAll('#views .btn').forEach((x) => x.classList.toggle('on', x.dataset.v === 'corner'))
    S.goView('corner'); toast('Back to the whole chair. All the notes are kept.')
  }
  $('photoBack').onclick = exitPhoto
  $('photoPrev').onclick = () => showPhoto(st.pi - 1); $('photoNext').onclick = () => showPhoto(st.pi + 1)
  $('photoOff').onclick = () => toast('Tap the spot on the model side of the bar.')

  // part card
  document.querySelectorAll('[data-close]').forEach((b) => (b.onclick = () => { if (st.photo) { cancelNote(); $('cardNote').hidden = true; setScreen(); S.request() } else closeCards() }))
  $('partSizes').addEventListener('click', (e) => { const li = e.target.closest('li[data-id]'); if (li) pickRow(li.dataset.id) })
  $('partOk').onclick = async () => {
    const part = st.sel.name
    if (!await submit({ id: `ok-${part}`, type: 'part_ok', part })) return
    toast(`Saved: ${S.partName(part).toLowerCase()} looks right`); closeCards(); refresh()
  }
  $('partOff').onclick = () => openNote(st.sel.name, st.sel.point)
  // note card
  $('noteWhat').addEventListener('click', (e) => {
    const b = e.target.closest('[data-w]'); if (!b || !st.note) return
    st.note.what = st.note.what === b.dataset.w ? null : b.dataset.w
    document.querySelectorAll('#noteWhat .btn').forEach((x) => x.classList.toggle('on', x.dataset.w === st.note.what))
  })
  $('notePhotos').addEventListener('change', async (e) => {
    const files = [...e.target.files]; e.target.value = ''
    for (const f of files) {
      if ((st.note?.photos.length || 0) >= 6) { toast('Up to 6 photos on one note.'); break }
      try { const ph = await store.preparePhoto(f); st.note?.photos.push(ph) } catch { toast('That photo could not be read.') }
    }
    renderShots()
  })
  $('noteShots').addEventListener('click', (e) => {
    const b = e.target.closest('[data-ph]'); if (!b || !st.note) return
    st.note.photos = st.note.photos.filter((p) => p.id !== b.dataset.ph); renderShots()
  })
  $('noteSave').onclick = saveNote
  $('noteCancel').onclick = () => { if (st.photo) { cancelNote(); $('cardNote').hidden = true; setScreen(); S.request() } else { cancelNote(); st.sel ? openPart(st.sel.name, st.sel.point) : closeCards() } }

  // measurements
  $('mList').addEventListener('click', (e) => { const b = e.target.closest('[data-i]'); if (b) showItem(+b.dataset.i) })
  $('askAns').addEventListener('click', (e) => {
    const a = e.target.closest('[data-a]'); if (a) return answer(a.dataset.a)
    const c = e.target.closest('[data-c]'); if (c) choose(c.dataset.c)
  })
  $('pgPrev').onclick = () => showItem(st.mIdx - 1); $('pgNext').onclick = () => showItem(st.mIdx + 1)
  $('printBtn').onclick = printList
  $('howto').onclick = () => $('howto').classList.toggle('open')
  // the sheet
  $('inMinus').onclick = () => { untype(); st.sheet.whole = Math.max(0, st.sheet.whole - 1); renderSheet() }
  $('inPlus').onclick = () => { untype(); st.sheet.whole++; renderSheet() }
  $('fracs').addEventListener('click', (e) => { const b = e.target.closest('[data-e]'); if (!b) return; untype(); st.sheet.e = +b.dataset.e; renderSheet() })
  $('finerBtn').onclick = () => { const f = $('fine'); f.hidden = !f.hidden; $('finerBtn').classList.toggle('on', !f.hidden); if (f.hidden) { st.sheet.s16 = st.sheet.s32 = false; renderSheet() } }
  $('add16').onclick = () => { untype(); st.sheet.s16 = !st.sheet.s16; renderSheet() }
  $('add32').onclick = () => { untype(); st.sheet.s32 = !st.sheet.s32; renderSheet() }
  $('shType').addEventListener('input', (e) => {
    const v = e.target.value.trim(), mm = parse(v)
    e.target.classList.toggle('bad', !!v && mm == null)
    st.sheet.typed = v && mm != null && mm > 0 ? mm : null; renderSheet()
  })
  $('shType').addEventListener('keydown', (e) => { if (e.key === 'Enter' && st.sheet.typed != null) saveSheet() })
  $('sheet').addEventListener('click', (e) => { if (e.target === $('sheet')) closeSheet() })
  $('shCancel').onclick = closeSheet; $('shSave').onclick = saveSheet
}

// for the screenshot script and for debugging from the console
window.__er = { S, st, store, openPart, openNote, openDrawer, go, showItem, openSheet, enterPhoto, refresh }
boot()
