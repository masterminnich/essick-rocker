// The 3D chair for the review app: a solid wood chair on a floor with a soft shadow, drag to turn.
// Chair frame (PLAN.md): mm, +X chair's right, +Y forward, +Z up, table top Z = 0.
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { toCreasedNormals } from 'three/addons/utils/BufferGeometryUtils.js'

THREE.Object3D.DEFAULT_UP.set(0, 0, 1)
export const CEN = new THREE.Vector3(0, 60, 545)
const PAPER = 0xf4f1ea
const WOOD = new THREE.Color('#7b5136'), WOOD_EDGE = new THREE.Color('#2b1d14')
const GHOST = new THREE.Color('#d3cbbb'), GHOST_EDGE = new THREE.Color('#9d9484')
const JOINT = new THREE.Color('#b7791f')
const PHOTO_FILL = new THREE.Color('#0f766e'), PHOTO_EDGE = new THREE.Color('#e9fffb')

export const VIEWS = {                     // direction from the chair to the camera
  front: [0, 1, 0.08], side: [1, 0, 0.08], back: [0, -1, 0.12], top: [0.0001, 0.12, 1], corner: [0.95, 1.05, 0.5],
}

let renderer, scene, cam, orbit, canvas, host
const photoCam = new THREE.PerspectiveCamera(50, 1, 10, 30000)
const model = new THREE.Group()
const parts = new Map()                    // name -> { group, mesh, edges, box }
const state = { mode: 'solid', selected: null, photo: null, needs: true, anim: null, onFrame: () => {} }
const ray = new THREE.Raycaster()

export function init(canvasEl, hostEl, { onFrame } = {}) {
  canvas = canvasEl; host = hostEl; state.onFrame = onFrame || state.onFrame
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true })
  renderer.setClearColor(PAPER, 1); renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 1.05
  scene = new THREE.Scene()
  scene.add(new THREE.HemisphereLight(0xfffaf0, 0x8a7a62, 1.5))
  const key = new THREE.DirectionalLight(0xfff4e6, 2.4); key.position.set(900, 1400, 2600); key.target.position.copy(CEN)
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.blurSamples = 16; key.shadow.bias = -0.0004
  Object.assign(key.shadow.camera, { left: -1100, right: 1100, top: 1100, bottom: -1100, near: 500, far: 6000 })
  scene.add(key, key.target)
  const fill = new THREE.DirectionalLight(0xffffff, 0.7); fill.position.set(-1600, -600, 900); scene.add(fill)
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), new THREE.ShadowMaterial({ color: 0x3c2814, opacity: 0.16 }))
  floor.receiveShadow = true; floor.name = 'floor'; scene.add(floor)
  scene.add(blob())
  scene.add(model)
  cam = new THREE.PerspectiveCamera(30, 1, 20, 40000)
  orbit = new OrbitControls(cam, canvas); orbit.enableDamping = true; orbit.dampingFactor = 0.12; orbit.target.copy(CEN)
  orbit.minDistance = 250; orbit.maxDistance = 9000; orbit.maxPolarAngle = Math.PI * 0.62
  orbit.addEventListener('change', request)
  orbit.addEventListener('start', () => { state.anim = null })
  new ResizeObserver(resize).observe(host); resize()
  goView('corner', true)
  tick()
}

function blob() {                          // a soft contact shadow under the chair, so it never floats
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d')
  const r = g.createRadialGradient(128, 128, 10, 128, 128, 128); r.addColorStop(0, 'rgba(60,40,20,0.30)'); r.addColorStop(1, 'rgba(60,40,20,0)')
  g.fillStyle = r; g.fillRect(0, 0, 256, 256)
  const m = new THREE.Mesh(new THREE.PlaneGeometry(900, 1500), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }))
  m.position.set(0, 70, 0.5); m.name = 'floor'; return m
}

export function resize() {
  const W = host.clientWidth, H = host.clientHeight; if (!W || !H) return
  renderer.setPixelRatio(Math.min(2, devicePixelRatio)); renderer.setSize(W, H, false)
  cam.aspect = W / H; cam.updateProjectionMatrix(); request()
}

// ------------------------------------------------------------------ model
const PART_NAMES = {
  ROCKER: 'rocker', FLEG: 'front leg', BLEG: 'back leg', ARM: 'arm', SEAT: 'Seat', CREST: 'Crest rail',
  SLAT_C: 'Centre slat', SLAT_L: 'Left slat', SLAT_R: 'Right slat',
}
export function partName(n) {
  if (n.startsWith('DOMINO_')) return `Domino joint, ${n.endsWith('L') ? 'left' : 'right'} side`
  if (PART_NAMES[n]) return PART_NAMES[n]
  const [k, s] = n.split('_'); const side = s === 'L' ? 'Left' : s === 'R' ? 'Right' : ''
  return `${side} ${PART_NAMES[k] || k.toLowerCase()}`.trim()
}

