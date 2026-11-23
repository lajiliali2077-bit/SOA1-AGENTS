---
name: order-tracking
description: Find where an order is, whether it is late and what to tell the customer. Use when the user asks where an order is, when it will arrive, or why a delivery is late.
allowed-tools: get_order track_shipment get_customer
---

# Order tracking

Report the delivery status of one order. This skill only reads data.

## Procedure
1. Retrieve the order with get_order. If it does not exist, stop and say so.
2. Retrieve the tracking with track_shipment: carrier, tracking number, expected delivery, days late and events.
3. Retrieve the customer with get_customer to know the loyalty tier.
4. If the order is late, give the number of days late. After 5 days late, read references/carriers.md and give the complaint procedure of the carrier.
5. Never promise a date. Give the expected date of the carrier.

## Answer template
Status: <processing, shipped or delivered>, <on time or N days late>
Carrier: <carrier> (tracking <number>)
Last event: <date>, <place>, <status>
Action: <none, or the complaint to open with the carrier>
To check: <open points, or none>
Message to the customer: <two polite sentences in French>

## Edge cases
- Delivered order: give the delivery date. If the customer says the parcel did not arrive, open a complaint with the carrier.
- No tracking event: say so and ask the carrier.
