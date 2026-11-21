// Cloud vs model: the measured 3D points (viewer/cloud, from tools/viewer_cloud.py) coloured by their signed distance to the
// model that is showing. Distances are computed here, in the browser, for every model version, so nothing needs re-exporting
// when a model lands. Sign: + = the wood point lies OUTSIDE the model (model too small there), − = inside (model too big).
// Inside/outside: ray parity for closed parts, the nearest face's normal for open ones (the seat).
import * as THREE from 'three'
import { MeshBVH } from 'three-mesh-bvh'
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js'

const LAYERS = [                                    // key, label, drawn bigger?
  ['dense', 'Matched points', false], ['sparse', 'Solve points', false], ['dots', 'Seat dots', true],
]
// diverging: rust (inside) — neutral grey — blue (outside). Midpoint is a mid grey so it still reads on the paper background.
const C_IN = new THREE.Color('#c2410c'), C_MID = new THREE.Color('#9b968b'), C_OUT = new THREE.Color('#1d5fd6'), C_FAR = new THREE.Color('#cfc8b8')
const SIDE = { L: 'left', R: 'right', C: 'centre' }

export function createCloud({ scene, request, $, onChange }) {
  const st = {
    on: true, mode: 'dist', scale: 6, cutoff: 25, size: 3, layers: { dense: true, sparse: false, dots: true },
    data: {}, partOf: null, hiddenKeys: new Set(), busy: false, modelId: null, hover: -1,
  }
  const group = new THREE.Group(); scene.add(group)
  const objs = {}                                   // layer -> THREE.Points
  const hoverGroup = new THREE.Group(); scene.add(hoverGroup)

  const mat = (big) => new THREE.ShaderMaterial({
    uniforms: { size: { value: 3 }, pr: { value: 1 }, ring: { value: big ? new THREE.Color('#1d2126') : new THREE.Color('#f4f1ea') }, ringA: { value: big ? 0.9 : 0.7 } },
    vertexShader: `attribute vec3 color; attribute float show; uniform float size; uniform float pr; varying vec3 vC;
      void main() { vC = color; if (show < 0.5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); gl_PointSize = 0.0; return; }
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_PointSize = size * pr; }`,
    fragmentShader: `uniform vec3 ring; uniform float ringA; uniform float size; uniform float pr; varying vec3 vC;
      void main() { vec2 q = gl_PointCoord * 2.0 - 1.0; float r = length(q); if (r > 1.0) discard;
        float edge = 1.0 - 1.6 / (size * pr); gl_FragColor = r > edge ? vec4(mix(vC, ring, ringA), 1.0) : vec4(vC, 1.0); }`,
    depthTest: true, depthWrite: true,
  })

  // ---------------------------------------------------------------- data
  async function load() {
    const idx = await (await fetch('cloud/index.json', { cache: 'no-cache' })).json()
    for (const [key, , big] of LAYERS) {
      const L = idx.layers[key]; if (!L) continue
      const buf = await (await fetch(`cloud/${L.file}`, { cache: 'no-cache' })).arrayBuffer(); const n = L.n
      let o = 0; const take = (T, k) => { const a = new T(buf, o, k); o += k * T.BYTES_PER_ELEMENT; return a }
      const xyz = take(Float32Array, 3 * n), rms = take(Float32Array, n), sigma = take(Float32Array, n), rgb = take(Uint8Array, 3 * n), views = take(Uint8Array, n)
      const d = { n, xyz, rms, sigma, rgb, views, desc: L.desc, big, dist: new Float32Array(n).fill(NaN), part: new Int16Array(n).fill(-1), near: new Float32Array(3 * n) }
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(xyz, 3))
      g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(3 * n), 3))
      g.setAttribute('show', new THREE.BufferAttribute(new Float32Array(n), 1))
      const p = new THREE.Points(g, mat(big)); p.frustumCulled = false; p.renderOrder = big ? 4 : 3
      objs[key] = p; group.add(p); st.data[key] = d
    }
    renderControls(); restyle()
  }

  // ---------------------------------------------------------------- distances to the model
  let parts = []                                    // { name, key, label, bvh, closed, box }
  async function measure(modelGroup, modelId) {
    if (!Object.keys(st.data).length || modelId === st.modelId) return
    const token = (st.token = {}); st.busy = true; st.modelId = modelId; renderSummary()
    parts = []
    for (const g of modelGroup.children) {
      const { mesh, key, name } = g.userData; mesh.updateMatrix()
      const geo = new THREE.BufferGeometry(); geo.setAttribute('position', mesh.geometry.getAttribute('position').clone())
      if (mesh.geometry.index) geo.setIndex(mesh.geometry.index.clone())
      geo.applyMatrix4(mesh.matrix)
      const welded = mergeVertices(geo, 1e-3); welded.computeBoundingBox()
      parts.push({ name, key, label: label(name), bvh: new MeshBVH(welded), closed: isClosed(welded), box: welded.boundingBox, geo: welded })
    }
    const P = new THREE.Vector3(), hit = {}, ray = new THREE.Ray(), dir = new THREE.Vector3(0.5774, 0.5774, 0.5774).add(new THREE.Vector3(0.013, -0.021, 0.007)).normalize()
    const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), n = new THREE.Vector3(), best = new THREE.Vector3()
    let done = 0; const total = Object.values(st.data).reduce((s, d) => s + d.n, 0)
    for (const d of Object.values(st.data)) {
      for (let i = 0; i < d.n; i++) {
        P.fromArray(d.xyz, 3 * i); let bd = Infinity, bp = -1, bf = -1
        for (let k = 0; k < parts.length; k++) {
          if (parts[k].box.distanceToPoint(P) >= bd) continue
          const r = parts[k].bvh.closestPointToPoint(P, hit, 0, bd); if (r && r.distance < bd) { bd = r.distance; bp = k; bf = r.faceIndex; best.copy(r.point) }
        }
        if (bp < 0) continue
        const part = parts[bp]; let inside
        if (part.closed) {
          ray.origin.copy(P); ray.direction.copy(dir)
          inside = part.bvh.raycast(ray, THREE.DoubleSide).length % 2 === 1
        } else {
          const ix = part.geo.index; const pos = part.geo.getAttribute('position')
          a.fromBufferAttribute(pos, ix.getX(3 * bf)); b.fromBufferAttribute(pos, ix.getX(3 * bf + 1)); c.fromBufferAttribute(pos, ix.getX(3 * bf + 2))
          n.subVectors(c, b).cross(a.clone().sub(b)).normalize()
          inside = P.clone().sub(best).dot(n) < 0
        }
        d.dist[i] = inside ? -bd : bd; d.part[i] = bp; best.toArray(d.near, 3 * i)
        if (++done % 1500 === 0) {
          $('cloudBusy').textContent = `Measuring ${Math.round(done / total * 100)}%`
          await new Promise((r) => setTimeout(r)); if (token !== st.token) return
        }
      }
    }
    st.busy = false; restyle()
  }

  function isClosed(geo) {                          // every edge shared by exactly two triangles
    const ix = geo.index; if (!ix) return false
    const m = new Map()
    for (let t = 0; t < ix.count; t += 3) for (let e = 0; e < 3; e++) {
      const u = ix.getX(t + e), v = ix.getX(t + (e + 1) % 3); const k = u < v ? u * 1e7 + v : v * 1e7 + u
      m.set(k, (m.get(k) || 0) + 1)
    }
    for (const c of m.values()) if (c !== 2) return false
    return true
  }
  function label(name) {
    const base = { ROCKER: 'Rocker', FLEG: 'Front leg', BLEG: 'Back leg', SEAT: 'Seat', ARM: 'Arm', CREST: 'Crest', SLAT: 'Slat' }
    const [p, s] = String(name).split('_'); return `${base[p] || p}${s ? ` · ${SIDE[s] || s}` : ''}`
  }

  // ---------------------------------------------------------------- colour + visibility
  const tmp = new THREE.Color()
  function colourFor(v) {
    const t = Math.max(-1, Math.min(1, v / st.scale))
    return t < 0 ? tmp.copy(C_MID).lerp(C_IN, -t) : tmp.copy(C_MID).lerp(C_OUT, t)
  }
  const shown = (d, i) => {
    const k = d.part[i]; if (k < 0 || st.hiddenKeys.has(parts[k].key)) return false
    return Math.abs(d.dist[i]) <= st.cutoff
  }
  function restyle() {
    group.visible = st.on
    for (const [key, d] of Object.entries(st.data)) {
      const o = objs[key]; o.visible = st.on && st.layers[key]
      o.material.uniforms.size.value = st.size * (d.big ? 1.7 : 1) + (d.big ? 1 : 0); o.material.uniforms.pr.value = Math.min(2, devicePixelRatio)
      const col = o.geometry.getAttribute('color'), show = o.geometry.getAttribute('show'); const measured = !st.busy && st.modelId
      for (let i = 0; i < d.n; i++) {
        let s = 1, cc
        if (st.mode === 'photo' || !measured) { cc = tmp.setRGB(d.rgb[3 * i] / 255, d.rgb[3 * i + 1] / 255, d.rgb[3 * i + 2] / 255, THREE.SRGBColorSpace); if (d.big && st.mode === 'photo') cc = tmp.set('#1d2126') }
        else cc = colourFor(d.dist[i])
        if (measured && !shown(d, i)) s = 0
        col.setXYZ(i, cc.r, cc.g, cc.b); show.setX(i, s)
      }
      col.needsUpdate = true; show.needsUpdate = true
    }
    renderSummary(); setHover(-1, null); request()
  }

  // ---------------------------------------------------------------- summary: headline, legend, per-part table
  const q = (arr, p) => { if (!arr.length) return NaN; const s = Float64Array.from(arr).sort(); return s[Math.min(s.length - 1, Math.floor(p * (s.length - 1) + 0.5))] }
  const mm = (v, sign) => Number.isFinite(v) ? `${sign && v > 0 ? '+' : sign && v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}` : '–'
  function renderSummary() {
    const busy = st.busy || !st.modelId
    $('cloudBusy').hidden = !busy; if (busy && !$('cloudBusy').textContent) $('cloudBusy').textContent = 'Measuring…'
    if (busy) { $('cloudHead').hidden = true; return }
    $('cloudBusy').textContent = ''
    const all = [], per = parts.map(() => []); let far = 0, hiddenPart = 0
    for (const [key, d] of Object.entries(st.data)) {
      if (!st.layers[key]) continue
      for (let i = 0; i < d.n; i++) {
        const k = d.part[i]; if (k < 0) continue
        if (st.hiddenKeys.has(parts[k].key)) { hiddenPart++; continue }
        if (Math.abs(d.dist[i]) > st.cutoff) { far++; continue }
        all.push(Math.abs(d.dist[i])); per[k].push(d.dist[i])
      }
    }
    $('cloudHead').hidden = false
    $('cloudMed').textContent = mm(q(all, 0.5))
    $('cloudSub').innerHTML = all.length
      ? `median distance from point to model · 90% within <b>${mm(q(all, 0.9))} mm</b><br>${all.length.toLocaleString()} points${far ? ` · ${far.toLocaleString()} farther than ${st.cutoff} mm not shown` : ''}`
      : 'No points to show. Turn on a point set or a part.'
    $('legMin').textContent = `−${st.scale}`; $('legMax').textContent = `+${st.scale}`
    const rows = parts.map((p, k) => ({ p, v: per[k] })).filter((r) => r.v.length).sort((x, y) => q(y.v.map(Math.abs), 0.5) - q(x.v.map(Math.abs), 0.5))
    $('cloudTable').innerHTML = rows.length ? `<thead><tr><th>Part</th><th title="points nearest this part">Pts</th><th title="median distance, either side">Median</th><th title="median signed distance: + model too small, − model too big">Bias</th><th title="90% of points are within this distance">90%</th></tr></thead><tbody>` +
      rows.map(({ p, v }) => { const ab = v.map(Math.abs); const bias = q(v, 0.5); const med = q(ab, 0.5)
        return `<tr><td>${p.label}</td><td>${v.length}</td><td class="${med > 3 ? 'warn' : ''}">${mm(med)}</td><td><i class="sw" style="--c:${colourFor(bias).getStyle()}"></i>${mm(bias, true)}</td><td>${mm(q(ab, 0.9))}</td></tr>` }).join('') + '</tbody>' : ''
  }

  function renderControls() {
    $('cloudLayers').innerHTML = LAYERS.filter(([k]) => st.data[k]).map(([k, lab]) =>
      `<button class="chip${st.layers[k] ? '' : ' off'}" data-k="${k}" title="${st.data[k].desc}" style="--c:#1d2126"><i></i>${lab} <span class="mono n">${st.data[k].n.toLocaleString()}</span></button>`).join('')
    for (const b of document.querySelectorAll('#cloudMode button')) b.setAttribute('aria-selected', String(b.dataset.m === st.mode))
    $('cloudBody').hidden = !st.on
  }

  // ---------------------------------------------------------------- hover: nearest shown point on screen
  const v3 = new THREE.Vector3()
  function pick(e, camera, canvas) {
    if (!st.on || st.busy || !st.modelId) return setHover(-1, null)
    const r = canvas.getBoundingClientRect(); const mx = e.clientX - r.left, my = e.clientY - r.top
    camera.updateMatrixWorld(); let best = 12 * 12, bi = -1, bk = null
    for (const [key, d] of Object.entries(st.data)) {
      if (!st.layers[key]) continue
      for (let i = 0; i < d.n; i++) {
        if (!shown(d, i)) continue
        v3.fromArray(d.xyz, 3 * i).project(camera); if (v3.z > 1 || v3.z < -1) continue
        const dx = (v3.x + 1) / 2 * r.width - mx, dy = (1 - v3.y) / 2 * r.height - my; const dd = dx * dx + dy * dy
        if (dd < best) { best = dd; bi = i; bk = key }
      }
    }
    setHover(bi, bk)
  }
  function setHover(i, key) {
    hoverGroup.clear(); const el = $('pointInfo')
    if (i < 0 || !key) { if (el) el.textContent = ''; request(); return }
    const d = st.data[key]; const P = new THREE.Vector3().fromArray(d.xyz, 3 * i), N = new THREE.Vector3().fromArray(d.near, 3 * i)
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([P, N]), new THREE.LineBasicMaterial({ color: 0x1d2126, depthTest: false, transparent: true }))
    line.renderOrder = 12; hoverGroup.add(line)
    const lab = LAYERS.find(([k]) => k === key)[1].replace(/s$/, '').toLowerCase()
    const sig = Number.isFinite(d.sigma[i]) ? ` · ±${d.sigma[i].toFixed(2)} mm` : ''
    const v = d.dist[i]
    el.textContent = `${mm(v, true)} mm ${v >= 0 ? 'outside' : 'inside'} ${parts[d.part[i]].label.toLowerCase()} · ${lab}, ${d.views[i]} photos, ${d.rms[i].toFixed(2)} px${sig}`
    request()
  }

  // ---------------------------------------------------------------- UI wiring
  function bind() {
    $('cloudOn').addEventListener('change', (e) => { st.on = e.target.checked; renderControls(); restyle(); onChange?.() })
    $('cloudLayers').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (!b) return; st.layers[b.dataset.k] = !st.layers[b.dataset.k]; renderControls(); restyle(); onChange?.() })
    $('cloudMode').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return; st.mode = b.dataset.m; renderControls(); restyle(); onChange?.() })
    const slide = (id, key, fmt) => $(id).addEventListener('input', (e) => { st[key] = +e.target.value; $(id + 'Out').textContent = fmt(st[key]); e.target.style.setProperty('--p', `${(e.target.value - e.target.min) / (e.target.max - e.target.min) * 100}%`); restyle() })
    slide('cloudScale', 'scale', (v) => `±${v} mm`); slide('cloudCut', 'cutoff', (v) => `${v} mm`); slide('cloudSize', 'size', (v) => `${v} px`)
  }

  bind()
  return {
    load, measure, pick, restyle,
    colouring: () => st.on && st.mode === 'dist' && Object.values(st.layers).some(Boolean),
    setHiddenParts(keys) { st.hiddenKeys = new Set(keys); if (st.modelId && !st.busy) restyle() },
    reset() { st.modelId = null; st.token = {}; st.busy = false },
  }
}
