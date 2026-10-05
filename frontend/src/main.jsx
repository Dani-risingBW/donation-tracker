import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)
let csrfToken = null

async function ensureCsrfToken() {
  if (csrfToken) return csrfToken
  const response = await fetch('/api/csrf', { credentials: 'include' })
  csrfToken = (await response.json()).token
  return csrfToken
}

async function api(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  if (method !== 'GET' && method !== 'HEAD' && method !== 'OPTIONS') await ensureCsrfToken()
  const isFormData = options.body instanceof FormData
  const headers = isFormData ? { ...options.headers } : { 'Content-Type': 'application/json', ...options.headers }
  if (csrfToken) headers['X-CSRF-Token'] = csrfToken
  const response = await fetch(path, { credentials: 'include', headers, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || 'Something went wrong.')
  return body
}

function App() {
  const [data, setData] = useState(null)
  const [type, setType] = useState('cash')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', email: '', amount: '', itemId: 'water', quantity: 1, screenshot: null })
  const [adminOpen, setAdminOpen] = useState(() => new URLSearchParams(window.location.search).get('admin') === '1')
  const [password, setPassword] = useState('')
  const [review, setReview] = useState(null)
  const [settings, setSettings] = useState(null)
  const [copyStatus, setCopyStatus] = useState('')

  const load = () => api('/api/campaign').then(setData).catch(err => setError(err.message))
  useEffect(() => { load() }, [])

  async function submit(event) {
    event.preventDefault(); setNotice(''); setError('')
    const body = new FormData()
    body.append('type', type)
    body.append('name', form.name)
    body.append('email', form.email)
    body.append('amount', form.amount)
    body.append('itemId', form.itemId)
    body.append('quantity', form.quantity)
    if (form.screenshot) body.append('screenshot', form.screenshot)
    try {
      await api('/api/submissions', { method: 'POST', body })
      setNotice('Thank you. Your donation is pending review.')
      setForm({ ...form, amount: '', quantity: 1, screenshot: null })
    } catch (err) { setError(err.message) }
  }

  async function copyCashtag() {
    try { await navigator.clipboard.writeText(data.campaign.cashtag); setCopyStatus('Copied!') }
    catch { setCopyStatus('Copy failed. Press and hold the cashtag to copy it.') }
    setTimeout(() => setCopyStatus(''), 3000)
  }

  async function login(event) {
    event.preventDefault(); setError('')
    try { await api('/api/admin/login', { method: 'POST', body: JSON.stringify({ password }) }); setReview(await api('/api/admin/review')); setSettings((await api('/api/admin/settings')).campaign); setAdminOpen(true) }
    catch (err) { setError(err.message) }
  }

  async function saveSettings(event) {
    event.preventDefault(); setError('')
    try {
      const response = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ goal: settings.goal, cashtag: settings.cashtag, endDate: settings.end_date, distribution: settings.distribution }) })
      setSettings(response.campaign)
      setData({ ...data, campaign: response.campaign })
      setNotice('Campaign settings saved.')
    } catch (err) { setError(err.message) }
  }

  async function moderate(id, action) {
    try { await api(`/api/admin/submissions/${id}/${action}`, { method: 'POST' }); setReview(await api('/api/admin/review')); await load() }
    catch (err) { setError(err.message) }
  }

  if (!data) return <main className="loading">Loading 25:35...</main>
  const { campaign, donations, totalRaised, progress, remaining, donorCount, itemTotals, campaignStatus } = data
  const campaignClosed = campaignStatus !== 'active'
  const cashAppUrl = `https://cash.app/$${encodeURIComponent(campaign.cashtag.trim().replace(/^\$/, ''))}`
  const campaignMessage = campaignStatus === 'ended' ? 'This fundraiser has ended.' : 'The campaign goal has been reached. Thank you for helping us serve our neighbors.'

  return <>
    <header className="topbar"><a className="brand" href="#top">25:35</a><nav><a href="#progress">Progress</a><a href="#items">Item drive</a><a href="#donate">Donate</a></nav></header>
    <main id="top">
      {notice && <p className="notice success">{notice}</p>}{error && <p className="notice error">{error}</p>}
      <section className="hero section"><div><p className="eyebrow">A DC outreach fundraiser</p><h1>25:35</h1><p className="scripture">“For I was hungry and you gave me something to eat, I was thirsty and you gave me something to drink.”</p><p className="muted">{campaign.scripture}</p></div><div className="mission">{campaignClosed && <p className="campaign-status">{campaignMessage}</p>}<p className="eyebrow">Our mission</p><p>{campaign.description}</p>{!campaignClosed && <a className="button" href="#donate">Give now</a>}</div></section>
      <section className="section" id="progress"><div className="section-heading"><div><p className="eyebrow">Campaign progress</p><h2>Practical care, measured clearly</h2></div><strong>{Math.round(progress)}%</strong></div><div className="big-total">{money(totalRaised)} <span>of {money(campaign.goal)}</span></div><div className="progress-track"><span style={{ width: `${progress}%` }} /></div><div className="meta-row"><span>{money(remaining)} remaining</span><span>{donorCount} verified gifts</span></div><div className="activity"><h3>Recent verified gifts</h3>{donations.slice(0, 8).map(donation => <div className="activity-row" key={donation.id}><span>{donation.name}</span><span>{donation.type}</span><strong>{money(donation.value)}</strong></div>)}</div></section>
      <section className="section" id="items"><div className="section-heading"><div><p className="eyebrow">Item drive</p><h2>What neighbors need</h2></div></div><div className="item-grid">{campaign.items.map(item => { const collected = itemTotals[item.id] || 0; const itemProgress = item.target ? Math.min(collected / item.target * 100, 100) : 0; return <article className="item-card" key={item.id}><div className="item-title"><h3>{item.name}</h3><span>{money(item.value)} each</span></div><div className="mini-track"><span style={{ width: `${itemProgress}%` }} /></div><div className="meta-row"><span>{collected} of {item.target}</span><strong>{money(collected * item.value)}</strong></div></article> })}</div></section>
      <section className="section donate-grid" id="donate"><div><p className="eyebrow">Where to donate</p><h2>Give through Cash App or goods</h2><p>{campaign.distribution}</p><div className="cashtag">{campaign.cashtag}</div><div className="cash-actions"><a className="small-button" href={cashAppUrl} target="_blank" rel="noopener noreferrer">Open in Cash App</a><button className="small-button" type="button" onClick={copyCashtag}>Copy cashtag</button><span className="muted" role="status">{copyStatus}</span></div><p className="muted">Email <a href={`mailto:${campaign.contact_email}`}>{campaign.contact_email}</a> for drop-off details.</p></div><form className="form-card" onSubmit={submit}><p className="eyebrow">I donated</p><h2>{campaignClosed ? 'Campaign closed' : 'Submit for review'}</h2>{campaignClosed ? <p className="muted">{campaignMessage}</p> : <><label htmlFor="type">Donation type</label><select id="type" value={type} onChange={event => setType(event.target.value)}><option value="cash">Cash</option><option value="goods">Goods</option></select><label htmlFor="name">Name</label><input id="name" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="Optional" />{type === 'cash' ? <><label htmlFor="amount">Cash amount</label><input id="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} required /></> : <><label htmlFor="itemId">Item</label><select id="itemId" value={form.itemId} onChange={event => setForm({ ...form, itemId: event.target.value })}>{campaign.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label htmlFor="quantity">Quantity</label><input id="quantity" type="number" min="1" value={form.quantity} onChange={event => setForm({ ...form, quantity: event.target.value })} required /></>}<label htmlFor="email">Email (optional)</label><input id="email" type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} /><label htmlFor="screenshot">Payment screenshot</label><input id="screenshot" type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => setForm({ ...form, screenshot: event.target.files?.[0] || null })} required /><small className="muted">Required. PNG, JPEG, GIF, or WebP up to 1 MB. Admins review it privately.</small><button className="button" type="submit">Submit donation</button><small className="muted">Your submission is reviewed before it appears in public totals.</small></>}</form></section>
      {adminOpen && <section className="section admin-panel"><p className="eyebrow">Private area</p><div className="section-heading"><h2>Admin review</h2>{review && <a className="small-button" href="/api/admin/export.csv">Export verified CSV</a>}</div>{!review ? <form onSubmit={login}><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} required /><button className="button" type="submit">Sign in</button></form> : review.pending.length ? review.pending.map(entry => <div className="activity-row" key={entry.id}><span>{entry.name} · {entry.type}</span><span>{entry.type === 'cash' ? money(entry.value) : `${entry.quantity} × ${entry.item_name}`}{entry.screenshot && <><br /><a href={entry.screenshot.url} target="_blank" rel="noreferrer">View screenshot</a></>}</span><span className="actions"><button className="small-button" onClick={() => moderate(entry.id, 'approve')}>Approve</button><button className="small-button danger" onClick={() => moderate(entry.id, 'reject')}>Reject</button></span></div>) : <p className="muted">No pending submissions.</p>}{review && settings && <form className="settings-form" onSubmit={saveSettings}><h3>Campaign settings</h3><label htmlFor="admin-goal">Goal</label><input id="admin-goal" type="number" min="1" step="0.01" value={settings.goal} onChange={event => setSettings({ ...settings, goal: event.target.value })} /><label htmlFor="admin-cashtag">Cash App cashtag</label><input id="admin-cashtag" value={settings.cashtag} onChange={event => setSettings({ ...settings, cashtag: event.target.value })} /><label htmlFor="admin-end-date">End date</label><input id="admin-end-date" type="date" value={settings.end_date || ''} onChange={event => setSettings({ ...settings, end_date: event.target.value })} /><label htmlFor="admin-distribution">Distribution details</label><textarea id="admin-distribution" rows="3" value={settings.distribution} onChange={event => setSettings({ ...settings, distribution: event.target.value })} /><button className="button" type="submit">Save settings</button></form>}</section>}
    </main><footer>25:35 · Serving neighbors with care <a className="admin-link" href="/?admin=1">Admin access</a></footer>
  </>
}

createRoot(document.getElementById('root')).render(<App />)
