// Public comments, stored in Supabase (see supabase/essick-comments.sql). Stays hidden unless the database
// answers with a list, so until it is set up the page looks exactly as it did. All comment text goes in with
// textContent, never innerHTML.
// The URL and the publishable (anon) key are public by design: the database only lets that key call the two
// comment functions, which enforce the limits and spam rules.
const SUPABASE_URL = 'https://cvfejlnfytsyswpkyamt.supabase.co'
const SUPABASE_KEY = 'sb_publishable_T53HgBKsth7uv4euw3vMpA_QyzO9se5' // the publishable / anon public key (never the secret / service_role key)
const LIVE_HOSTS = ['masterminnich.github.io'] // the preview never touches the real comments
const NAME_KEY = 'er.comments.name'
const MAX_NAME = 60, MAX_BODY = 2000

const configured = SUPABASE_URL && SUPABASE_KEY && LIVE_HOSTS.includes(location.hostname)
const rpc = (fn, args, signal) => fetch(`${SUPABASE_URL}/rest/v1/rpc/${fn}`, {
  method: 'POST', signal,
  headers: { apikey: SUPABASE_KEY, 'content-type': 'application/json', accept: 'application/json' },
  body: JSON.stringify(args || {}),
})

const $ = (id) => document.getElementById(id)
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e }
const st = { comments: [], closed: false, sending: false, prevScreen: '' }

// ------------------------------------------------------------------ load (or stay hidden)
async function load() {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 8000)
  try {
    const r = await rpc('essick_comments_list', {}, ctl.signal)
    if (!r.ok) return null
    const j = await r.json()
    return Array.isArray(j?.comments) ? { comments: j.comments, postingEnabled: j.postingEnabled !== false } : null
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
  try { localStorage.setItem(NAME_KEY, name) } catch {}
  setSending(true); status('', '')
  let r
  try {
    r = await rpc('essick_comment_post', { p_name: name, p_body: body, p_website: $('cmtWebsite').value })
  } catch {
    setSending(false); status('err', 'Could not reach the server. Check your connection and try again.'); return
  }
  setSending(false)
  if (r.status === 429) { status('warn', 'Slow down a little. Wait a minute, then post again.'); return }
  if (r.status === 403) { closeForm(); return }
  if (!r.ok) {
    let msg = ''; try { const j = await r.json(); msg = (r.status === 400 && j?.code === 'PT400' && j.message) || '' } catch {}
    status('err', typeof msg === 'string' && msg ? msg : 'That did not post. Try again in a moment.'); return
  }
  let c = null; try { const j = await r.json(); c = j?.comment || (j?.id ? j : null) } catch {}
  if (!c) c = { id: 'local-' + Date.now(), name, body, created_at: new Date().toISOString() }
  st.comments.push(c); $('cmtBody').value = ''
  render(c.id); status('ok', 'Posted. Thanks!')
  const l = $('cmtList'); l.scrollTop = l.scrollHeight
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
  if (!configured) return
  const got = await load()
  if (!got) return // backend not live (404, unreachable, bad answer): leave everything hidden
  st.comments = got.comments
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
  if (!got.postingEnabled) closeForm()
  if (location.hash === '#comments') open()
}
init()
