// Saving for the review app. Everything Joe's reviewer gives (answers, pins, notes, photos) goes through this one module.
// Today it saves to the device only (IndexedDB) and exports one file. Set REMOTE_URL to a Worker (see viewer/README.md,
// "Saving") and every record is also sent there; records not yet sent are retried on the next load.
export const REMOTE_URL = null          // e.g. 'https://essick-rocker-notes.<account>.workers.dev'

const DB = 'essick-rocker-review', STORE = 'records', PHOTOS = 'photos'
let dbp = null
function db() {
  if (!dbp) dbp = new Promise((res, rej) => {
    const r = indexedDB.open(DB, 1)
    r.onupgradeneeded = () => {
      const d = r.result
      if (!d.objectStoreNames.contains(STORE)) d.createObjectStore(STORE, { keyPath: 'id' })
      if (!d.objectStoreNames.contains(PHOTOS)) d.createObjectStore(PHOTOS, { keyPath: 'id' })
    }
    r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error)
  })
  return dbp
}
async function tx(store, mode, fn) {
  const d = await db()
  return new Promise((res, rej) => {
    const t = d.transaction(store, mode); const s = t.objectStore(store); let out
    Promise.resolve(fn(s)).then((v) => { out = v })
    t.oncomplete = () => res(out); t.onerror = () => rej(t.error); t.onabort = () => rej(t.error)
  })
}
const req = (r) => new Promise((res, rej) => { r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error) })

export const newId = (p) => `${p}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`

// A record: { id, type: 'answer' | 'note' | 'part_ok' | 'question', at (ms), model, ...fields, photos: [photoId] }
export async function save(rec) {
  rec = { ...rec, at: rec.at || Date.now(), updated: Date.now(), synced: false }
  await tx(STORE, 'readwrite', (s) => s.put(rec))
  push(rec)
  return rec
}
export async function all() {
  const rows = await tx(STORE, 'readonly', (s) => req(s.getAll()))
  return (rows || []).sort((a, b) => a.at - b.at)
}
export async function remove(id) {
  const rec = await tx(STORE, 'readonly', (s) => req(s.get(id)))
  await tx(STORE, 'readwrite', (s) => s.delete(id))
  for (const p of rec?.photos || []) await tx(PHOTOS, 'readwrite', (s) => s.delete(p))
  if (REMOTE_URL) fetch(`${REMOTE_URL}/records/${encodeURIComponent(id)}`, { method: 'DELETE' }).catch(() => {})
}

// Photos: downscaled on the device to about 1600 px on the long side, JPEG, before they are stored.
export async function addPhoto(file, maxSide = 1600) {
  const bmp = await (window.createImageBitmap ? createImageBitmap(file, { imageOrientation: 'from-image' }) : loadImg(file))
  const k = Math.min(1, maxSide / Math.max(bmp.width, bmp.height))
  const c = document.createElement('canvas'); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k)
  c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height)
  const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.84))
  const id = newId('photo')
  await tx(PHOTOS, 'readwrite', (s) => s.put({ id, blob, w: c.width, h: c.height, name: file.name || 'photo.jpg', synced: false }))
  pushPhoto(id, blob)
  return id
}
function loadImg(file) {
  return new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = rej; i.src = URL.createObjectURL(file) })
}
export async function photo(id) { return tx(PHOTOS, 'readonly', (s) => req(s.get(id))) }
export async function dropPhoto(id) { await tx(PHOTOS, 'readwrite', (s) => s.delete(id)) }

// One file with everything, photos embedded, for "Send to Joe".
export async function exportFile(meta = {}) {
  const records = await all(); const photos = {}
  for (const r of records) for (const p of r.photos || []) {
    const ph = await photo(p); if (ph) photos[p] = await blobToDataURL(ph.blob)
  }
  const out = { what: 'Essick rocker review: answers, notes and photos', exported: new Date().toISOString(), ...meta,
    records: records.map(({ synced, ...r }) => r), photos }
  const day = new Date().toISOString().slice(0, 10)
  return new File([JSON.stringify(out, null, 1)], `essick-rocker-notes-${day}.json`, { type: 'application/json' })
}
const blobToDataURL = (b) => new Promise((res) => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(b) })

// ------------------------------------------------------------------ remote (off while REMOTE_URL is null)
async function push(rec) {
  if (!REMOTE_URL) return
  try {
    const { synced, ...body } = rec
    const r = await fetch(`${REMOTE_URL}/records/${encodeURIComponent(rec.id)}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) })
    if (r.ok) await tx(STORE, 'readwrite', (s) => s.put({ ...rec, synced: true }))
  } catch { /* offline: retried by syncAll() on the next load */ }
}
async function pushPhoto(id, blob) {
  if (!REMOTE_URL) return
  try {
    const r = await fetch(`${REMOTE_URL}/photos/${encodeURIComponent(id)}`, { method: 'PUT', headers: { 'content-type': 'image/jpeg' }, body: blob })
    if (r.ok) { const p = await photo(id); if (p) await tx(PHOTOS, 'readwrite', (s) => s.put({ ...p, synced: true })) }
  } catch { /* retried */ }
}
export async function syncAll() {
  if (!REMOTE_URL) return
  const photos = await tx(PHOTOS, 'readonly', (s) => req(s.getAll()))
  for (const p of photos || []) if (!p.synced) await pushPhoto(p.id, p.blob)
  for (const r of await all()) if (!r.synced) await push(r)
}
