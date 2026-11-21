// Rocker model viewer. Chair frame throughout (PLAN.md): mm, +X = chair's right, +Y = forward, +Z = up, table top Z = 0.
// Photos come from tools/viewer_photos.py: upright, undistorted pinhole images with the principal point at the centre,
// camera {w, h, f, C, R} where R rows are the camera's x (right), y (down), z (forward) axes in the chair frame.
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

THREE.Object3D.DEFAULT_UP.set(0, 0, 1)
const $ = (id) => document.getElementById(id)
const CEN = new THREE.Vector3(0, 70, 540)                         // middle of the chair
const BOX = { min: [-330, -490, 0], max: [330, 630, 1090] }       // chair bounds with a margin
const AX = ['x', 'y', 'z']
const PARTS = [                                                   // name prefix -> label, colour (no purple)
  ['ROCKER', 'Rockers', '#c2410c'], ['FLEG', 'Front legs', '#2f7d4f'], ['BLEG', 'Back legs', '#0f766e'],
  ['SEAT', 'Seat', '#ca8a04'], ['ARM', 'Arms', '#2563eb'], ['CREST', 'Crest', '#0e7490'], ['SLAT', 'Slats', '#9a3412'],
]
const VIEWS = {                                                   // square-on views: camera direction, screen up
  front: { dir: [0, 1, 0], up: [0, 0, 1], axis: 1, label: 'Front', h: ['x', -1], v: ['z', 1] },
  back: { dir: [0, -1, 0], up: [0, 0, 1], axis: 1, label: 'Back', h: ['x', 1], v: ['z', 1] },
  right: { dir: [1, 0, 0], up: [0, 0, 1], axis: 0, label: 'Right side', h: ['y', 1], v: ['z', 1] },
  left: { dir: [-1, 0, 0], up: [0, 0, 1], axis: 0, label: 'Left side', h: ['y', -1], v: ['z', 1] },
  top: { dir: [0, 0, 1], up: [0, 1, 0], axis: 2, label: 'Top', h: ['x', 1], v: ['y', 1] },
}
// default depth of each rectifying plane, by axis and by which side the photo is taken from (mm)
const DEPTH = { 'x+': 235, 'x-': -235, 'y+': 495, 'y-': -165, 'z+': 600 }
const RANGE = { x: [-340, 340], y: [-480, 620], z: [0, 1090] }

const state = {
  view: 'free', models: [], modelId: null, modelMtime: 0, follow: true, opacity: 0.55, edges: true, hidden: new Set(),
  planes: { x: { on: true, pick: 'auto' }, y: { on: true, pick: 'auto' }, z: { on: false, pick: 'auto' } },
  depth: { ...DEPTH }, bgOpacity: 1, grid: false, photo: null, cams: {}, zoom: { s: 1, x: 0, y: 0 },
}

// ------------------------------------------------------------------ renderer, cameras, scene
const stage = $('stage'), frame = $('frame'), canvas = $('gl'), photoImg = $('photo')
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
renderer.setClearColor(0xf4f1ea, 1)
const scene = new THREE.Scene()
scene.add(new THREE.HemisphereLight(0xffffff, 0xb9ae98, 2.2))
const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(600, 900, 1600); scene.add(sun)
const persp = new THREE.PerspectiveCamera(35, 1, 10, 30000)
const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 30000)
const photoCam = new THREE.PerspectiveCamera(50, 1, 10, 30000)
persp.position.set(2600, 2300, 1500); persp.lookAt(CEN)
const orbit = new OrbitControls(persp, canvas); orbit.target.copy(CEN); orbit.enableDamping = true; orbit.dampingFactor = 0.12
const pan = new OrbitControls(ortho, canvas); pan.enableRotate = false; pan.screenSpacePanning = true; pan.zoomToCursor = true; pan.enabled = false
pan.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN }
pan.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN }
const camera = () => state.view === 'free' ? persp : state.view === 'photo' ? photoCam : ortho

