import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const money = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)
const wholeMoney = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0)
const MILESTONES = [25, 50, 75]
let csrfToken = null

const parseDay = value => { const [year, month, day] = value.split('-').map(Number); return new Date(year, month - 1, day) }
const dayFormat = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' })

function eventDates(start, end) {
  const first = parseDay(start), last = parseDay(end || start)
  const sameDay = first.getTime() === last.getTime()
  const days = sameDay ? dayFormat.format(first) : first.getMonth() === last.getMonth() ? `${dayFormat.format(first)}–${last.getDate()}` : `${dayFormat.format(first)} – ${dayFormat.format(last)}`
  return `${days}, ${last.getFullYear()}`
}

function eventCountdown(start, end) {
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const daysUntil = Math.round((parseDay(start) - today) / 86400000)
  if (daysUntil > 1) return `${daysUntil} days until our outreach`
  if (daysUntil === 1) return 'Our outreach is tomorrow'
  if (today <= parseDay(end || start)) return 'Our outreach is happening now'
  return 'Thank you for supporting our outreach'
}

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
  const [confirmation, setConfirmation] = useState(null)
  const [manualForm, setManualForm] = useState({ type: 'cash', name: '', value: '', itemId: 'water', quantity: 1 })
  const confirmationRef = useRef(null)

  const load = () => api('/api/campaign').then(setData).catch(err => setError(err.message))
  useEffect(() => { load() }, [])
  useEffect(() => { confirmationRef.current?.focus() }, [confirmation])

  async function submit(event) {
    event.preventDefault(); setNotice(''); setError('')
    const body = new FormData()
    body.append('type', type)
    body.append('name', form.name)
    body.append('email', form.email)
    body.append('amount', form.amount)
    body.append('itemId', form.itemId)
    body.append('quantity', form.quantity)
    if (type === 'cash' && form.screenshot) body.append('screenshot', form.screenshot)
    try {
      await api('/api/submissions', { method: 'POST', body })
      const item = data.campaign.items.find(entry => entry.id === form.itemId)
      setConfirmation({
        type,
        name: form.name.trim(),
        email: form.email.trim(),
        gift: type === 'cash' ? money(form.amount) : `${form.quantity} × ${item?.name || 'items'}`,
      })
      setForm({ ...form, amount: '', quantity: 1, screenshot: null })
    } catch (err) { setError(err.message) }
  }

  function giveItem(itemId) {
    setConfirmation(null)
    setType('goods')
    setForm(current => ({ ...current, itemId, quantity: 1 }))
    setTimeout(() => {
      document.querySelector('.form-card')?.scrollIntoView({ block: 'start' })
      document.getElementById('quantity')?.focus({ preventScroll: true })
    })
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
    event?.preventDefault(); setError('')
    try {
      const response = await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ goal: settings.goal, cashtag: settings.cashtag, endDate: settings.end_date, distribution: settings.distribution, items: settings.items }) })
      setSettings(response.campaign)
      setData({ ...data, campaign: response.campaign })
      setNotice('Campaign settings saved.')
    } catch (err) { setError(err.message) }
  }

  async function moderate(id, action) {
    try { await api(`/api/admin/submissions/${id}/${action}`, { method: 'POST' }); setReview(await api('/api/admin/review')); await load() }
    catch (err) { setError(err.message) }
  }

  async function addManualDonation(event) {
    event.preventDefault(); setError('')
    try {
      await api('/api/admin/donations', { method: 'POST', body: JSON.stringify(manualForm) })
      setManualForm({ ...manualForm, name: '', value: '', quantity: 1 })
      setReview(await api('/api/admin/review')); await load(); setNotice('Manual donation added.')
    } catch (err) { setError(err.message) }
  }

  async function editDonation(donation) {
    const name = window.prompt('Donor name', donation.name || 'Anonymous')
    if (name === null) return
    const field = donation.type === 'cash' ? 'value' : 'quantity'
    const value = window.prompt(donation.type === 'cash' ? 'Cash value' : 'Quantity', donation[field])
    if (value === null) return
    try { await api(`/api/admin/donations/${donation.id}`, { method: 'PUT', body: JSON.stringify({ name, [field]: value, type: donation.type, itemId: donation.item_id }) }); setReview(await api('/api/admin/review')); await load(); setNotice('Donation updated.') }
    catch (err) { setError(err.message) }
  }

  async function deleteDonation(id) {
    if (!window.confirm('Delete this verified donation?')) return
    try { await api(`/api/admin/donations/${id}`, { method: 'DELETE' }); setReview(await api('/api/admin/review')); await load(); setNotice('Donation deleted.') }
    catch (err) { setError(err.message) }
  }

  if (!data) return <main className="loading">Loading 25:35...</main>
  const { campaign, donations, totalRaised, progress, remaining, donorCount, itemTotals, campaignStatus } = data
  const campaignClosed = campaignStatus !== 'active'
  const nextMilestone = MILESTONES.map(percent => campaign.goal * percent / 100).find(amount => amount > totalRaised)
  const cashAppUrl = `https://cash.app/$${encodeURIComponent(campaign.cashtag.trim().replace(/^\$/, ''))}`
  const campaignMessage = campaignStatus === 'ended' ? 'This fundraiser has ended.' : 'The campaign goal has been reached. Thank you for helping us serve our neighbors.'

  return <>
     <header className="topbar"><a className="brand" href="#top">25:35</a><nav><a href="#about">About us</a><a href="#progress">Progress</a><a href="#items">Item drive</a><a href="#donate">Donate</a></nav></header>
    <main id="top">
      {notice && <p className="notice success">{notice}</p>}{error && <p className="notice error">{error}</p>}
       <section className="hero section"><div><p className="eyebrow">A DC outreach fundraiser</p><h1>25:35</h1><p className="scripture">“{campaign.mission}”</p><p className="muted">{campaign.scripture}</p></div><div className="mission">{campaignClosed && <p className="campaign-status">{campaignMessage}</p>}<p className="eyebrow">Our mission</p><p>{campaign.description}</p>{!campaignClosed && <a className="button" href="#donate">Give now</a>}</div></section>
       <section className="section about-section" id="about"><div className="about-intro"><p className="eyebrow">About 25:35</p><h2>Faith in action. Care in community.</h2><p>Welcome to our community outreach initiative! We are a dedicated student- and community-led movement united by a shared calling to serve, pray for, and support our neighbors living on the streets in Washington, D.C.</p><p>Rooted in our anchor verse, Matthew 25:31–39, and guided by Hebrews 13:1–2 and Luke 3:11, our mission is to put faith into action through direct compassion, dignity, and fellowship.</p></div><div className="about-image-slot" role="img" aria-label="Reserved space for a 25:35 outreach photo"><span>Image coming soon</span></div><div className="about-highlight"><p className="eyebrow">Our upcoming initiative</p><h3>November 13–14</h3><p>This fall, we are mobilizing a two-day community care effort designed to serve 100–150 individuals across the District.</p></div><div className="about-grid"><article><p className="eyebrow">Day 1 · November 13</p><h3>Preparation day</h3><p>Hosted at the District College Partnership ministry center, volunteers will prep food and organize care packages.</p></article><article><p className="eyebrow">Day 2 · November 14</p><h3>Outreach and evangelism</h3><p>Coordinated volunteer teams will deploy directly into the community to distribute care and share fellowship.</p></article><article><p className="eyebrow">Where we serve</p><h3>Two D.C. locations</h3><ul><li>MLK Library&Chinatown</li><li>Columbia Heights</li></ul></article><article><p className="eyebrow">What we hand out</p><h3>Practical care packages</h3><p>Cold sandwiches, fresh meals, mittens, scarves, wet wipes, travel-size toiletries, and feminine hygiene products.</p></article></div><div className="about-details"><div><h3>Partner with us</h3><p>The District College Partnership supports our prep space, student mobilization, and logistical needs.</p></div><div><h3>Volunteer</h3><p>We need <strong>60 volunteers</strong>, 30 per day, organized into focused outreach teams.</p></div><div><h3>Support</h3><p>Our <strong>$1,300–$2,000</strong> goal funds food supplies and winter care packages. We are seeking support through District, Pastor Chen, and general donations.</p></div></div><div className="about-bottom"><div><p className="eyebrow">Join us</p><p>Together, we can bring hope, comfort, and practical support to those who need it most in our city.</p><p className="scripture-list">“Whatever you did for one of the least of these brothers and sisters of mine, you did for me.”<br /><span>— Matthew 25:40</span></p></div><div><p className="eyebrow">Next meeting</p><p><strong>October 11 at 5:00/6:00 PM</strong></p><p className="muted">We welcome your prayers, partnership, and participation.</p></div></div></section>
      <section className="section" id="progress"><div className="section-heading"><div><p className="eyebrow">Campaign progress</p><h2>Practical care, measured clearly</h2></div><strong>{Math.round(progress)}%</strong></div><div className="big-total">{money(totalRaised)} <span>of {money(campaign.goal)}</span></div><div className="progress-track milestone-track" role="progressbar" aria-label="Raised toward goal" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(progress)}><span style={{ width: `${progress}%` }} />{MILESTONES.map(percent => <i key={percent} className={progress >= percent ? 'tick reached' : 'tick'} style={{ left: `${percent}%` }} />)}</div><div className="milestone-labels" aria-hidden="true">{MILESTONES.map(percent => <span key={percent} className={progress >= percent ? 'reached' : ''} style={{ left: `${percent}%` }}>{wholeMoney(campaign.goal * percent / 100)}</span>)}</div>{nextMilestone ? <p className="next-milestone">Next milestone: <strong>{wholeMoney(nextMilestone)}</strong>, just {money(nextMilestone - totalRaised)} to go</p> : remaining > 0 && <p className="next-milestone"><strong>Final stretch:</strong> just {money(remaining)} to reach our goal</p>}<div className="meta-row"><span>{money(remaining)} remaining</span><span>{donorCount} verified gifts</span></div>{campaign.event_start && <p className="countdown"><strong>{eventCountdown(campaign.event_start, campaign.event_end)}</strong><span>Serving neighbors {eventDates(campaign.event_start, campaign.event_end)}{campaign.end_date && !campaignClosed && ` · Give by ${dayFormat.format(parseDay(campaign.end_date))}`}</span></p>}<div className="activity"><h3>Recent verified gifts</h3>{donations.slice(0, 8).map(donation => <div className="activity-row" key={donation.id}><span>{donation.name}</span><span>{donation.type}</span><strong>{money(donation.value)}</strong></div>)}</div></section>
      <section className="section" id="items"><div className="section-heading"><div><p className="eyebrow">Item drive</p><h2>What neighbors need</h2></div></div><div className="item-grid">{campaign.items.map(item => { const collected = itemTotals[item.id] || 0; const itemProgress = item.target ? Math.min(collected / item.target * 100, 100) : 0; const needed = Math.max(item.target - collected, 0); const status = itemProgress >= 100 ? 'done' : itemProgress >= 75 ? 'close' : ''; return <article className={status ? `item-card ${status}` : 'item-card'} key={item.id}>{status && <span className={`item-badge ${status}`}>{status === 'done' ? '✓ Goal met' : 'Almost there'}</span>}<div className="item-title"><h3>{item.name}</h3><span>{money(item.value)} each</span></div><div className="mini-track"><span style={{ width: `${itemProgress}%` }} /></div><div className="meta-row"><span>{collected} of {item.target}</span><strong>{money(collected * item.value)}</strong></div>{needed > 0 && <p className="item-needed muted">{needed} more needed</p>}{!campaignClosed && <button className="small-button give-item" type="button" aria-label={`Give ${item.name}`} onClick={() => giveItem(item.id)}>Give this item</button>}</article> })}</div></section>
      <section className="section donate-grid" id="donate"><div><p className="eyebrow">Where to donate</p><h2>Give through Cash App or goods</h2><p>{campaign.distribution}</p><div className="cashtag">{campaign.cashtag}</div><div className="cash-actions"><a className="small-button" href={cashAppUrl} target="_blank" rel="noopener noreferrer">Open in Cash App</a><button className="small-button" type="button" onClick={copyCashtag}>Copy cashtag</button><span className="muted" role="status">{copyStatus}</span></div><p className="muted">Email <a href={`mailto:${campaign.contact_email}`}>{campaign.contact_email}</a> for drop-off details.</p></div>{confirmation ? <div className="form-card confirmation" ref={confirmationRef} tabIndex="-1" aria-live="polite"><p className="eyebrow">Donation received</p><h2>Thank you{confirmation.name ? `, ${confirmation.name}` : ''}!</h2><p>We are so grateful you are partnering with us to serve our unhoused neighbors in Washington, D.C.</p><dl className="receipt"><div><dt>Your gift</dt><dd>{confirmation.gift}</dd></div><div><dt>Status</dt><dd><span className="status-pill">Pending review</span></dd></div><div><dt>Confirmation email</dt><dd>{confirmation.email || 'None provided'}</dd></div></dl><h3>What happens next</h3><ol className="next-steps"><li>{confirmation.type === 'cash' ? 'Our team reviews your payment screenshot.' : 'Our team confirms your items when they are dropped off.'}</li><li>Once verified, your gift is added to the campaign total above.</li><li>{confirmation.email ? `We'll send a thank-you note to ${confirmation.email}.` : 'Questions? Email us at the address on this page.'}</li></ol><button className="button" type="button" onClick={() => setConfirmation(null)}>Submit another donation</button></div> : <form className="form-card" onSubmit={submit}><p className="eyebrow">I donated</p><h2>{campaignClosed ? 'Campaign closed' : 'Submit for review'}</h2>{campaignClosed ? <p className="muted">{campaignMessage}</p> : <><label htmlFor="type">Donation type</label><select id="type" value={type} onChange={event => setType(event.target.value)}><option value="cash">Cash</option><option value="goods">Goods</option></select><label htmlFor="name">Name</label><input id="name" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="Optional" />{type === 'cash' ? <><label htmlFor="amount">Cash amount</label><input id="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={event => setForm({ ...form, amount: event.target.value })} required /></> : <><label htmlFor="itemId">Item</label><select id="itemId" value={form.itemId} onChange={event => setForm({ ...form, itemId: event.target.value })}>{campaign.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label htmlFor="quantity">Quantity</label><input id="quantity" type="number" min="1" value={form.quantity} onChange={event => setForm({ ...form, quantity: event.target.value })} required /></>}<label htmlFor="email">Email (optional)</label><input id="email" type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} />{type === 'cash' && <><label htmlFor="screenshot">Payment screenshot</label><input id="screenshot" type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => setForm({ ...form, screenshot: event.target.files?.[0] || null })} required /><small className="muted">Required. PNG, JPEG, GIF, or WebP up to 1 MB. Admins review it privately.</small></>}<button className="button" type="submit">Submit donation</button><small className="muted">Your submission is reviewed before it appears in public totals.</small></>}</form>}</section>
      {adminOpen && <section className="section admin-panel"><p className="eyebrow">Private area</p><div className="section-heading"><h2>Admin review</h2>{review && <a className="small-button" href="/api/admin/export.csv">Export verified CSV</a>}</div>{!review ? <form onSubmit={login}><label htmlFor="password">Password</label><input id="password" type="password" value={password} onChange={event => setPassword(event.target.value)} required /><button className="button" type="submit">Sign in</button></form> : review.pending.length ? review.pending.map(entry => <div className="activity-row" key={entry.id}><span>{entry.name} · {entry.type}</span><span>{entry.type === 'cash' ? money(entry.value) : `${entry.quantity} × ${entry.item_name}`}{entry.screenshot && <><br /><a href={entry.screenshot.url} target="_blank" rel="noreferrer">View screenshot</a></>}</span><span className="actions"><button className="small-button" onClick={() => moderate(entry.id, 'approve')}>Approve</button><button className="small-button danger" onClick={() => moderate(entry.id, 'reject')}>Reject</button></span></div>) : <p className="muted">No pending submissions.</p>}{review && settings && <form className="settings-form" onSubmit={saveSettings}><h3>Campaign settings</h3><label htmlFor="admin-goal">Goal</label><input id="admin-goal" type="number" min="1" step="0.01" value={settings.goal} onChange={event => setSettings({ ...settings, goal: event.target.value })} /><label htmlFor="admin-cashtag">Cash App cashtag</label><input id="admin-cashtag" value={settings.cashtag} onChange={event => setSettings({ ...settings, cashtag: event.target.value })} /><label htmlFor="admin-end-date">End date</label><input id="admin-end-date" type="date" value={settings.end_date || ''} onChange={event => setSettings({ ...settings, end_date: event.target.value })} /><label htmlFor="admin-distribution">Distribution details</label><textarea id="admin-distribution" rows="3" value={settings.distribution} onChange={event => setSettings({ ...settings, distribution: event.target.value })} /><button className="button" type="submit">Save settings</button></form>}</section>}
        {adminOpen && review && settings && <section className="section admin-crud"><p className="eyebrow">Admin tools</p><h2>Manage progress</h2><form onSubmit={addManualDonation} className="manual-form"><label htmlFor="manual-type">Donation type</label><select id="manual-type" value={manualForm.type} onChange={event => setManualForm({ ...manualForm, type: event.target.value })}><option value="cash">Cash</option><option value="goods">Goods</option></select><label htmlFor="manual-name">Donor name</label><input id="manual-name" value={manualForm.name} onChange={event => setManualForm({ ...manualForm, name: event.target.value })} placeholder="Anonymous" />{manualForm.type === 'cash' ? <><label htmlFor="manual-value">Cash value</label><input id="manual-value" type="number" min="0.01" step="0.01" value={manualForm.value} onChange={event => setManualForm({ ...manualForm, value: event.target.value })} required /></> : <><label htmlFor="manual-item">Item</label><select id="manual-item" value={manualForm.itemId} onChange={event => setManualForm({ ...manualForm, itemId: event.target.value })}>{settings.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label htmlFor="manual-quantity">Quantity</label><input id="manual-quantity" type="number" min="1" value={manualForm.quantity} onChange={event => setManualForm({ ...manualForm, quantity: event.target.value })} required /></>}<button className="button" type="submit">Add verified donation</button></form><h3>Item values and targets</h3><div className="item-admin-list">{settings.items.map(item => <div className="item-admin-row" key={item.id}><span>{item.name}</span><input aria-label={`${item.name} value`} type="number" min="0.01" step="0.01" value={item.value} onChange={event => setSettings({ ...settings, items: settings.items.map(current => current.id === item.id ? { ...current, value: event.target.value } : current) })} /><input aria-label={`${item.name} target`} type="number" min="1" value={item.target} onChange={event => setSettings({ ...settings, items: settings.items.map(current => current.id === item.id ? { ...current, target: event.target.value } : current) })} /></div>)}</div><button className="button" type="button" onClick={saveSettings}>Save progress settings</button><h3>Verified donations</h3>{review.verified.map(donation => <div className="activity-row" key={donation.id}><span>{donation.name} · {donation.type}</span><strong>{money(donation.value)}</strong><span className="actions"><button className="small-button" type="button" onClick={() => editDonation(donation)}>Edit</button><button className="small-button danger" type="button" onClick={() => deleteDonation(donation.id)}>Delete</button></span></div>)}</section>}
        <section className="section volunteer-section"><div><p className="eyebrow">Serve with us</p><h2>Volunteer at the outreach</h2><p className="muted">Sign up through Google Forms to let us know how you would like to help. Google may ask you to sign in before you complete the form.</p>{campaign.volunteer_form_url ? <a className="button" href={campaign.volunteer_form_url} target="_blank" rel="noopener noreferrer">Open volunteer sign-up</a> : <p className="muted">Volunteer sign-up will be available soon.</p>}</div></section>
       <section className="section about-section" id="about"><div className="about-intro"><p className="eyebrow">About 25:35</p><h2>Serving our neighbors with practical care, prayer, and presence.</h2><p>25:35 is a student-led outreach effort gathering supplies, volunteers, and financial support for a two-day event serving people living on the streets in Washington, D.C.</p></div><div className="about-image-slot" role="img" aria-label="Reserved space for a 25:35 outreach photo"><span>Image coming soon</span></div><div className="about-grid"><article><p className="eyebrow">Our mission</p><p>We are preparing to serve, pray for, and support our neighbors through a focused weekend of outreach and evangelism.</p></article><article><p className="eyebrow">District College partnership</p><p>District College can provide its ministry center for preparation, connect us with student volunteers, and help us explore financial support.</p></article><article><p className="eyebrow">The weekend</p><p><strong>November 13–14</strong><br />Day 1: food preparation and packing.<br />Day 2: outreach and evangelism.</p></article><article><p className="eyebrow">Volunteer need</p><p>We need 60 volunteers total, 30 per day, organized into 4–5 groups of about 15 people.</p></article></div><div className="about-details"><div><h3>Where we will serve</h3><ul><li>MLK Library</li><li>Columbia Heights</li><li>Chinatown</li><li>Howard Hospital</li></ul></div><div><h3>What we will hand out</h3><p>Cold sandwiches, mittens, scarves, wet wipes, travel-size deodorant, toothbrush and toothpaste kits, and feminine hygiene products.</p></div><div><h3>Funding the work</h3><p>Our projected budget is <strong>$1,300–$2,000</strong> to serve 100–150 people. We are seeking support through District, Pastor Chen, and general donations.</p></div></div><div className="about-bottom"><div><p className="eyebrow">Teams and action items</p><ul className="committee-list"><li><strong>Finance / Logistics:</strong> Nkiru, Malachi, Azon, Elliot. Finalize the budget, donation tracker, and website.</li><li><strong>Partnership:</strong> Lydia, Elliott. Visit shelters, food banks, and kitchens to gather guidance and explore partnerships.</li><li><strong>Social Media / Outreach:</strong> Campbell, Jeremiah, Kadima. Lead promotion and volunteer outreach.</li><li><strong>Safety:</strong> Mercy, Lydia, Caleb. Address safety logistics and concerns.</li></ul></div><div><p className="eyebrow">Scripture and next meeting</p><p className="scripture-list">Hebrews 13:1–2<br />Matthew 25:31–39 <span>(anchor passage)</span><br />Luke 3:11</p><p><strong>Next meeting:</strong> October 11 at 5:00/6:00 PM</p></div></div></section>
     </main><footer>25:35 · Serving neighbors with care · <strong>We are not a registered nonprofit organization. Donations are not tax-deductible.</strong> <a className="admin-link" href="/?admin=1">Admin access</a></footer>
  </>
}

createRoot(document.getElementById('root')).render(<App />)
