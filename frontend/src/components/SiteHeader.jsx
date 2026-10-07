import { useEffect, useState } from 'react'
import logo from '../assets/logo-icon.png'

// One link list for every page, so the menu never changes order. "/#id" links scroll on the home page
// and load the home page then scroll everywhere else.
const LINKS = [
  { href: '/about', label: 'About us' },
  { href: '/#progress', label: 'Progress' },
  { href: '/#items', label: 'Item drive' },
  { href: '/#donate', label: 'Donate' },
  { href: '/#volunteer', label: 'Volunteer' },
]

export default function SiteHeader() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const closeOnEscape = event => { if (event.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [open])

  return <header className="topbar">
    <a className="brand" href="/"><img src={logo} alt="" width="44" height="44" />25:35</a>
    <button className="menu-toggle" type="button" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen(!open)}>
      <span className="menu-icon" aria-hidden="true" />{open ? 'Close' : 'Menu'}
    </button>
    <nav id="site-nav" className={open ? 'open' : ''} aria-label="Main">
      {LINKS.map(link => <a key={link.href} href={link.href} aria-current={window.location.pathname === link.href ? 'page' : undefined} onClick={() => setOpen(false)}>{link.label}</a>)}
    </nav>
  </header>
}
