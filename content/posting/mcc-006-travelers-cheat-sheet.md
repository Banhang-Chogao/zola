+++
draft = false
title = "MCC Cheat Sheet: 50+ Codes Every Traveler Should Know"
description = "Complete reference guide to common MCCs you'll encounter abroad. Understand the difference between similar codes and how each affects your rewards."
date = 2026-06-26
updated = 2026-06-26
slug = "mcc-travelers-cheat-sheet"
[taxonomies]
categories = ["Tất cả", "Du lịch"]
tags = ["MCC", "travel", "reference", "international"]
series = "merchant-category-codes-series"
extra.series_part = 6
extra.seo_keyword = "MCC cheat sheet travel codes merchants reference"
extra.thumbnail = "/images/blog/mcc-reference.jpg"
+++

## Airlines & Air Travel (MCC 4011)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 4011 | Airlines | 3–5x points | Best reward rate for any travel card; includes online bookings + airport ticketing |
| 4112 | Passenger Railways | 2–3x points | Trains, high-speed rail; some travel cards bundle this with airlines |
| 4131 | Bus Lines | 1–2x points | City buses, intercity coaches; lower rewards than airlines |
| 4214 | Motor Freight Carriers | 1x | Commercial trucking; not useful for travelers |

**Travel Card Bonus:** Most 3x "airline" bonuses only cover 4011; missed 4112 (trains) and 4131 (buses). If you take trains in Europe, you might not get the 3x you expect.

## Hotels & Lodging (MCC 3500–3501)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 3500 | Hotels & Motels | 3–5x points | Standard hotel booking; includes major chains + boutique hotels |
| 3501 | Motels | 2–3x points | Budget lodging; some systems treat as separate from 3500 |
| 3502 | Hotel Casinos | 2x or blocked | Risky; some banks don't reward casino-hotels the same as regular hotels |
| 7011 | Hotels – Casino | 1x or blocked | Explicitly casino-focused; fraud scoring treats as gambling, not travel |

**Traveler Mistake:** Booking a casino-hotel on MCC 3502 or 7011 instead of 3500 costs you 2–3x in lost rewards. Pre-trip research: verify the merchant is coded as 3500 before booking.

## Car Rental (MCC 3700–3710)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 3700 | Auto Rental | 3–5x points | Standard car rental; includes major chains |
| 3710 | Taxi | 1x or 2x | Taxi dispatch + hail; some travel cards include, others don't |
| 4121 | Taxi & Limousine | 2–3x points | Ride-hailing (Uber, Grab, Lyft); often 3x on travel cards |
| 4111 | Local Transport | 1x | Public transit (buses, subways); low reward rate |

**Key Difference:** Taxi dispatch (MCC 3710) vs. ride-hailing (MCC 4121) vs. public transit (MCC 4111) are different codes. Visa premium travel cards often reward 4121 (Uber) at 3x but only 1x on 4111 (subway). International travelers save money using ride-hailing instead of taxis in cities where available.

## Dining (MCC 5812–5814)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 5812 | Eating Places & Restaurants | 3–4x points | Fine dining, casual restaurants, cafe; highest reward tier |
| 5813 | Drinking Places (Bars) | 1–2x points | Nightclubs, bars; some cards exclude, others limit |
| 5814 | Fast Food Restaurants | 1–2x points | McDonald's, KFC, Subway; lower rewards than fine dining |
| 5811 | Caterers | 2x points | Catering companies; business meals |
| 5499 | Miscellaneous Food Retailers | 1x | Grocery delivery, meal kits (often miscoded); should be 5412 |

**Why The Difference?** Visa's risk model views fast food (5814) as lower-ticket, lower-dispute than fine dining (5812). Restaurants pay higher interchange because of dispute risk. Bars (5813) have chargeback risk due to alcohol. Most dining cards reward 5812 at 4x but 5814 at only 1–2x.

**Common Miscode:** A high-end restaurant in London is miscoded as MCC 5814 (fast food) instead of 5812 (fine dining). You lose 3 points per dollar. Over a year of international dining, this costs $200–$500 in missed rewards.

## Grocery & Fuel (MCC 5411–5542)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 5411 | Grocery Stores | 1–3x points | Supermarkets (Tesco, Carrefour, etc.); vary by card |
| 5412 | Grocery Stores (alt) | 1–2x points | Alternate code for grocers; less common than 5411 |
| 5422 | Meat Markets | 1x | Butchers, fish markets; low reward rate |
| 5499 | Miscellaneous Food | 1x | Organic markets, meal kits; often under-rewarded |
| 5541 | Gas Stations | 1–3x points | Fuel; varies widely by card (some 0%, some 3%) |
| 5542 | Fuel Dealers | 1x | Alternative fuel (EV charging); emerging MCC |
| 5551 | Boat Marinas & Docks | 1x | Marina services; niche |

