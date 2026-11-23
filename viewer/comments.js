// Public comments. Stays hidden unless the comments API answers with a list: until the backend is live the page
// must look exactly as it did. All comment text goes in with textContent, never innerHTML.
const API = 'https://marcella-api.sean-b08.workers.dev/api/essick-rocker/comments'
const TURNSTILE_SITE_KEY = '' // set to the Cloudflare Turnstile site key to require a check; empty skips it
const NAME_KEY = 'er.comments.name'
const MAX_NAME = 80, MAX_BODY = 2000

const $ = (id) => document.getElementById(id)
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e }
const st = { comments: [], closed: false, sending: false, token: '', widget: null, prevScreen: '' }

// ------------------------------------------------------------------ load (or stay hidden)
async function load() {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 8000)
  try {
    const r = await fetch(API, { signal: ctl.signal, headers: { accept: 'application/json' } })
    if (!r.ok) return null
    const j = await r.json()
    return Array.isArray(j?.comments) ? j.comments : null
  } catch { return null } finally { clearTimeout(t) }
}

// ------------------------------------------------------------------ list
const fmtDay = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' })
const fmtYear = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
function when(s) {
  const d = new Date(typeof s === 'number' && s < 1e12 ? s * 1000 : s); if (isNaN(d)) return ''
  const mins = (Date.now() - d) / 60000
  if (mins < 1) return 'just now'
  if (mins < 60) return `${Math.floor(mins)} min ago`
  if (mins < 60 * 24) return `${Math.floor(mins / 60)} h ago`
  return (d.getFullYear() === new Date().getFullYear() ? fmtDay : fmtYear).format(d)
}
function row(c, fresh) {
  const li = el('li', 'crow' + (fresh ? ' fresh' : ''))
  const head = el('div', 'chead')
  head.append(el('b', 'cname', String(c.name || 'Someone')))
  const t = el('time', 'cwhen', when(c.created_at)); if (c.created_at) t.dateTime = String(c.created_at)
  head.append(t)
  li.append(head, el('p', 'cbody', String(c.body ?? '')))
  return li
}
function render(freshId) {
  const n = st.comments.length
  $('cmtN').textContent = n; $('cmtN').toggleAttribute('data-zero', !n)
  $('cmtSub').textContent = n ? `${n} ${n === 1 ? 'comment' : 'comments'}. Anyone with the link can read them.` : 'Anyone with the link can read these.'
  const list = $('cmtList'); list.replaceChildren()
  if (!n) {
    const e = el('div', 'dempty'); e.append(el('b', null, 'No comments yet'), document.createTextNode('Say what you think of the chair, or ask Joe a question.'))
    list.append(e); return
  }
  const ol = el('ol', 'clist')
  for (const c of [...st.comments].sort((a, b) => new Date(a.created_at) - new Date(b.created_at))) ol.append(row(c, c.id === freshId))
  list.append(ol)
}

// ------------------------------------------------------------------ form states
function status(kind, text) {
  const s = $('cmtStatus'); s.className = 'cstatus' + (kind ? ' ' + kind : ''); s.textContent = text || ''
}
function setSending(on) {
  st.sending = on
  const b = $('cmtPost'); b.disabled = on || st.closed; b.textContent = on ? 'Posting…' : 'Post comment'
  $('cmtForm').classList.toggle('busy', on)
}
function closeForm() {
  st.closed = true
  $('cmtForm').hidden = true; $('cmtClosed').hidden = false
}

