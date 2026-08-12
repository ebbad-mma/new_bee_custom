# Phase 2 — what was built and where to find it

A quick-reference for answering client questions. Every path here has been
checked against the deployed code.

---

## 1. Product Catalogue (spec §2)

Storage for brand and supplier catalogues, so staff can find "the latest X
catalogue" when building a product.

**Where:** `/app/product-catalogue`, or search "Product Catalogue".

**Demo:** New → title, type (Brand / Importer / Supplier), attach the file,
save. Saving with neither a brand nor a supplier is refused — a catalogue
nobody can find later serves no purpose.

**Linked to items:** Item → **Product Builder** tab → `Linked Catalogue` and
`Catalogue Page Ref` ("page 14, SKU X").

Out of scope, as agreed in §2.4: automated extraction of data from catalogue
PDFs. Manual reference only for now.

---

## 2. Product label (spec §4)

The two-zone 50 × 25 mm label. Vertical barcode and ID on the left, the
customer-facing price block on the right.

**Where:** any Item → toolbar → **Label** group:

| Button | Does |
|---|---|
| Design / Preview Label | shows the label before printing |
| Print Barcode Label | sends it to the printer |

**What to point out:** OUR PRICE is the largest type on the label at 19pt,
struck-through MRP below it, then `SAVE ₹___`. Removed per §4.2 — the four-box
Discount/MRP/LRP grid, any discount percentage, and the term "LRP" anywhere on
the label. Three type sizes only.

The page box is a real 50 × 25 mm, not A4 with a small label printed on it.

The barcode is rendered on the server rather than drawn by JavaScript: a print
dialog does not wait for scripts, so a JS barcode is a coin toss between a real
label and a blank strip.

---

## 3. Read-only scan lookup

Scan a barcode, see the product. Changes nothing — there is no write path in
the module at all.

| Where | For | How |
|---|---|---|
| Desk dialog | staff at a computer | **Ctrl+Shift+F** anywhere in Desk |
| `/product_check` | phones, shop floor | open the URL, tap **Scan a barcode** |

Accepts `L#####`, `LX#####`, or a supplier barcode — the same codes the mobile
edit forms accept, so nobody has to think about which label they are pointing
at.

---

## 4. Customer vs staff price check

Same URL — `/product_check` — showing different things depending on who is
looking.

| | Customer (not logged in) | Staff | Senior staff |
|---|---|---|---|
| Name, price, MRP, SAVE | yes | yes | yes |
| Amazon price + link | yes | yes | yes |
| Rating | yes | yes | yes |
| Stock + warehouse | **no** | yes | yes |
| Category, brand | **no** | yes | yes |
| Velocity, days cover | **no** | yes | yes |
| Barcodes | **no** | yes | yes |
| Cost + margin | **no** | **no** | yes |

Senior = `Owner-Supervisor` or `System Manager`.

**If asked whether stock data is safe:** the restriction is enforced on the
server, not hidden in the page. A customer calling the staff endpoint directly
is refused. Fuzzy name search is disabled for guests, so the catalogue and its
prices cannot be browsed without physically holding a product.

**Images:** customers are served only photographs uploaded to the site. Every
image currently held is a hotlinked Amazon URL, which is neither ours to
republish nor reliable, so customers see none until real photos are taken.

**Camera:** requires HTTPS. On plain http the page says so rather than
appearing broken.

---

## 5. Flipkart scraper (spec §1)

Paste a Flipkart URL, get the product data. The previous implementation had
stopped returning anything.

**Input:** Item → **Market Intelligence** tab → **Codes & Links** section →
**Flipkart URL** (middle column, among the AMZ fields). `FSN No` is further
down the same tab under *Item Attributes*.

**Output:** toolbar → **Item Extra Details** → **Flipkart** tab.

**Demo:** paste a full Flipkart URL and save. The FSN extracts from the `pid=`
parameter; title, rating, ratings count, reviews count and discount fill in.

**Two points worth making:**

The FSN comes strictly from `pid=`, never a pattern match. The same URL carries
`lid=LSTSHOHFCB4WYHQDDY4EUH2ME`, which contains the FSN as a substring plus
extra characters — keying on the pattern would silently pick the wrong code.

MRP was being stored as the *selling* price. On a shoe discounted to ₹2,700
from ₹7,999, it saved 2,700 as the MRP, which made the SAVE line on every
printed label read zero. It now stores 7,999.

