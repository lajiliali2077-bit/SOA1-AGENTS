---
name: cash-forecast
description: Produce a weekly cash flow forecast for the next 30 days from bank balances and scheduled payments. Use when the user asks about cash position, expected balance, incoming or outgoing payments, or liquidity.
allowed-tools: get_bank_balance query_payments query_bank_transactions get_exchange_rate
---

# Cash forecast

Produce a 30-day cash forecast per week for one account or a group of accounts. This skill only reads data.

## Procedure
1. Identify the accounts. If the user does not name any, read references/bank_accounts.md and use the operating group. Use another group only if the user asks for it.
2. Get the starting balance of each account with get_bank_balance (today). Use the available amount, not the booked amount.
3. Get scheduled and expected payments for the next 30 days with query_payments, once for incoming and once for outgoing (status scheduled, date_from today, date_to today plus 30 days).
4. Get the last 30 days of transactions with query_bank_transactions only to find recurring flows that are not yet scheduled (salaries, rent, social contributions). Add them as "recurring, not yet scheduled" lines and say so.
5. Convert foreign currency amounts with get_exchange_rate at the start date. State the rate once.
6. Build the weekly table (incoming, outgoing, closing balance) following references/forecast_method.md.
7. Compare each closing balance with the 50000 TND buffer. Flag weeks below it, and flag any negative balance first.

## Answer template
Headline: the lowest closing balance, the week it occurs in, and whether the buffer holds.
Table: week, incoming, outgoing, closing (summary in KTND, one decimal)
Flags: weeks below the buffer with the shortfall in TND (3 decimals)
Assumptions: expected incoming payments, recurring flows, rate used
To check: <open points, or none>

## Edge cases
- Failed payments in the last 7 days are not outgoing flows of the forecast. Mention them under "To check:".
- An account with no transactions for 30 days: report it and exclude it from the recurring flows.
- If get_bank_balance fails for one account, give the forecast for the other accounts and say which account is missing.
- Never present expected incoming payments as certain.