async function post(e) {
  e.preventDefault()
  if (st.sending || st.closed) return
  const name = $('cmtName').value.trim(), body = $('cmtBody').value.trim()
  if (!name) { status('warn', 'Add your name first.'); $('cmtName').focus(); return }
  if (!body) { status('warn', 'Write a comment first.'); $('cmtBody').focus(); return }
  if (TURNSTILE_SITE_KEY && !st.token) { status('warn', 'One moment: finishing the robot check.'); return }
  try { localStorage.setItem(NAME_KEY, name) } catch {}
  setSending(true); status('', '')
  const payload = { name, body, website: $('cmtWebsite').value }
  if (TURNSTILE_SITE_KEY) payload.turnstileToken = st.token
  let r
  try {
    r = await fetch(API, { method: 'POST', headers: { 'content-type': 'application/json', accept: 'application/json' }, body: JSON.stringify(payload) })
  } catch {
    setSending(false); status('err', 'Could not reach the server. Check your connection and try again.'); return
  } finally { resetTurnstile() }
  setSending(false)
  if (r.status === 429) { status('warn', 'Slow down a little. Wait a minute, then post again.'); return }
  if (r.status === 403) { closeForm(); return }
  if (!r.ok) {
    let msg = ''; try { msg = (await r.json())?.error || '' } catch {}
    status('err', typeof msg === 'string' && msg ? msg : 'That did not post. Try again in a moment.'); return
  }
  let c = null; try { const j = await r.json(); c = j?.comment || (j?.id ? j : null) } catch {}
  if (!c) c = { id: 'local-' + Date.now(), name, body, created_at: new Date().toISOString() }
  st.comments.push(c); $('cmtBody').value = ''
  render(c.id); status('ok', 'Posted. Thanks!')
  const l = $('cmtList'); l.scrollTop = l.scrollHeight
}

// ------------------------------------------------------------------ Turnstile (only when a site key is set)
function loadTurnstile() {
  if (!TURNSTILE_SITE_KEY) return
  const box = $('cmtTs'); box.hidden = false
  window.erTurnstileReady = () => {
    st.widget = window.turnstile.render(box, {
      sitekey: TURNSTILE_SITE_KEY, theme: 'light', size: 'flexible',
      callback: (t) => { st.token = t }, 'expired-callback': () => { st.token = '' }, 'error-callback': () => { st.token = '' },
    })
  }
  const s = document.createElement('script')
  s.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=erTurnstileReady'
  s.async = true; s.defer = true; document.head.append(s)
}
function resetTurnstile() {
  if (!TURNSTILE_SITE_KEY || st.widget == null || !window.turnstile) return
  st.token = ''; window.turnstile.reset(st.widget)
}

// ------------------------------------------------------------------ drawer
function open() {
  $('cdrawer').hidden = false
  st.prevScreen = document.body.dataset.screen
  document.body.dataset.screen = 'er.comments'; $('sid').textContent = 'er.comments'
  const l = $('cmtList'); l.scrollTop = l.scrollHeight
  if (!st.closed && matchMedia('(pointer: fine)').matches) ($('cmtName').value ? $('cmtBody') : $('cmtName')).focus({ preventScroll: true })
}
function close() {
  if ($('cdrawer').hidden) return
  $('cdrawer').hidden = true
  if (document.body.dataset.screen === 'er.comments' && st.prevScreen) { document.body.dataset.screen = st.prevScreen; $('sid').textContent = st.prevScreen }
  if (location.hash === '#comments') history.replaceState(null, '', location.pathname + location.search)
}

async function init() {
  const comments = await load()
  if (!comments) return // backend not live (404, unreachable, bad answer): leave everything hidden
  st.comments = comments
  try { $('cmtName').value = localStorage.getItem(NAME_KEY) || '' } catch {}
  $('cmtName').maxLength = MAX_NAME; $('cmtBody').maxLength = MAX_BODY
  render()
  $('commentsBtn').hidden = false; document.body.classList.add('has-comments')
  $('commentsBtn').onclick = open; $('cmtClose').onclick = close
  $('cdrawer').addEventListener('click', (e) => { if (e.target === $('cdrawer')) close() })
  addEventListener('keydown', (e) => { if (e.key === 'Escape') close() })
  document.querySelectorAll('.tab, #notesBtn').forEach((t) => t.addEventListener('click', close))
  $('cmtForm').addEventListener('submit', post)
  $('cmtBody').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) post(e) })
  for (const id of ['cmtName', 'cmtBody']) $(id).addEventListener('input', () => { if ($('cmtStatus').classList.contains('warn') || $('cmtStatus').classList.contains('ok')) status('', '') })
  loadTurnstile()
  if (location.hash === '#comments') open()
}
init()
