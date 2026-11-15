# Approval matrix for supplier invoices

The amount used is amount_tnd, never a rounded value.

| amount in TND | validation | approval |
|---|---|---|
| up to 5000.000 | accounts payable accountant | none |
| above 5000.000 up to 20000.000 | accounts payable accountant | finance manager |
| above 20000.000 | accounts payable accountant | finance manager and finance director |

## Extra rules
- First invoice of a new vendor (vendor created in the last 90 days): finance manager approval whatever the amount.
- Invoice whose vendor bank account changed in the last 30 days: HOLD until the vendor is called back on a known phone number and the user confirms it.
- Foreign currency invoice: apply the table to amount_tnd. Above 20000 TND the treasury team must also confirm that the foreign currency is available.
- Invoice approved with a matching difference above the tolerance: finance manager approval whatever the amount, and the difference is written in the reason.

## Segregation of duties
The person who validates an invoice cannot approve it. The approver identifier given by the user must differ from the validator. If they are the same person, HOLD and ask for another approver.

## Escalation
If the finance manager is unavailable for more than 3 working days, the finance director can approve in place of the manager. Record that in the reason.
