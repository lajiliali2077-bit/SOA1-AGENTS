---
name: delivery-complaint
description: Prepare a complaint to the carrier for a late, lost or wrongly delivered parcel. Use when the user asks to complain to the carrier, to report a lost parcel or a parcel marked delivered but not received.
allowed-tools: get_order track_shipment
---

# Delivery complaint

Prepare the information of a complaint to the carrier. This skill only reads data: the agent sends the complaint himself or herself.

## Procedure
1. Retrieve the order with get_order and the tracking with track_shipment.
2. Check that a complaint is allowed: the parcel is more than 5 days late, or marked delivered but not received.
3. Read references/carriers.md of the order-tracking skill for the complaint procedure. If this reference is not loaded, give the carrier name and say that the procedure must be checked.
4. Prepare the complaint text: order identifier, tracking number, expected date, last event, problem.

## Answer template
Complaint: allowed or not allowed yet
Carrier: <carrier> (tracking <number>)
Problem: <late N days, lost, delivered but not received>
Complaint text: <three lines>
To check: <open points, or none>
