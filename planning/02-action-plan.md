# Action Plan

## Phase 1: Decisions to make first
1. Confirm basics: fundraiser name (**25:35**, decided), dollar goal, end date, admins, and your actual $cashtag.
2. Set a dollar value per item (e.g., beanie = $8, water = $1). Admins can edit later.
3. Set a target quantity per item so each has its own progress meter.
4. Choose hosting:
   - *Simplest:* static site (GitHub Pages/Netlify) + Google Sheets/Apps Script as the database.
   - *More robust:* a small backend (Firebase or Supabase) with real login and file storage.

## Phase 2: Data design
5. Three data tables: **Donations** (id, type, amount or item, quantity, calculated value, donor name optional, status, date), **Items** (name, unit value, target qty, collected qty), **Settings** (goal, end date, cashtag).
6. Every donation has a status: **Pending → Verified or Rejected**. Only Verified entries count toward public totals.

## Phase 3: Public pages
7. **Title page:** name, scripture, mission statement, menu of page buttons, Give now.
8. **Progress:** goal bar, total raised, days left, recent verified gifts.
9. **Item Drive:** one card per item with a mini progress bar.
10. **I Donated:** Cash vs. Goods toggle; goods calculate value live.
11. **Where to Donate:** cashtag, QR code, copy button, drop-off details.
12. **Contact:** spreadmatthew2535@gmail.com in the footer and its own section.

## Phase 4: Cash App verification flow
13. Donor sends money through Cash App, then opens "I Donated."
14. They submit name (optional), amount, and a screenshot.
15. Submission lands in the review queue as **Pending**.
16. An admin compares it to Cash App activity, then approves or rejects; the bar updates.

**Decision: custom form instead of a Google Form.** Google Forms only allows file uploads from signed-in Google users, which blocks many donors. A custom form on the site that sends the screenshot and amount to a Google Sheet/Drive folder via Apps Script gives the same review experience without forced sign-in.

## Phase 5: Admin dashboard
17. Secure login (admin accounts only).
18. Review queue with screenshot preview and Approve/Reject.
19. Edit tools: manual entries, corrections, goal/item value/target changes.
20. CSV export for records.

## Phase 6: Recommended extras
- Duplicate/fraud checks (repeat screenshots or amounts) and CAPTCHA
- Privacy: private screenshot storage, admin-only access, delete after verification
- Thank-you auto-email to donors who give an email
- Share buttons and a link preview image
- Milestone celebrations (25/50/75/100%), goal-reached and fundraiser-ended states
- Accessibility: contrast, alt text, keyboard navigation
- Legal/tax note: say if donations are not tax-deductible; check local rules on fundraising and food distribution
- Impact/distribution section explaining where items go
- Volunteer or drop-off sign-up

## Phase 7: Test and launch
21. Test on phones (most donors arrive via social links).
22. Full test: submit a fake donation, approve it, watch the bar update.
23. Scan the QR code with a real phone.
24. Launch, share the link, check the review queue daily.
