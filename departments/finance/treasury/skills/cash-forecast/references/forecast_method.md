# Cash forecast method

## Periods
- Weeks run from Monday to Sunday. The forecast starts today and covers 30 days.
- Week 1 starts today and ends on the first Sunday. Weeks 2 to 4 are full weeks. The remaining days form week 5.
- Payments dated on a Saturday, a Sunday or a public holiday are executed on the next working day. Put them in the week of that working day.

## Opening balance
- Use the available balance of each account at the start date, as returned by get_bank_balance.
- Do not add payments already executed today. They are already in the balance.

## Flows
- Incoming: customer receipts with status scheduled, plus expected receipts. Expected receipts are listed on their own line and never mixed with scheduled ones.
- Outgoing: payment orders with status scheduled, plus recurring flows that are not yet scheduled.
- Recurring flows: look at the last 30 days of bank transactions. A flow with the same label and a similar amount (within 10 percent) on the same day of the month is recurring. Add it in the week of its next expected date.
- Ignore failed payments. List them under "To check:" with the reason if known.

## Computation
For each week and each account:
closing balance = opening balance + incoming - outgoing
The opening balance of week N+1 is the closing balance of week N.
Consolidate a group of accounts by adding the closing balances in TND after conversion.

## Foreign currency
- Convert each foreign currency amount with the rate of the forecast start date, taken from get_exchange_rate.
- Keep the original amount in the detail table next to the TND amount.

## Rounding and presentation
- Compute with full precision and round only for display.
- Summary table in KTND with 1 decimal. Detail table in TND with 3 decimals.
- Flag a week when the closing balance is below the minimum buffer of 50000.000 TND, with the shortfall.