export async function loadModel(url) {
  const gltf = await new GLTFLoader().loadAsync(url)
  model.clear(); parts.clear()
  gltf.scene.updateMatrixWorld(true)
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return
    const name = o.name || o.parent?.name || 'PART'
    let geo = o.geometry.clone(); geo.applyMatrix4(o.matrixWorld)
    try { geo = toCreasedNormals(geo, THREE.MathUtils.degToRad(32)) } catch { geo.computeVertexNormals() }
    const mat = new THREE.MeshStandardMaterial({ color: WOOD.clone(), roughness: 0.62, metalness: 0, side: THREE.FrontSide })
    const mesh = new THREE.Mesh(geo, mat); mesh.castShadow = true; mesh.receiveShadow = true; mesh.name = name
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 35).applyMatrix4(o.matrixWorld),
      new THREE.LineBasicMaterial({ color: WOOD_EDGE.clone(), transparent: true, opacity: 0.45 }))
    edges.renderOrder = 2
    const g = new THREE.Group(); g.name = name; g.add(mesh, edges); model.add(g)
    geo.computeBoundingBox()
    parts.set(name, { group: g, mesh, edges, box: geo.boundingBox.clone() })
  })
  style(); request()
  return [...parts.keys()]
}

export function setMode(m) { state.mode = m; style() }
export function select(name) { state.selected = name; style() }
export const selected = () => state.selected

function style() {
  const photo = !!state.photo
  for (const [name, p] of parts) {
    const m = p.mesh.material, e = p.edges.material
    const isJoint = name.startsWith('DOMINO')
    const sel = state.selected, on = !sel || sel === name
    let fill = WOOD, edge = WOOD_EDGE, op = 1, eop = 0.45
    if (photo) { fill = PHOTO_FILL; edge = PHOTO_EDGE; op = 0.5; eop = 0.9 }
    else if (state.mode === 'ghost') { fill = isJoint ? JOINT : on && sel ? WOOD : GHOST; edge = isJoint ? JOINT : WOOD_EDGE; op = isJoint || (sel && on) ? 1 : 0.2; eop = isJoint ? 0.8 : 0.55 }
    else if (!on) { fill = GHOST; edge = GHOST_EDGE; eop = 0.35 }
    m.color.copy(fill); m.opacity = op; m.transparent = op < 1; m.depthWrite = op >= 1
    e.color.copy(edge); e.opacity = eop
    p.mesh.castShadow = op >= 1 && !photo
    p.group.renderOrder = op < 1 ? 1 : 0
  }
  request()
}

// ------------------------------------------------------------------ picking
export function pick(clientX, clientY) {
  const r = canvas.getBoundingClientRect()
  const ndc = new THREE.Vector2(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1)
  ray.setFromCamera(ndc, camera())
  const hit = ray.intersectObjects([...parts.values()].map((p) => p.mesh), false)[0]
  return hit ? { part: hit.object.name, point: hit.point.toArray() } : null
}

// ------------------------------------------------------------------ camera
export const camera = () => (state.photo ? photoCam : cam)
function fitDistance(radius) {
  const v = THREE.MathUtils.degToRad(cam.fov) / 2; const h = Math.atan(Math.tan(v) * cam.aspect)
  return radius / Math.sin(Math.min(v, h))
}
function animateTo(pos, target, instant) {
  if (instant) { cam.position.copy(pos); orbit.target.copy(target); orbit.update(); request(); return }
  state.anim = { t0: performance.now(), dur: 650, p0: cam.position.clone(), q0: orbit.target.clone(), p1: pos, q1: target }
  request()
}
export function goView(name, instant) {
  const d = new THREE.Vector3(...VIEWS[name]).normalize()
  const r = name === 'top' ? 760 : name === 'corner' ? 760 : 720
  const target = CEN.clone(); if (name === 'corner') target.z -= 10
  animateTo(target.clone().addScaledVector(d, fitDistance(r)), target, instant)
}
export function lookAtSpan(points, dir, { pad = 1.25, add = 110, min = 260, lift = 0 } = {}) {
  const box = new THREE.Box3().setFromPoints(points.map((p) => new THREE.Vector3(...p)))
  const c = box.getCenter(new THREE.Vector3()); const r = Math.max(min, box.getSize(new THREE.Vector3()).length() / 2 * pad + add)
  const d = new THREE.Vector3(...dir).normalize(), dist = fitDistance(r)
  if (lift) {                       // aim above the span so it sits lower on screen, clear of the text at the top
    const up = new THREE.Vector3(0, 0, 1).addScaledVector(d, -d.z).normalize()
    c.addScaledVector(up, dist * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2) * lift)
  }
  animateTo(c.clone().addScaledVector(d, dist), c)
}
export function framePart(name, dirHint, lift = 0) {
  const p = parts.get(name); if (!p) return
  const d = dirHint || cam.position.clone().sub(orbit.target).normalize().toArray()
  lookAtSpan([p.box.min.toArray(), p.box.max.toArray()], d, { pad: 1.35, add: 0, min: 240, lift })
}
export function partCenter(name) { const p = parts.get(name); return p ? p.box.getCenter(new THREE.Vector3()).toArray() : CEN.toArray() }
export const getView = () => ({ p: cam.position.toArray(), t: orbit.target.toArray() })
export function setView(v, instant) { if (v) animateTo(new THREE.Vector3(...v.p), new THREE.Vector3(...v.t), instant) }
export const viewDir = () => cam.position.clone().sub(orbit.target).normalize().toArray()
export function enableOrbit(on) { orbit.enabled = on }

