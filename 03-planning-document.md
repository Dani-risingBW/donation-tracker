# 25:35 Fundraiser: Planning Document

**Live page:** https://claude.ai/artifact/FbKStDfSZwTfnHsFoKHkv2
**Contact:** spreadmatthew2535@gmail.com

## 1. Purpose
Track fundraiser progress toward a dollar goal, combining cash and the cash value of donated goods, and manage an item drive for people experiencing homelessness in Washington, D.C.

## 2. Branding
- **Name:** 25:35
- **Scripture:** "For I was hungry and you gave me something to eat, I was thirsty and you gave me something to drink, I was a stranger and you invited me in." (Matthew 25:35)
- **Mission:** A college-student outreach non-profit organization in Washington, D.C., dedicated to joyfully serving, praying for, and giving to the unhoused community through faith in God.
- **Colors:** Cream `#F9F6F0` (primary background), Navy `#001F3F` (text, menu button), Gold `#D99B26` (progress bars, accents, Give button). Cream in all modes; no dark mode.

## 3. Pages and features (built)
| Page | What it does |
|---|---|
| Title page | Name, scripture, mission, text-button menu, Give now |
| Progress | Goal bar, total, days left, milestones, recent verified gifts |
| Item Drive | Per-item progress bars with value and target |
| Where to Donate | Cashtag, QR code, copy and open-Cash-App buttons, drop-off note |
| I Donated | Cash (amount + screenshot) or Goods (item + quantity) form; submits as Pending |
| Contact | Email address (also in footer) |
| Admin (admins only) | Review queue, manual entries, settings, CSV export, delete screenshots |

**Navigation:** a ☰ Menu dropdown at top right on every page; the 25:35 title button at top left returns to the title page. Layout is compact for mobile.

## 4. Item list (default value / target; editable in Admin)
| Item | Value | Target |
|---|---|---|
| Knit Beanies | $8 | 50 |
| Warm Mittens | $6 | 50 |
| Fleece Scarves | $10 | 40 |
| Cold Sandwiches (deli or PB&J) | $4 | 100 |
| Fruit Cups & Soft Granola Bars | $2 | 100 |
| Bottled Water | $1 | 200 |
| Travel Toothbrush & Toothpaste Kit | $3 | 60 |
| Travel Deodorant | $3 | 60 |
| Wet Wipes (packs) | $2 | 80 |
| Feminine Hygiene Items | $5 | 60 |
| Drawstring / Cinch Bags | $3 | 60 |

These numbers are placeholders. The default goal is $1,000.

## 5. Verification flow
Donor pays via Cash App → opens "I Donated" → submits amount and screenshot → status **Pending** → admin compares with Cash App activity → **Approve** (counts toward totals, screenshot deleted) or **Reject**. Only verified entries appear publicly.

## 6. Decisions and trade-offs
- **Custom form instead of Google Form:** avoids forced Google sign-in. The Google Sheet/Drive (Apps Script) route is the recommendation if you self-host.
- **Built-in database instead of Google Sheets:** published pages here cannot send data to Google, so the review queue lives in the page's own database.
- **Production database:** use Neon PostgreSQL with SQLAlchemy. SQLite remains the local-development default, while PostgreSQL provides safer concurrent writes and a migration path for production.
- **Production file storage:** use private Supabase Storage for payment screenshots, accessed through a storage adapter. Screenshots must remain admin-only and be deleted after moderation.
- **Free-tier launch:** Neon and Supabase free tiers are acceptable for an initial low-traffic launch, but the fundraiser must move to paid resources or add backups before relying on it for important records.
- **Known limitations:**
  - Donors need to be signed in to Claude with access to submit; others can view only.
  - Pending screenshots are technically readable by any invited submitter, though only admins see the review queue. Delete after review.
  - Spam protection is only a hidden honeypot field.

## 7. Open items
- [ ] Real Cash App $cashtag (currently `$YourCashtag`)
- [ ] Real goal amount and end date
- [ ] Confirm item values and targets
- [ ] Replace "Where the items go" placeholder text with the real distribution plan
- [ ] Add drop-off location and instructions
- [ ] Decide on tax-deductibility statement (501(c)(3) status)
- [ ] Optional: thank-you emails, CAPTCHA, duplicate-screenshot detection, share buttons, volunteer sign-up
- [ ] Test on phones; run a fake donation end to end; scan the QR code
- [x] Decide production database and file storage: Neon PostgreSQL + SQLAlchemy and private Supabase Storage

## 8. Design reference
Navigation and button style modeled on campusoutreachdc.org/give (clean uppercase text buttons). The site blocked automated access, so the style was matched from description, not from the page itself.

## 9. Files
- `01-refined-prompt.md`
- `02-action-plan.md`
- `03-planning-document.md`
