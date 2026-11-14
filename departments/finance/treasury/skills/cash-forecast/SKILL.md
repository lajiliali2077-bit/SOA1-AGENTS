---
name: cash-forecast
description: Produce a weekly cash flow forecast for the next 30 days. Use when the user asks about cash position, incoming payments or expected balance.
allowed-tools: query_payments
---

# cash-forecast

1. Retrieve expected payments with query_payments.
2. Group incoming and outgoing amounts per week.
3. Report the expected balance at the end of each week.