// ------------------------------------------------------------------ through a photo's own camera
// Photos (tools/viewer_photos.py): upright pinhole images, principal point at the centre; camera {w, h, f, C, R}, R rows = the
// camera's x (right), y (down), z (forward) in the chair frame.
export function setPhoto(c) {
  state.photo = c || null
  if (c) {
    photoCam.fov = 2 * Math.atan(c.h / 2 / c.f) * 180 / Math.PI; photoCam.aspect = c.w / c.h
    const x = new THREE.Vector3(...c.R[0]), y = new THREE.Vector3(...c.R[1]).negate(), z = new THREE.Vector3(...c.R[2]).negate()
    photoCam.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z)); photoCam.position.set(...c.C); photoCam.updateProjectionMatrix()
  }
  renderer.setClearColor(PAPER, c ? 0 : 1); orbit.enabled = !c
  scene.traverse((o) => { if (o.name === 'floor') o.visible = !c })
  style(); request()
}

// ------------------------------------------------------------------ projecting points for the overlays
const _v = new THREE.Vector3()
export function project(p) {
  const c = camera(); _v.set(p[0], p[1], p[2]).project(c)
  const W = canvas.clientWidth, H = canvas.clientHeight
  return { x: (_v.x + 1) / 2 * W, y: (1 - _v.y) / 2 * H, behind: _v.z > 1 }
}
export const size = () => ({ w: canvas.clientWidth, h: canvas.clientHeight })

// A still picture of the chair from a direction, for the printed sheet: returns { url, project } for that view.
export function still(w, h, points, dir) {
  const box = new THREE.Box3().setFromPoints(points.map((p) => new THREE.Vector3(...p)))
  const c = box.getCenter(new THREE.Vector3()); const r = Math.max(260, box.getSize(new THREE.Vector3()).length() / 2 * 1.25 + 110)
  const k = new THREE.PerspectiveCamera(30, w / h, 20, 40000); k.up.set(0, 0, 1)
  const v = THREE.MathUtils.degToRad(15); const hh = Math.atan(Math.tan(v) * k.aspect)
  k.position.copy(c).addScaledVector(new THREE.Vector3(...dir).normalize(), r / Math.sin(Math.min(v, hh))); k.lookAt(c); k.updateMatrixWorld(); k.updateProjectionMatrix()
  const pr = renderer.getPixelRatio(); const W0 = canvas.width, H0 = canvas.height
  renderer.setPixelRatio(1); renderer.setSize(w * 2, h * 2, false); renderer.render(scene, k)
  const url = canvas.toDataURL('image/jpeg', 0.85)
  renderer.setPixelRatio(pr); renderer.setSize(W0 / pr, H0 / pr, false); request()
  const proj = (p) => { const q = new THREE.Vector3(...p).project(k); return { x: (q.x + 1) / 2 * w, y: (1 - q.y) / 2 * h } }
  return { url, project: proj }
}

// ------------------------------------------------------------------ render loop, on demand
export function request() { state.needs = true }
function tick() {
  requestAnimationFrame(tick)
  if (state.anim) {
    const a = state.anim; let t = Math.min(1, (performance.now() - a.t0) / a.dur); const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
    cam.position.lerpVectors(a.p0, a.p1, e); orbit.target.lerpVectors(a.q0, a.q1, e); if (t >= 1) state.anim = null
    state.needs = true
  }
  if (orbit.enabled) orbit.update()
  if (!state.needs) return; state.needs = false
  renderer.render(scene, camera())
  state.onFrame()
}
