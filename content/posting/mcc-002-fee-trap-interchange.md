+++
draft = false
title = "MCC and Cross-Border Fees: Why Hotels Cost More Than Casinos"
description = "Deep dive into how Merchant Category Codes determine interchange fees, cross-border surcharges, and why some merchant types pay 5x more than others."
date = 2026-06-26
updated = 2026-06-26
slug = "mcc-cross-border-fees-interchange"
[taxonomies]
categories = ["Tất cả", "Tài chính"]
tags = ["MCC", "interchange-fees", "cross-border", "merchant-costs"]
series = "merchant-category-codes-series"
extra.series_part = 2
extra.seo_keyword = "MCC cross-border fees interchange rates merchant category"
extra.thumbnail = "/images/blog/mcc-fees.jpg"
+++

## How Interchange Fees Are Set by Merchant Category Code

When you pay with a credit card abroad, the acquiring bank (the merchant's bank) instantly transfers your payment to your issuing bank (who issued your card). That transfer isn't free. Visa and Mastercard set **interchange fees**—the percentage the acquiring bank pays the issuing bank to process the transaction.

Interchange fees are not universal. They vary by **Merchant Category Code**. This is the key insight most travelers miss: **the merchant doesn't choose how much they pay—the payment network does, based on the MCC.** Visa publishes an official interchange fee table (updated quarterly) that maps MCCs to percentage rates.

### Interchange Fee Examples by MCC (Visa/Mastercard typical rates, 2026)

| Merchant Type | MCC | Domestic Interchange | International Interchange |
|---|---|---|---|
| Airlines | 4511 | 1.50% | 2.20% |
| Hotels | 3500–3501 | 1.80% | 2.80% |
| Car Rental | 3700 | 2.00% | 2.90% |
| Restaurants | 5812 | 2.20% | 3.10% |
| Grocery Stores | 5411 | 0.55% | 1.50% |
| Gas Stations | 5542 | 0.80% | 1.80% |
| Casinos | 7995 | 1.50% | 3.50% |
| Money Transfers | 6211 | 3.00% | 4.50% |
| Cryptocurrency | 6051 | 3.50% | 5.00% |
| Gambling Online | 6812 | 3.00% | 5.50% |

**Why the variation?** Visa's risk model treats high-ticket, dispute-prone, or chargeback-intensive merchant categories as riskier. Casinos and cryptocurrency exchanges have higher chargeback rates (people dispute "losing" money), so they pay higher interchange. Grocery stores have low chargeback rates—they get rewarded with 0.55% interchange.

### The Hidden Layer: Currency Conversion & Cross-Border Markup

Interchange is only the first layer. On top of it, your issuing bank adds:

1. **Currency conversion markup** (typically 1–3%, fixed by your bank's FX desk)
2. **Cross-border processing fee** (sometimes 0%, sometimes 3%, depends on the bank and the merchant's MCC)
3. **Dynamic Currency Conversion (DCC) junk fee** (if you accept "conversion at the terminal")

For a $1,000 hotel booking at MCC 3500:
- Interchange: 2.80% = $28
- FX markup: 2.00% = $20
- Cross-border fee: 1.50% (some banks apply this to certain MCCs) = $15
- **Total hidden cost: $63 (6.3%)**

But wait—**who pays this?** Often, the merchant absorbs part of it. But not all. Many merchants practicing "dynamic currency conversion" (DCC) at the terminal offer you a "convenient" local currency conversion at a jacked-up rate. That's how they recoup the interchange + cross-border fees and add a margin. Result: you pay an effective 8–10% premium if you agree to DCC.

## Real Case: Hotel Miscoded as "Miscellaneous Retail"

A boutique hotel in Prague (MCC should be 3500, "Hotels and Motels") was miscoded by its acquirer as **MCC 5999 ("Miscellaneous Retail")**.

**Impact:**
- Correct MCC 3500 interchange: 2.80%
- Miscoded MCC 5999 interchange: 2.40% (cheaper for the merchant, but...)
- The hotel's acquirer passed the "savings" to... themselves, not the guest.
- Guests who expected 3x points on "travel" got 1x on "retail" instead.
- Over 1 year, frequent travelers lost $200–$500 in cashback per person per year.

**The catch?** The hotel's terminal was miscoded at the acquiring bank. The hotel owner didn't know. The guests didn't know. Their credit card rewards programs didn't know. Only the payment network knew—but by then, the transaction was already settled.

## How Merchants Choose (and Are Forced Into) MCCs

Merchants don't actually choose their MCC. Here's the real process:

1. **Merchant applies to an acquiring bank** (usually via a payment processor like Stripe, Square, etc.)
2. **The acquirer assigns an MCC** based on:
   - The merchant's legal business classification (restaurant = 5812)
   - The acquirer's own risk model
   - Visa/Mastercard's mandatory MCC mapping rules
3. **The merchant can request a change**, but it's rare, slow, and requires proof of primary business activity
4. **The merchant CANNOT avoid their MCC** without changing their legal business entity

Some merchants are incentivized to miscategorize themselves. A restaurant that wants lower interchange might claim to be "meal prep retail" (MCC 5499) instead of "restaurant" (5812). This costs them credibility, but saves 1–2% on processing fees. Those savings sometimes pass to customers via lower menu prices—but often they don't.

## Who Bears the Cost?

This is where it gets political. In theory:
- Merchant pays interchange to their acquirer
- Acquirer passes some to the network (Visa/Mastercard)
- If interchange is high, merchant either: absorbs it (margin compression) or passes it to customer (higher prices)

**In practice?** All three happen:
- Some merchants eat the cost (competitive markets, thin margins)
- Some pass it to cardholders via surcharges or higher prices
- Some optimize by miscoding (risky long-term, can trigger audits)
- Some negotiate lower interchange by volume (only works for big merchants)

**Frequent travelers pay double:** You get hit by higher interchange (2.80–5.50% for international MCCs) AND your credit card might not recognize the MCC as "travel," so you lose rewards on top of the fee. A $1,000 hotel stay that costs $63 extra in fees + $30 in lost cashback = $93 total damage, or 9.3% of the bill.

---

## Key Takeaway

**Merchant Category Codes are how payment networks price-discriminate between merchant types.** High-chargeback, high-risk categories (crypto, gambling, money transfers) pay 3–5x more interchange than low-risk ones (grocery, gas). Hotels and airlines are in the middle. Merchants sometimes miscode to reduce costs, and when they do, *you* lose cashback rewards even though the merchant paid less in fees. Knowing the MCC of every merchant you use lets you spot these mismatches early.

---

## Your Next Step

**Look up the interchange rates for your top 10 international merchants.** Visa publishes their [official interchange fee table](https://www.visa.com/en/business/small-business-tools/merchant-category-codes). Find the MCC for each of your frequent merchants (hotel chain, airline, restaurant), note the interchange rate, and compare it to the rewards bonus your card offers. If your hotel pays 2.80% interchange but you only get 2x points (0.5–1% value), the math is broken—you're effectively losing money on cashback while the merchant still pays full fees.
