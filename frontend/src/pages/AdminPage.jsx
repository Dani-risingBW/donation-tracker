import { useEffect, useState } from 'react'

async function csrfToken() {
  return (await fetch('/api/csrf', { credentials: 'include' })).json().then(body => body.token)
}

async function request(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase()
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) }
  if (!['GET', 'HEAD'].includes(method)) headers['X-CSRF-Token'] = await csrfToken()
  const response = await fetch(path, { ...options, method, headers, credentials: 'include' })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || 'Something went wrong.')
  return body
}

const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)

export default function AdminPage() {
  const [password, setPassword] = useState('')
  const [review, setReview] = useState(null)
  const [settings, setSettings] = useState(null)
  const [manual, setManual] = useState({ type: 'cash', name: '', value: '', itemId: 'water', quantity: 1 })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function refresh() {
    setReview(await request('/api/admin/review'))
    setSettings((await request('/api/admin/settings')).campaign)
  }

  useEffect(() => { request('/api/admin/review').then(refresh).catch(() => {}) }, [])

  async function login(event) {
    event.preventDefault(); setError('')
    try { await request('/api/admin/login', { method: 'POST', body: JSON.stringify({ password }) }); await refresh() }
    catch (err) { setError(err.message) }
  }

  async function moderate(id, action) {
    try { await request(`/api/admin/submissions/${id}/${action}`, { method: 'POST' }); await refresh() }
    catch (err) { setError(err.message) }
  }

  async function addManual(event) {
    event.preventDefault(); setError('')
    try { await request('/api/admin/donations', { method: 'POST', body: JSON.stringify(manual) }); setManual({ ...manual, name: '', value: '', quantity: 1 }); await refresh(); setNotice('Verified donation added.') }
    catch (err) { setError(err.message) }
  }

  async function editDonation(donation) {
    const name = window.prompt('Donor name', donation.name || 'Anonymous')
    const value = window.prompt(donation.type === 'cash' ? 'Cash value' : 'Quantity', donation.type === 'cash' ? donation.value : donation.quantity)
    if (name === null || value === null) return
    try { await request(`/api/admin/donations/${donation.id}`, { method: 'PUT', body: JSON.stringify({ type: donation.type, name, value: donation.type === 'cash' ? value : undefined, quantity: donation.type === 'goods' ? value : undefined, itemId: donation.item_id }) }); await refresh() }
    catch (err) { setError(err.message) }
  }

  async function deleteDonation(id) {
    if (!window.confirm('Delete this verified donation?')) return
    try { await request(`/api/admin/donations/${id}`, { method: 'DELETE' }); await refresh() }
    catch (err) { setError(err.message) }
  }

  async function saveSettings(event) {
    event.preventDefault(); setError('')
    try { await request('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ goal: settings.goal, cashtag: settings.cashtag, endDate: settings.end_date, distribution: settings.distribution, items: settings.items }) }); setNotice('Campaign settings saved.') }
    catch (err) { setError(err.message) }
  }

  return <><header className="topbar"><a className="brand" href="/">25:35</a><nav><a href="/">Return to site</a></nav></header><main className="admin-page"><div className="admin-page-heading"><p className="eyebrow">Private area</p><h1>Admin dashboard</h1><p className="muted">Manage verified donations, review submissions, and update campaign progress.</p></div>{error && <p className="notice error">{error}</p>}{notice && <p className="notice success">{notice}</p>}{!review || !settings ? <form className="section admin-login" onSubmit={login}><p className="eyebrow">Secure sign in</p><h2>Admin access</h2><label htmlFor="admin-password">Password</label><input id="admin-password" type="password" value={password} onChange={event => setPassword(event.target.value)} required /><button className="button" type="submit">Sign in</button></form> : <><section className="section"><div className="section-heading"><div><p className="eyebrow">Review queue</p><h2>Pending submissions</h2></div><a className="small-button" href="/api/admin/export.csv">Export CSV</a></div>{review.pending.map(entry => <div className="activity-row" key={entry.id}><span>{entry.name} · {entry.type}</span><span>{entry.type === 'cash' ? money(entry.value) : `${entry.quantity} × ${entry.item_name}`}</span><span className="actions"><button className="small-button" type="button" onClick={() => moderate(entry.id, 'approve')}>Approve</button><button className="small-button danger" type="button" onClick={() => moderate(entry.id, 'reject')}>Reject</button></span></div>)}{!review.pending.length && <p className="muted">No pending submissions.</p>}</section><section className="section"><p className="eyebrow">Manual entry</p><h2>Add verified donation</h2><form onSubmit={addManual}><label htmlFor="admin-type">Type</label><select id="admin-type" value={manual.type} onChange={event => setManual({ ...manual, type: event.target.value })}><option value="cash">Cash</option><option value="goods">Goods</option></select><label htmlFor="admin-name">Donor name</label><input id="admin-name" value={manual.name} onChange={event => setManual({ ...manual, name: event.target.value })} placeholder="Anonymous" />{manual.type === 'cash' ? <><label htmlFor="admin-value">Value</label><input id="admin-value" type="number" min="0.01" step="0.01" value={manual.value} onChange={event => setManual({ ...manual, value: event.target.value })} required /></> : <><label htmlFor="admin-item">Item</label><select id="admin-item" value={manual.itemId} onChange={event => setManual({ ...manual, itemId: event.target.value })}>{settings.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label htmlFor="admin-quantity">Quantity</label><input id="admin-quantity" type="number" min="1" value={manual.quantity} onChange={event => setManual({ ...manual, quantity: event.target.value })} required /></>}<button className="button" type="submit">Add donation</button></form></section><section className="section"><p className="eyebrow">Verified progress</p><h2>Donations</h2>{review.verified.map(donation => <div className="activity-row" key={donation.id}><span>{donation.name} · {donation.type}</span><strong>{money(donation.value)}</strong><span className="actions"><button className="small-button" type="button" onClick={() => editDonation(donation)}>Edit</button><button className="small-button danger" type="button" onClick={() => deleteDonation(donation.id)}>Delete</button></span></div>)}</section><form className="section" onSubmit={saveSettings}><p className="eyebrow">Campaign controls</p><h2>Progress settings</h2><label htmlFor="admin-goal-setting">Goal</label><input id="admin-goal-setting" type="number" min="1" value={settings.goal} onChange={event => setSettings({ ...settings, goal: event.target.value })} /><label htmlFor="admin-distribution-setting">Distribution details</label><textarea id="admin-distribution-setting" rows="3" value={settings.distribution} onChange={event => setSettings({ ...settings, distribution: event.target.value })} /><h3>Item values and targets</h3>{settings.items.map(item => <div className="item-admin-row" key={item.id}><span>{item.name}</span><input aria-label={`${item.name} value`} type="number" min="0.01" value={item.value} onChange={event => setSettings({ ...settings, items: settings.items.map(current => current.id === item.id ? { ...current, value: event.target.value } : current) })} /><input aria-label={`${item.name} target`} type="number" min="1" value={item.target} onChange={event => setSettings({ ...settings, items: settings.items.map(current => current.id === item.id ? { ...current, target: event.target.value } : current) })} /></div>)}<button className="button" type="submit">Save progress settings</button></form></>}</main><footer>25:35 admin · <a href="/">Return to public site</a></footer></>
}