**Traveler Impact:** In many countries, a grocery store where you buy snacks might be coded as MCC 5499 (miscellaneous) instead of 5411 (grocery), costing you rewards. Checking MCC in real-time at checkout lets you request correction before the transaction settles.

## Entertainment & Attractions (MCC 7991–7999)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 7991 | Tourist Attractions | 2–3x points | Museums, theme parks, landmarks; some travel cards reward |
| 7992 | Miniature Golf | 1x | Mini golf, bowling; low reward rate |
| 7993 | Video Arcades | 1x | Game arcades; often blocked due to youth concern |
| 7994 | Video Game Centers | 1x | Gaming centers; fraud-flagged with youth |
| 7995 | Gambling | 0x or blocked | Casinos, card rooms; high fraud flag |
| 7996 | Swimming Pools | 1x | Public pools, water parks; niche |
| 7997 | Amusement Parks | 1–2x points | Theme parks; some travel cards include |
| 7998 | Nightclubs & Discos | 0x or blocked | After-hours venue; fraud-flagged, chargeback risk |
| 7999 | Recreation Services | 1x | General recreation; catch-all category |

**Fraud Alert:** MCCs 7995, 7998, and 7994 are high-fraud-flagged. Even legitimate charges might be blocked abroad. Pre-trip notification to your bank is essential if you plan to use these MCCs.

## Professional Services & Miscellaneous (MCC 8000+)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 8011 | Doctors | 1x | Medical clinics, physicians; no travel card bonus |
| 8021 | Dentists | 1x | Dental work; deductible for medical reimbursement accounts (HSA/FSA) |
| 8220 | Colleges & Universities | 0.5–1x | Tuition, student services; rarely rewarded |
| 8244 | Business & Secretarial Schools | 1x | Coding bootcamps, professional development |
| 8299 | Educational Services (misc) | 1x | Online courses, training; some business cards reward |
| 8398 | Business Consulting | 1–2x points | Consulting firms, tax prep; business spending |

**Note:** Education and professional services rarely earn high rewards even on "travel" cards. Many executives who pay for business training or conferences find they earn 1x instead of expected 3x.

## Travel-Adjacent Services (MCC 4700–4799)

| Code | Merchant Type | Typical Rewards | Notes |
|---|---|---|---|
| 4711 | Ticket Agencies | 3x points | Movie, concert, event tickets (not flights) |
| 4721 | Travel Agencies | 3x points | TravelAgencies, tour operators; often 3x on travel cards |
| 4722 | Travel Agencies (alt) | 3x points | Some systems split into two codes |
| 4789 | Other Ground Transport Services | 2–3x points | Bus lines, shuttle services, parking |
| 4790 | Transportation Services (misc) | 1–2x points | Parking, tolls, transport; catch-all |

**Overlooked:** Many international travelers book through travel agencies instead of directly with airlines/hotels. MCC 4721 often earns 3x (same as direct), but some cards exclude it. Check your card's T&C.

## Quick Lookup: Am I Earning What I Should?

**Scenario 1: Prague Restaurant Booking**
- You book dinner at a Michelin-star restaurant
- Card offers 4x dining bonus
- **Check:** Receipt should show MCC 5812
- **If MCC shows 5499/5814:** Dispute it

**Scenario 2: European Train Ticket**
- You buy a first-class train ticket in Switzerland
- Card offers 3x travel bonus (airlines only)
- **Check:** MCC will be 4112 (railways)
- **Reality:** Only 1x on 4112 if not bundled
- **Learn:** Your card doesn't cover trains; use dining card for meals instead

**Scenario 3: London Gas Station**
- You refuel your rental car
- Card offers 3x gas rewards
- **Check:** MCC should be 5541
- **If MCC shows 5542/5500:** Different code, possibly 1x rewards
- **Action:** Note for next gas station; try to use 5541 merchants only

---

## Key Takeaway

**MCCs are granular. A hotel (3500) is different from a casino-hotel (7011). A restaurant (5812) is different from fast food (5814).** Most travelers don't know these distinctions and leave money on the table. Familiarize yourself with the MCCs for your frequent spending categories (airline 4011, hotel 3500, restaurant 5812, car rental 3700). Check the MCC on your receipt after every major purchase abroad. If it's wrong, dispute it before the 60-day window closes.

---

## Your Next Step

**Print or screenshot this MCC reference table and save it to your phone.** Before your next trip, identify the 10–15 merchants you'll visit most (specific hotel chains, airlines, restaurants, gas stations). Look up their MCCs online or in your past statements. Note which MCCs earn your highest rewards. Plan your payment strategy: use your travel card for MCC 4011/3500 (airlines/hotels), dining card for MCC 5812 (restaurants), cash-back card for MCC 5411/5499 (grocery/misc). This simple homework prevents 80% of reward losses.
