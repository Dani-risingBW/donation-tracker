import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import AboutPage from './pages/AboutPage'
import AdminPage from './pages/AdminPage'
import SiteHeader from './components/SiteHeader'
import logo from './assets/logo.jpg'

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
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (csrfToken) headers['X-CSRF-Token'] = csrfToken
  const response = await fetch(path, { credentials: 'include', headers, ...options })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || 'Something went wrong.')
  return body
}

function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', email: '', itemId: '', quantity: 1 })
  const [copyStatus, setCopyStatus] = useState('')
  const [confirmation, setConfirmation] = useState(null)
  const [showItems, setShowItems] = useState(false)
  const confirmationRef = useRef(null)
  const isAboutPage = window.location.pathname === '/about'
  const isAdminPage = window.location.pathname === '/admin'

  const load = () => api('/api/campaign').then(setData).catch(err => setError(err.message))
  useEffect(() => { load() }, [])
  useEffect(() => { confirmationRef.current?.focus() }, [confirmation])
  // Sections render after the campaign loads, so links like /#donate from other pages scroll once data arrives.
  useEffect(() => { if (data && window.location.hash) document.getElementById(window.location.hash.slice(1))?.scrollIntoView() }, [data])

  async function submit(event) {
    event.preventDefault(); setError('')
    try {
      const itemId = form.itemId || data.campaign.items[0]?.id
      await api('/api/submissions', { method: 'POST', body: JSON.stringify({ type: 'goods', ...form, itemId }) })
      const item = data.campaign.items.find(entry => entry.id === itemId)
      setConfirmation({
        name: form.name.trim(),
        email: form.email.trim(),
        gift: `${form.quantity} × ${item?.name || 'items'}`,
      })
      setForm({ ...form, quantity: 1 })
    } catch (err) { setError(err.message) }
  }

  function giveItem(itemId) {
    setConfirmation(null)
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

  if (isAboutPage) return <AboutPage />
  if (isAdminPage) return <AdminPage />
  if (!data) return <main className="loading">Loading 25:35...</main>
  const { campaign, donations, totalRaised, progress, remaining, donorCount, itemTotals, campaignStatus } = data
  const campaignClosed = campaignStatus !== 'active'
  const nextMilestone = MILESTONES.map(percent => campaign.goal * percent / 100).find(amount => amount > totalRaised)
  const cashAppUrl = `https://cash.app/$${encodeURIComponent(campaign.cashtag.trim().replace(/^\$/, ''))}`
  const itemsCollected = campaign.items.reduce((sum, item) => sum + Math.min(itemTotals[item.id] || 0, item.target), 0)
  const itemsWanted = campaign.items.reduce((sum, item) => sum + item.target, 0)
  const campaignMessage = campaignStatus === 'ended' ? 'This fundraiser has ended.' : 'The campaign goal has been reached. Thank you for helping us serve our neighbors.'

  return <>
     <SiteHeader />
     <main id="top">
      {error && <p className="notice error">{error}</p>}
       <section className="hero section"><div><h1 className="hero-logo"><img src={logo} alt="25:35 College-Student Outreach. Serve. Pray. Give." width="520" height="520" /></h1><p className="eyebrow">A DC outreach fundraiser</p><p className="scripture">“{campaign.mission}”</p><p className="muted">{campaign.scripture}</p></div><div className="mission">{campaignClosed && <p className="campaign-status">{campaignMessage}</p>}<p className="eyebrow">Our mission</p><p>{campaign.description}</p>{!campaignClosed && <a className="button" href="#donate">Give now</a>}</div></section>
      <section className="section" id="progress"><div className="section-heading"><div><p className="eyebrow">Campaign progress</p><h2>Practical care, measured clearly</h2></div><strong>{Math.round(progress)}%</strong></div><div className="big-total">{money(totalRaised)} <span>of {money(campaign.goal)}</span></div><div className="progress-track milestone-track" role="progressbar" aria-label="Raised toward goal" aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(progress)}><span style={{ width: `${progress}%` }} />{MILESTONES.map(percent => <i key={percent} className={progress >= percent ? 'tick reached' : 'tick'} style={{ left: `${percent}%` }} />)}</div><div className="milestone-labels" aria-hidden="true">{MILESTONES.map(percent => <span key={percent} className={progress >= percent ? 'reached' : ''} style={{ left: `${percent}%` }}>{wholeMoney(campaign.goal * percent / 100)}</span>)}</div>{nextMilestone ? <p className="next-milestone">Next milestone: <strong>{wholeMoney(nextMilestone)}</strong>, just {money(nextMilestone - totalRaised)} to go</p> : remaining > 0 && <p className="next-milestone"><strong>Final stretch:</strong> just {money(remaining)} to reach our goal</p>}<div className="meta-row"><span>{money(remaining)} remaining</span><span>{donorCount} verified gifts</span></div>{campaign.event_start && <p className="countdown"><strong>{eventCountdown(campaign.event_start, campaign.event_end)}</strong><span>Serving neighbors {eventDates(campaign.event_start, campaign.event_end)}{campaign.end_date && !campaignClosed && ` · Give by ${dayFormat.format(parseDay(campaign.end_date))}`}</span></p>}<div className="activity"><h3>Recent verified gifts</h3>{!donations.length && <p className="muted">Gifts appear here once our team records them.</p>}{donations.slice(0, 8).map(donation => <div className="activity-row" key={donation.id}><span>{donation.name}</span><span>{donation.type}</span><strong>{money(donation.value)}</strong></div>)}</div></section>
      <section className="section item-drive" id="items">
        <div className="section-heading"><div><p className="eyebrow">Item drive</p><h2>Help fill the care packages</h2><p className="muted">Everything we hand out on November 14 comes from items you bring. Pledge what you can, then drop it off before the prep day.</p></div></div>
        <div className="drive-summary"><p><strong>{itemsCollected}</strong> of {itemsWanted} items collected</p><div className="mini-track" role="progressbar" aria-label="Items collected" aria-valuemin="0" aria-valuemax="100" aria-valuenow={itemsWanted ? Math.round(itemsCollected / itemsWanted * 100) : 0}><span style={{ width: `${itemsWanted ? itemsCollected / itemsWanted * 100 : 0}%` }} /></div><button className="small-button" type="button" aria-expanded={showItems} aria-controls="item-list" onClick={() => setShowItems(!showItems)}>{showItems ? 'Hide items' : `See all ${campaign.items.length} items`}</button></div>
        {showItems && <div id="item-list"><ol className="drive-steps"><li><strong>Choose an item</strong><span>Pick anything below that still needs help.</span></li><li><strong>Pledge it</strong><span>Tell us how many you can bring.</span></li><li><strong>Drop it off</strong><span>Email <a href={`mailto:${campaign.contact_email}`}>{campaign.contact_email}</a> for drop-off details{campaign.end_date && ` by ${dayFormat.format(parseDay(campaign.end_date))}`}.</span></li></ol>
        <div className="item-grid">{campaign.items.map(item => { const collected = itemTotals[item.id] || 0; const itemProgress = item.target ? Math.min(collected / item.target * 100, 100) : 0; const needed = Math.max(item.target - collected, 0); const status = itemProgress >= 100 ? 'done' : itemProgress >= 75 ? 'close' : ''; return <article className={status ? `item-card ${status}` : 'item-card'} key={item.id}>{status && <span className={`item-badge ${status}`}>{status === 'done' ? '✓ Goal met' : 'Almost there'}</span>}<h3>{item.name}</h3><p className="item-needed">{needed > 0 ? <><strong>{needed}</strong> still needed</> : 'Thank you! We have enough.'}</p><div className="mini-track" role="progressbar" aria-label={`${item.name} collected`} aria-valuemin="0" aria-valuemax="100" aria-valuenow={Math.round(itemProgress)}><span style={{ width: `${itemProgress}%` }} /></div><div className="meta-row muted"><span>{collected} of {item.target} collected</span><span>About {wholeMoney(item.value)} each</span></div>{!campaignClosed && needed > 0 && <button className="small-button give-item" type="button" aria-label={`Pledge ${item.name}`} onClick={() => giveItem(item.id)}>Pledge this item</button>}</article> })}</div></div>}
      </section>
      <section className="section donate-grid" id="donate"><div><p className="eyebrow">Where to donate</p><h2>Give money through GoFundMe</h2><p>{campaign.distribution}</p><a className="button" href={campaign.gofundme_url} target="_blank" rel="noopener noreferrer">Donate on GoFundMe</a><p className="muted">Prefer Cash App? Send to <strong>{campaign.cashtag}</strong> with no fees.</p><div className="cash-actions"><a className="small-button" href={cashAppUrl} target="_blank" rel="noopener noreferrer">Open in Cash App</a><button className="small-button" type="button" onClick={copyCashtag}>Copy cashtag</button><span className="muted" role="status">{copyStatus}</span></div><p className="muted">Money gifts appear in the total above after our team records them. Email <a href={`mailto:${campaign.contact_email}`}>{campaign.contact_email}</a> for goods drop-off details.</p></div>{confirmation ? <div className="form-card confirmation" ref={confirmationRef} tabIndex="-1" aria-live="polite"><p className="eyebrow">Donation received</p><h2>Thank you{confirmation.name ? `, ${confirmation.name}` : ''}!</h2><p>We are so grateful you are partnering with us to serve our unhoused neighbors in Washington, D.C.</p><dl className="receipt"><div><dt>Your gift</dt><dd>{confirmation.gift}</dd></div><div><dt>Status</dt><dd><span className="status-pill">Pending review</span></dd></div><div><dt>Confirmation email</dt><dd>{confirmation.email || 'None provided'}</dd></div></dl><h3>What happens next</h3><ol className="next-steps"><li>Our team confirms your items when they are dropped off.</li><li>Once verified, your gift is added to the campaign total above.</li><li>{confirmation.email ? `We'll send a thank-you note to ${confirmation.email}.` : 'Questions? Email us at the address on this page.'}</li></ol><button className="button" type="button" onClick={() => setConfirmation(null)}>Pledge more items</button></div> : <form className="form-card" onSubmit={submit}><p className="eyebrow">Donate goods</p><h2>{campaignClosed ? 'Campaign closed' : 'Pledge items'}</h2>{campaignClosed ? <p className="muted">{campaignMessage}</p> : <><label htmlFor="name">Name</label><input id="name" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} placeholder="Optional" /><label htmlFor="itemId">Item</label><select id="itemId" value={form.itemId || campaign.items[0]?.id} onChange={event => setForm({ ...form, itemId: event.target.value })}>{campaign.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><label htmlFor="quantity">Quantity</label><input id="quantity" type="number" min="1" step="1" inputMode="numeric" value={form.quantity} onChange={event => setForm({ ...form, quantity: event.target.value })} required /><label htmlFor="email">Email (optional)</label><input id="email" type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} /><small className="muted">We use your email to thank you and to tell you about future 25:35 events. It is never shown on this site.</small><button className="button" type="submit">Pledge items</button><small className="muted">Items count toward the totals once our team confirms them at drop-off.</small></>}</form>}</section>
        <section className="section volunteer-section" id="volunteer"><div><p className="eyebrow">Serve with us</p><h2>Volunteer at the outreach</h2><p className="muted">Sign up through Google Forms to let us know how you would like to help. Google may ask you to sign in before you complete the form.</p>{campaign.volunteer_form_url ? <a className="button" href={campaign.volunteer_form_url} target="_blank" rel="noopener noreferrer">Open volunteer sign-up</a> : <p className="muted">Volunteer sign-up will be available soon.</p>}</div></section>
      </main><footer>25:35 · Serving neighbors with care · <strong>We are not a registered nonprofit organization. Donations are not tax-deductible.</strong> <a className="admin-link" href="/admin">Admin access</a></footer>
  </>
}

createRoot(document.getElementById('root')).render(<App />)