**Known limit:** the spec tables (model, dimensions) do not populate. They are
absent from Flipkart's structured data and the fallback parse returns nothing.

---

## 6. Product Builder (spec §3)

For products with no Amazon or Flipkart match, whose data lives on a brand
site, in a catalogue, or on a similar product's listing.

**Where:** Item → **Product Builder** tab. Buttons under the toolbar's
**Product Builder** group.

**The part worth demonstrating.** Set a Reference ASIN, choose a Reference
Relationship, then **Pull from Reference ASIN**. Before anything is written it
shows exactly what will and will not be copied:

| Relationship | Copies | Refuses |
|---|---|---|
| Exact match | everything (27 fields) | nothing |
| Same product, different brand | 16 fields — category, specs, dimensions, keywords | brand, price, reviews, features, images |
| Same brand, different size | brand, description, features, reviews, images | price, dimensions |
| Same brand, different colour | as above, plus price and dimensions | — |
| Same sub-category only | category hints only | everything else |

The principle to state plainly: another brand's price and reviews are not ours
to inherit, and a different size's dimensions are simply wrong for this one.
Approximate data is never published as though it were exact.

**Photo rule (§3.5):** scraped images always go to *Reference Photo* and never
become the product image — including on an exact match, which is where
publishing the borrowed photo would be most tempting. The item is flagged
**Needs Own Photos** until a real one is taken.

**Publish gate (§3.4):** **Check Publish Readiness** lists what is missing. It
reports rather than blocks, so staff can still record partial data.

---

## 7. POS groundwork (spec §5.2, §5.3)

Built and deployed, deliberately switched **off**.

- `Sales Person` → **Short Code**, for fast entry at the till
- `POS Profile` → **Require Salesperson On Every Sale**, currently unticked

**Why off:** the Sales Person master holds one group node and no actual people.
Switching it on would refuse every sale at the counter. The roster comes first.

Attribution is built on the native Sales Person master and Sales Team table,
never a free-text name, because per-salesperson grouping is the entire point
and free text makes it impossible.

**Current state: 4,670 POS invoices, none attributed.** Worth saying plainly —
§5.3 exists because a sale that was never attributed cannot be analysed
afterwards.

---

## What is not done

**POS Next migration (§5).** Not attempted, and the reason is factual rather
than a matter of scheduling:

| | |
|---|---|
| POS Next `version-16` branch, last commit | December 2025 |
| Built and CI-tested against | `version-16-beta` |
| Commits behind their `version-15` branch | 463 |
| What `version-15` CI targets | ERPNext 15 |
| What this site runs | ERPNext 16.28 |

Their maintainers were asked directly in June 2026 whether the version-16
branch could be used with ERPNext 16. The answer was "we will update version 16
branch soon"; the branch has not moved since, and the issue was closed by a
stale-bot rather than resolved. A follow-up asking about an ERPNext 16 release
is still open.

So the spec's premise — *"configuration and migration, not building features
from scratch"* — does not hold today.

Also pending: loyalty tiers and earn/redeem rates (a decision for the client),
and the floor staff roster.

---

## Data gaps — raise these before they are discovered

These look like broken software but are empty fields.

| | |
|---|---|
| Items with a Flipkart FSN | **0 of 8,017** |
| Genuine product descriptions | **3** — the other 7,316 hold the item name copied into the description field |
| Product photographs | all **1,722** are hotlinked Amazon URLs, so customers see none |
| Items with a real cost recorded | **44** — cost/margin shows "not recorded" on the rest |
| Flipkart spec tables (model, dimensions) | never populate — absent from Flipkart's data |

Only the last is a genuine limitation of the software. The rest fill in as
staff work through the data.

**On cost and margin specifically:** 7,861 items carry a margin figure against
a zero cost, one reading 475% against a cost of nothing and the highest in the
catalogue at 280,130%. Those are leftovers from costs that are no longer
stored. Cost and margin are therefore withheld unless a real cost exists —
showing them to someone with discount authority would be worse than showing
nothing. They appear on their own once the cost field is backfilled.

---

## Deployment note

`custom_url` and `custom_fsn_no` — the entry points for the entire Flipkart
flow — were historically shipped by **woocommerceconnector's** fixture file
rather than by this app, despite being tagged `module: luckybee_customization`.
A site running a different version of that app never received them, and the
Flipkart feature was unreachable there with no error explaining why.

The `ensure_flipkart_fields` patch now creates them from this app. It is
idempotent: on a site that already has the fields, nothing changes.