const modelGroup = new THREE.Group(); scene.add(modelGroup)
const planeGroup = new THREE.Group(); scene.add(planeGroup)
const gridGroup = new THREE.Group(); scene.add(gridGroup)
const measureGroup = new THREE.Group(); scene.add(measureGroup)

// ------------------------------------------------------------------ model
const loader = new GLTFLoader()
const partOf = (name) => PARTS.find(([p]) => name.startsWith(p)) || ['OTHER', 'Other', '#6b7280']

async function loadModel(m, quiet) {
  const gltf = await loader.loadAsync(`/models/${encodeURIComponent(m.id)}?t=${m.mtime}`)
  modelGroup.clear()
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return
    const [key, , col] = partOf(o.name || o.parent?.name || '')
    const c = new THREE.Color(col)
    const mesh = new THREE.Mesh(o.geometry, new THREE.MeshStandardMaterial({ color: c.clone().lerp(new THREE.Color(0xffffff), 0.15), roughness: 0.75, metalness: 0, flatShading: true, transparent: true, side: THREE.DoubleSide }))
    o.updateWorldMatrix(true, false); mesh.applyMatrix4(o.matrixWorld)
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 28), new THREE.LineBasicMaterial({ color: c.clone().multiplyScalar(0.7), transparent: true }))
    edges.applyMatrix4(o.matrixWorld); edges.renderOrder = 2
    const g = new THREE.Group(); g.add(mesh, edges); g.userData = { key, mesh, edges }; modelGroup.add(g)
  })
  state.modelId = m.id; state.modelMtime = m.mtime
  applyModelStyle(); renderVersion(); request()
  if (!quiet) toast(`Showing v${m.version}`)
}

function applyModelStyle() {
  for (const g of modelGroup.children) {
    const { key, mesh, edges } = g.userData
    g.visible = !state.hidden.has(key)
    mesh.material.opacity = state.opacity; mesh.material.depthWrite = state.opacity > 0.98; mesh.visible = state.opacity > 0.01
    edges.visible = state.edges || state.opacity <= 0.01
    edges.material.opacity = state.view === 'photo' ? 1 : 0.85
  }
  request()
}

// ------------------------------------------------------------------ photos and the rectifying planes
const texLoader = new THREE.TextureLoader(); const texCache = new Map()
function photoTex(key) {
  if (!texCache.has(key)) {
    const t = texLoader.load(`photos/${key}.jpg`, request); t.colorSpace = THREE.NoColorSpace
    t.minFilter = THREE.LinearMipmapLinearFilter; t.anisotropy = 8; texCache.set(key, t)
  }
  return texCache.get(key)
}

