# NurSkin — Client Handoff Message

Send to the clinic owner. Specific values filled in from the July/Oct 2026 setup.

---

Hi [Name], your website is built and live! 🎉

You can see it here: **nurskin.onrender.com** (the final address will be **nurskin.co**).

To make it officially yours there are a couple of small setup steps, and I've kept them as simple as possible:

**What it costs:**
- **Your web address (nurskin.co):** about **£25 a year**
- **Hosting (keeping the website online):** about **£5.50 a month** — this is why your site stays up even if nobody's computer is on
- **Card payments (Stripe):** no monthly fee — Stripe just takes a small percentage of each card payment, a few pence per pound
- That's everything. No hidden fees, and **you own all of it** — the address and the website are in your name, not mine.

**What you need to do (about 15 minutes):**

**Step 1 — Buy your web address (5 min)**
1. Go to **cloudflare.com** and click **Sign up**
2. Use your own email and a password
3. Click **Domain Registration → Register Domain**
4. Type **nurskin.co** and pay (~£25)

**Step 2 — Set up hosting (10 min)**
1. Go to **render.com** and sign up (you can sign up with a GitHub account — if you don't have one, it will let you create one during signup, that's normal)
2. Open **github.com/Oaktree96/nurskin** and click **Fork** (top right) to copy the project into your account
3. On Render click **New → Blueprint** and pick the **nurskin** project from your list
4. Click **Apply** — your site appears at your own render.com address within a few minutes

**Step 3 — Do nothing**
Once it's live, tell me and I'll connect your new web address to the website for you — that part is my job. I'll also take care of the payment setup with you over a quick call so your card guarantee keeps working.

---

**Or, if you'd rather not touch any of this:** no problem — I can run it all for you for **£25/month** (includes the hosting, web address, updates and support). Just reply "take care of it for me" and I'll handle everything, you just pay the one monthly bill.

Either way, your website is up and taking bookings right now. Let me know which you'd prefer!

---

## Internal notes (delete before sending)

- Live URLs: preview https://nurskin.onrender.com (on Steven's Render, $7/mo starter plan), local PC copy on :8081, Cloudflare tunnel created but no zone (domain never purchased).
- The GitHub fork step is the only bit she might stumble on — fallback: fork for her via screen-share, or she picks the £25/month care plan.
- Her Stripe live keys are in the project `.env` — reuse them on her Render service (confirm the Stripe account is registered to the clinic; payouts follow the account owner).
- After her deployment is live: delete Steven's Render service, wire DNS (Cloudflare CNAME → her Render URL).
