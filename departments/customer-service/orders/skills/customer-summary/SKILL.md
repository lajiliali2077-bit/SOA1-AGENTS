---
name: customer-summary
description: Summarize a customer account with its loyalty tier, recent orders and refunds. Use when the user asks who a customer is, for a customer summary or for the order history of a customer.
allowed-tools: get_customer search_orders
---

# Customer summary

Give a short summary of one customer account. This skill only reads data.

## Procedure
1. Retrieve the customer with get_customer. If the customer does not exist, say so.
2. Retrieve the last orders with search_orders (limit 10).
3. Explain the loyalty tier with references/loyalty_tiers.md.
4. Count the refunded orders. Report a customer with more than 3 refunds in 90 days under "To check:".

## Answer template
Customer: <name> (<customer_id>), <city>, tier <tier>
Contact: <masked email>, <masked phone>
Orders: <count>, last one <order_id> on <date>
Refunds: <count>
To check: <open points, or none>