const planeMat = (axis) => new THREE.ShaderMaterial({
  uniforms: { map: { value: null }, R: { value: new THREE.Matrix3() }, C: { value: new THREE.Vector3() }, fwh: { value: new THREE.Vector3(1, 1, 1) },
    depth: { value: 0 }, opacity: { value: 1 } },
  vertexShader: `varying vec3 vW; void main() { vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
  fragmentShader: `uniform sampler2D map; uniform mat3 R; uniform vec3 C; uniform vec3 fwh; uniform float depth; uniform float opacity; varying vec3 vW;
    void main() {
      vec3 X = vW; X.${AX[axis]} = depth;                       // the point on the rectifying plane behind this pixel
      vec3 p = R * (X - C);
      if (p.z < 1.0) discard;
      vec2 uv = vec2(fwh.x * p.x / p.z + 0.5 * fwh.y, fwh.x * p.y / p.z + 0.5 * fwh.z);
      if (uv.x < 0.0 || uv.y < 0.0 || uv.x > fwh.y || uv.y > fwh.z) discard;
      gl_FragColor = vec4(texture2D(map, vec2(uv.x / fwh.y, 1.0 - uv.y / fwh.z)).rgb, opacity);
    }`,
  transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide,
})
const planes = [0, 1, 2].map((axis) => {
  const m = new THREE.Mesh(new THREE.BufferGeometry(), planeMat(axis)); m.renderOrder = -10; m.frustumCulled = false; planeGroup.add(m); return m
})

// rank photos for each axis and side: most square-on first, chair fully in frame
function candidates(axis, sign) {
  const out = []
  for (const [key, c] of Object.entries(state.cams)) {
    const d = new THREE.Vector3(...c.C).sub(CEN).normalize(); const cos = d.getComponent(axis) * sign
    if (cos < 0.6) continue
    out.push({ key, deg: Math.acos(Math.min(1, cos)) * 180 / Math.PI, inFrame: chairInFrame(c) })
  }
  return out.sort((a, b) => (b.inFrame - a.inFrame) || a.deg - b.deg)
}
function chairInFrame(c) {
  let n = 0
  for (const x of [BOX.min[0] + 30, BOX.max[0] - 30]) for (const y of [BOX.min[1] + 10, BOX.max[1] - 10]) for (const z of [0, BOX.max[2] - 10]) {
    const p = project(c, [x, y, z]); if (p && p[0] >= 0 && p[1] >= 0 && p[0] <= c.w && p[1] <= c.h) n++
  }
  return n / 8
}
function project(c, X) {
  const d = [X[0] - c.C[0], X[1] - c.C[1], X[2] - c.C[2]]
  const p = c.R.map((r) => r[0] * d[0] + r[1] * d[1] + r[2] * d[2]); if (p[2] <= 0) return null
  return [c.f * p[0] / p[2] + c.w / 2, c.f * p[1] / p[2] + c.h / 2]
}

// which side the camera is looking from, per axis; the plane is drawn on the far side, the photo comes from the near side
function sideOf(axis) {
  if (axis === 2) return 1
  const cam = camera(); const v = state.view
  if (VIEWS[v]) return VIEWS[v].dir[axis] !== 0 ? Math.sign(VIEWS[v].dir[axis]) : 1
  return Math.sign(cam.position.getComponent(axis) - CEN.getComponent(axis)) || 1
}
const sideKey = (axis, s) => `${AX[axis]}${s > 0 ? '+' : '-'}`

function planePhoto(axis) {
  const s = sideOf(axis); const pick = state.planes[AX[axis]].pick
  if (pick !== 'auto' && pick.side === s) return pick.key
  return candidates(axis, s)[0]?.key
}

function updatePlanes() {
  const showPlanes = state.view !== 'photo'
  planes.forEach((m, axis) => {
    const p = state.planes[AX[axis]]; const s = sideOf(axis); const key = planePhoto(axis)
    m.visible = showPlanes && p.on && !!key && !(axis === 2 && state.view === 'free' && persp.position.z < 0)
    if (!m.visible) return
    const c = state.cams[key]; const u = m.material.uniforms
    u.map.value = photoTex(key); u.R.value.set(...c.R[0], ...c.R[1], ...c.R[2]); u.C.value.set(...c.C); u.fwh.value.set(c.f, c.w, c.h)
    u.depth.value = state.depth[sideKey(axis, s)]; u.opacity.value = state.bgOpacity
    const at = axis === 2 ? -2 : (s > 0 ? BOX.min[axis] - 40 : BOX.max[axis] + 40)     // far side of the chair
    m.geometry.dispose(); m.geometry = wallGeometry(axis, at)
  })
  updateGrid(); request()
}

function wallGeometry(axis, at) {
  const [a, b] = [0, 1, 2].filter((i) => i !== axis); const pad = 220
  const corners = [[BOX.min[a] - pad, BOX.min[b] - pad], [BOX.max[a] + pad, BOX.min[b] - pad], [BOX.max[a] + pad, BOX.max[b] + pad], [BOX.min[a] - pad, BOX.max[b] + pad]]
  const pos = []
  for (const i of [0, 1, 2, 0, 2, 3]) { const v = [0, 0, 0]; v[axis] = at; v[a] = corners[i][0]; v[b] = corners[i][1]; pos.push(...v) }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); return g
}

// ------------------------------------------------------------------ 50 mm grid (square-on views and the 3D floor)
function updateGrid() {
  gridGroup.clear(); if (!state.grid || state.view === 'photo') return
  const axis = VIEWS[state.view]?.axis ?? 2
  const [a, b] = [0, 1, 2].filter((i) => i !== axis)
  const at = axis === 2 ? (state.view === 'free' ? 0 : -1) : (sideOf(axis) > 0 ? BOX.min[axis] - 30 : BOX.max[axis] + 30)
  const minor = [], major = []
  const lo = (i) => Math.floor((BOX.min[i] - 200) / 50) * 50, hi = (i) => Math.ceil((BOX.max[i] + 200) / 50) * 50
  const push = (arr, p, q) => { for (const P of [p, q]) { const v = [0, 0, 0]; v[axis] = at; v[a] = P[0]; v[b] = P[1]; arr.push(...v) } }
  for (let u = lo(a); u <= hi(a); u += 50) push(u % 100 === 0 ? major : minor, [u, lo(b)], [u, hi(b)])
  for (let w = lo(b); w <= hi(b); w += 50) push(w % 100 === 0 ? major : minor, [lo(a), w], [hi(a), w])
  for (const [arr, op] of [[minor, 0.12], [major, 0.26]]) {
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3))
    const l = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x1d2126, transparent: true, opacity: op, depthTest: state.view === 'free', depthWrite: false }))
    l.renderOrder = -5; gridGroup.add(l)
  }
}

// ------------------------------------------------------------------ views
function setView(v) {
  state.view = v
  for (const b of document.querySelectorAll('#views button')) b.setAttribute('aria-selected', String(b.dataset.view === v))
  $('photoBox').hidden = v !== 'photo'; $('backBlock').style.display = v === 'photo' ? 'none' : ''
  stage.classList.toggle('photo', v === 'photo'); photoImg.hidden = v !== 'photo'
  renderer.setClearColor(0xf4f1ea, v === 'photo' ? 0 : 1)
  orbit.enabled = v === 'free'; pan.enabled = !!VIEWS[v]
  state.zoom = { s: 1, x: 0, y: 0 }
  if (VIEWS[v]) {
    const d = new THREE.Vector3(...VIEWS[v].dir)
    ortho.up.set(...VIEWS[v].up); ortho.position.copy(CEN).addScaledVector(d, 5000); ortho.lookAt(CEN)
    pan.target.copy(CEN); ortho.zoom = 1
  }
  if (v === 'photo' && !state.photo) state.photo = nearestPhoto()
  if (v === 'photo') showPhoto(state.photo)
  $('readout').textContent = ''; clearMeasure(); layout(); applyModelStyle(); lastSides = ''; syncPlaneSides(); hud()
}

function nearestPhoto() {
  const d = persp.position.clone().sub(CEN).normalize(); let best = null, bd = -2
  for (const [k, c] of Object.entries(state.cams)) { const e = new THREE.Vector3(...c.C).sub(CEN).normalize().dot(d); if (e > bd) { bd = e; best = k } }
  return best
}

function showPhoto(key) {
  if (!key) return
  state.photo = key; const c = state.cams[key]; $('photoSel').value = key
  photoImg.src = `photos/${key}.jpg`
  photoCam.fov = 2 * Math.atan(c.h / 2 / c.f) * 180 / Math.PI; photoCam.aspect = c.w / c.h
  const x = new THREE.Vector3(...c.R[0]), y = new THREE.Vector3(...c.R[1]).negate(), z = new THREE.Vector3(...c.R[2]).negate()
  photoCam.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z)); photoCam.position.set(...c.C)
  photoCam.updateProjectionMatrix(); state.zoom = { s: 1, x: 0, y: 0 }; layout(); hud()
}

// stage sizing: photo mode letterboxes the frame to the photo's aspect and lets it be zoomed/panned as one piece
function layout() {
  const W = stage.clientWidth, H = stage.clientHeight
  let fw = W, fh = H, fx = 0, fy = 0
  if (state.view === 'photo' && state.photo) {
    const c = state.cams[state.photo]; const pad = 20; const s = Math.min((W - pad * 2) / c.w, (H - pad * 2) / c.h)
    fw = Math.round(c.w * s); fh = Math.round(c.h * s); fx = Math.round((W - fw) / 2); fy = Math.round((H - fh) / 2)
  }
  const z = state.zoom
  frame.style.width = fw + 'px'; frame.style.height = fh + 'px'; frame.style.inset = 'auto'; frame.style.left = fx + 'px'; frame.style.top = fy + 'px'
  frame.style.transform = `translate(${z.x}px, ${z.y}px) scale(${z.s})`
  renderer.setPixelRatio(Math.min(3, devicePixelRatio * (state.view === 'photo' ? Math.min(z.s, 2.5) : 1)))
  renderer.setSize(fw, fh, false)
  persp.aspect = fw / fh; persp.updateProjectionMatrix()
  const asp = fw / fh; const span = Math.max(1300, 1350 / asp)
  ortho.left = -span / 2 * asp; ortho.right = span / 2 * asp; ortho.top = span / 2; ortho.bottom = -span / 2; ortho.updateProjectionMatrix()
  request()
}

// zoom/pan the photo frame (photo mode only)
stage.addEventListener('wheel', (e) => {
  if (state.view !== 'photo') return
  e.preventDefault(); const r = stage.getBoundingClientRect(); const z = state.zoom
  const k = Math.exp(-e.deltaY * 0.0015); const s = Math.min(12, Math.max(1, z.s * k)); const f = s / z.s
  const fx = parseFloat(frame.style.left), fy = parseFloat(frame.style.top)
  const mx = e.clientX - r.left - fx, my = e.clientY - r.top - fy
  z.x = mx - (mx - z.x) * f; z.y = my - (my - z.y) * f; z.s = s; if (s === 1) { z.x = 0; z.y = 0 }
  layout()
}, { passive: false })
let drag = null
stage.addEventListener('pointerdown', (e) => {
  down = { x: e.clientX, y: e.clientY }
  if (state.view === 'photo') { drag = { x: e.clientX, y: e.clientY, zx: state.zoom.x, zy: state.zoom.y }; stage.setPointerCapture(e.pointerId) }
})
stage.addEventListener('pointermove', (e) => {
  if (drag) { state.zoom.x = drag.zx + e.clientX - drag.x; state.zoom.y = drag.zy + e.clientY - drag.y; layout() }
  readout(e)
})
stage.addEventListener('pointerup', (e) => {
  drag = null
  if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 4 && VIEWS[state.view]) measureClick(e)
  down = null
})
let down = null

// ------------------------------------------------------------------ readout and measuring (square-on views)
function worldAt(e) {
  ortho.updateMatrixWorld()
  const r = canvas.getBoundingClientRect()
  const ndc = new THREE.Vector3(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1, 0)
  return ndc.unproject(ortho)
}
const fmt = (mm) => `${mm.toFixed(1)}`
const inch = (mm) => { const t = Math.round(Math.abs(mm) / 25.4 * 32); const w = Math.floor(t / 32); let n = t % 32, d = 32; while (n && n % 2 === 0) { n /= 2; d /= 2 } return `${mm < 0 ? '−' : ''}${w}${n ? ` ${n}/${d}` : ''}″` }
function readout(e) {
  const v = VIEWS[state.view]; if (!v) { $('readout').textContent = ''; return }
  const p = worldAt(e); const [a, b] = [0, 1, 2].filter((i) => i !== v.axis)
  $('readout').textContent = `${AX[a]} ${fmt(p.getComponent(a))}   ${AX[b]} ${fmt(p.getComponent(b))} mm`
}
let mA = null
function measureClick(e) {
  const v = VIEWS[state.view]; const p = worldAt(e); p.setComponent(v.axis, CEN.getComponent(v.axis) + v.dir[v.axis] * 800)
  if (!mA || measureGroup.children.length > 1) { clearMeasure(); mA = p; dot(p); return }
  dot(p); const g = new THREE.BufferGeometry().setFromPoints([mA, p])
  const l = new THREE.Line(g, new THREE.LineBasicMaterial({ color: 0xc2410c, depthTest: false, transparent: true })); l.renderOrder = 10; measureGroup.add(l)
  const [a, b] = [0, 1, 2].filter((i) => i !== v.axis); const da = p.getComponent(a) - mA.getComponent(a), db = p.getComponent(b) - mA.getComponent(b)
  const d = Math.hypot(da, db)
  $('measure').textContent = `${fmt(d)} mm  ${inch(d)}   (${AX[a]} ${fmt(Math.abs(da))}, ${AX[b]} ${fmt(Math.abs(db))})`
  request()
}
function dot(p) {
  const m = new THREE.Mesh(new THREE.CircleGeometry(5 / ortho.zoom, 20), new THREE.MeshBasicMaterial({ color: 0xc2410c, depthTest: false, transparent: true }))
  m.position.copy(p); m.quaternion.copy(ortho.quaternion); m.renderOrder = 10; measureGroup.add(m); request()
}
function clearMeasure() { measureGroup.clear(); mA = null; $('measure').textContent = ''; request() }

// ------------------------------------------------------------------ rail UI
function hud() {
  const v = state.view; let h = ''
  if (v === 'free') h = `<span class="big">3D</span><span class="lab hint">drag to turn · scroll to zoom</span>`
  else if (VIEWS[v]) {
    const ax = VIEWS[v].axis; const on = state.planes[AX[ax]].on; const key = on && planePhoto(ax)
    h = `<span class="big">${VIEWS[v].label}</span><span class="lab hint">square-on · click two points to measure</span>` +
      (key ? `<span class="lab">behind: ${key.slice(4)} flattened at ${AX[ax]} = ${Math.round(state.depth[sideKey(ax, sideOf(ax))])} mm</span>` : '')
  } else if (state.photo) h = `<span class="big">${state.photo.replace('_', ' ')}</span><span class="lab">${describe(state.cams[state.photo])}</span>`
  $('hudTop').innerHTML = h
}
function describe(c) {
  const d = new THREE.Vector3(...c.C).sub(CEN); const az = Math.atan2(d.x, d.y) * 180 / Math.PI; const el = Math.atan2(d.z, Math.hypot(d.x, d.y)) * 180 / Math.PI
  const side = Math.abs(az) < 22 ? 'front' : Math.abs(az) > 158 ? 'back' : Math.abs(az) < 68 ? (az > 0 ? 'front right' : 'front left') : Math.abs(az) < 112 ? (az > 0 ? 'right side' : 'left side') : (az > 0 ? 'back right' : 'back left')
  return `${side} · ${el > 55 ? 'from above' : `${Math.round(el)}° up`} · ${(d.length() / 1000).toFixed(1)} m away`
}

function renderVersion() {
  const m = state.models.find((x) => x.id === state.modelId); if (!m) return
  const latest = state.models[0]?.id === m.id
  $('verNum').textContent = `v${m.version}`
  $('verMeta').innerHTML = `${latest ? '<b>newest</b> · ' : ''}saved ${ago(m.mtime)}<br>${m.dir === 'repo' ? 'committed copy' : 'working copy'} · ${(m.size / 1024).toFixed(0)} KB`
  $('verSel').value = m.id
}
const ago = (t) => { const s = (Date.now() - t) / 1000; return s < 60 ? 'just now' : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : new Date(t).toLocaleDateString() }

const stamp = (t) => { const d = new Date(t); return d.toDateString() === new Date().toDateString() ? d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : d.toLocaleDateString([], { month: 'short', day: 'numeric' }) }
function renderVersions() {
  const sel = $('verSel'); const cur = state.modelId
  sel.innerHTML = state.models.map((m) => `<option value="${m.id}">v${m.version} · ${stamp(m.mtime)}</option>`).join('')
  if (cur) sel.value = cur
}

function renderParts() {
  $('parts').innerHTML = PARTS.map(([k, label, col]) => `<button class="chip${state.hidden.has(k) ? ' off' : ''}" data-k="${k}" style="--c:${col}"><i></i>${label}</button>`).join('')
}

function renderPlanes() {
  const names = { x: ['Side', 'X plane'], y: ['Front / back', 'Y plane'], z: ['Top', 'Z plane'] }
  $('planes').innerHTML = [0, 1, 2].map((axis) => {
    const a = AX[axis]; const p = state.planes[a]; const s = sideOf(axis); const sk = sideKey(axis, s); const cands = candidates(axis, s).slice(0, 10)
    const cur = p.pick !== 'auto' && p.pick.side === s ? p.pick.key : 'auto'
    const opts = [`<option value="auto">Best: ${cands[0] ? `${cands[0].key.slice(4)} · ${Math.round(cands[0].deg)}° off square` : 'none'}</option>`]
      .concat(cands.map((c) => `<option value="${c.key}">${c.key.slice(4)} · ${Math.round(c.deg)}° off square${c.inFrame < 1 ? ' · chair cut off' : ''}</option>`)).join('')
    const [lo, hi] = RANGE[a]; const d = state.depth[sk]
    return `<div class="plane${p.on ? '' : ' off'}" data-a="${a}">
      <div class="plane-head"><span class="axis">${names[a][0]}<small>${names[a][1]}${axis === 2 ? '' : s > 0 ? (axis === 0 ? ' · right photo' : ' · front photo') : (axis === 0 ? ' · left photo' : ' · back photo')}</small></span>
        <label class="switch"><input type="checkbox" class="pon" ${p.on ? 'checked' : ''}><span></span></label></div>
      <div class="body">
        <select class="sel ppick" aria-label="Photo for the ${a} plane">${opts}</select>
        <div class="slider"><label>Depth</label><input type="range" class="pdepth" min="${lo}" max="${hi}" step="1" value="${d}" style="--p:${(d - lo) / (hi - lo) * 100}%">
          <output class="mono">${a} ${Math.round(d)}</output></div>
      </div></div>`
  }).join('')
  for (const el of $('planes').querySelectorAll('.ppick')) {
    const a = el.closest('.plane').dataset.a; const p = state.planes[a]; const axis = AX.indexOf(a)
    el.value = p.pick !== 'auto' && p.pick.side === sideOf(axis) ? p.pick.key : 'auto'
  }
}
let lastSides = ''
function syncPlaneSides() {                       // in 3D the near side changes as you orbit: refresh labels/photos
  const s = [0, 1].map(sideOf).join(); if (s !== lastSides) { lastSides = s; renderPlanes(); updatePlanes() }
}

function renderPhotoList() {
  const keys = Object.keys(state.cams).sort()
  $('photoSel').innerHTML = keys.map((k) => `<option value="${k}">${k.slice(4)} · ${describe(state.cams[k])}</option>`).join('')
}

function setSliderFill(el) { el.style.setProperty('--p', `${(el.value - el.min) / (el.max - el.min) * 100}%`) }

function bindUI() {
  $('views').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setView(b.dataset.view) })
  $('opacity').addEventListener('input', (e) => { state.opacity = e.target.value / 100; $('opacityOut').textContent = `${e.target.value}%`; setSliderFill(e.target); applyModelStyle() })
  $('bgOpacity').addEventListener('input', (e) => { state.bgOpacity = e.target.value / 100; $('bgOpacityOut').textContent = `${e.target.value}%`; setSliderFill(e.target); updatePlanes() })
  $('edges').addEventListener('change', (e) => { state.edges = e.target.checked; applyModelStyle() })
  $('grid').addEventListener('change', (e) => { state.grid = e.target.checked; updatePlanes() })
  $('follow').addEventListener('change', (e) => { state.follow = e.target.checked; if (state.follow) poll() })
  $('verSel').addEventListener('change', (e) => {
    const m = state.models.find((x) => x.id === e.target.value); if (!m) return
    if (m.id !== state.models[0].id) { state.follow = false; $('follow').checked = false }
    loadModel(m)
  })
  $('parts').addEventListener('click', (e) => { const b = e.target.closest('.chip'); if (!b) return; const k = b.dataset.k; state.hidden.has(k) ? state.hidden.delete(k) : state.hidden.add(k); renderParts(); applyModelStyle() })
  $('planes').addEventListener('input', (e) => {
    const row = e.target.closest('.plane'); if (!row) return; const a = row.dataset.a; const axis = AX.indexOf(a); const p = state.planes[a]
    if (e.target.classList.contains('pon')) { p.on = e.target.checked; row.classList.toggle('off', !p.on) }
    if (e.target.classList.contains('ppick')) p.pick = e.target.value === 'auto' ? 'auto' : { key: e.target.value, side: sideOf(axis) }
    if (e.target.classList.contains('pdepth')) { state.depth[sideKey(axis, sideOf(axis))] = +e.target.value; row.querySelector('output').textContent = `${a} ${e.target.value}`; setSliderFill(e.target) }
    updatePlanes(); hud()
  })
  $('photoSel').addEventListener('change', (e) => showPhoto(e.target.value))
  const step = (k) => { const keys = Object.keys(state.cams).sort(); const i = keys.indexOf(state.photo); showPhoto(keys[(i + k + keys.length) % keys.length]) }
  $('prevPhoto').onclick = () => step(-1); $('nextPhoto').onclick = () => step(1)
  addEventListener('keydown', (e) => {
    if (e.target.matches('input, select')) return
    const map = { 1: 'free', 2: 'front', 3: 'right', 4: 'left', 5: 'back', 6: 'top', p: 'photo', P: 'photo' }
    if (map[e.key]) setView(map[e.key])
    else if (e.key === '[' && state.view === 'photo') step(-1)
    else if (e.key === ']' && state.view === 'photo') step(1)
    else if (e.key === 'e' || e.key === 'E') { state.edges = !state.edges; $('edges').checked = state.edges; applyModelStyle() }
    else if (e.key === 'Escape') clearMeasure()
  })
  for (const el of document.querySelectorAll('input[type=range]')) setSliderFill(el)
  new ResizeObserver(layout).observe(stage)
}

// ------------------------------------------------------------------ newest model polling
async function poll() {
  try {
    const r = await fetch('/api/models', { cache: 'no-store' }); const j = await r.json()
    state.models = j.models; renderVersions()
    if (!j.models.length) { showState('No model yet', 'No parts/model_vN.glb was found in the model folders.'); return }
    showState()
    const cur = j.models.find((m) => m.id === state.modelId)
    if (state.follow && (j.latest !== state.modelId || (cur && cur.mtime !== state.modelMtime))) await loadModel(j.models[0], !state.modelId)
    else renderVersion()
  } catch (e) { if (!state.modelId) showState('Can’t reach the viewer server', String(e.message || e)) }
}
function showState(title, text) { const el = $('state'); el.hidden = !title; if (title) el.innerHTML = `<div><b>${title}</b>${text}</div>` }
let toastT
function toast(t) { const el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => { el.hidden = true }, 2600) }

// ------------------------------------------------------------------ render loop (on demand; damping keeps it going briefly)
let needs = true
function request() { needs = true }
orbit.addEventListener('change', () => { request(); syncPlaneSides() }); pan.addEventListener('change', request)
function tick() {
  requestAnimationFrame(tick)
  if (orbit.enabled) orbit.update(); if (pan.enabled) pan.update()
  if (!needs) return; needs = false
  renderer.render(scene, camera())
}

async function main() {
  bindUI(); renderParts()
  state.cams = await (await fetch('photos/cameras.json')).json()
  renderPhotoList(); renderPlanes(); setView('free')
  await poll(); setInterval(poll, 5000); setInterval(renderVersion, 30000)
  tick()
}
main().catch((e) => showState('Viewer failed to start', String(e.message || e)))
