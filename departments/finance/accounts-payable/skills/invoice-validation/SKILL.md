---
name: invoice-validation
description: Validate supplier invoices against vendor records, purchase orders and approval thresholds, and prepare an approve, reject or hold decision. Use when the user asks to check, validate, approve or reject a supplier invoice.
allowed-tools: get_invoice query_invoices get_vendor match_invoice_to_po get_exchange_rate update_invoice_status
---

# Invoice validation

Prepare a decision on one supplier invoice. The decision is only recorded after the user confirms it.

## When to use
- The user gives an invoice identifier and asks to check, validate, approve or reject it.
- The user asks why an invoice is blocked or pending.
Do not use this skill for payment scheduling (treasury skills) or for vendor questions without an invoice (vendor-check).

## Procedure
1. Retrieve the invoice with get_invoice (include_lines true). Note the vendor, the amount, the currency, the date and the purchase order reference. If the invoice does not exist, stop and say so.
2. If the invoice is not in TND, convert the amount with get_exchange_rate at the invoice date. Keep both amounts.
3. Retrieve the vendor with get_vendor, by vendor_id. Check that the status is active and that the tax id matches the invoice. Check whether the bank account changed in the last 30 days.
4. Run match_invoice_to_po. Record each difference in quantity, unit price and total. A difference above the tolerance is a rejection reason.
5. Look for duplicates with query_invoices using the same vendor_id, a date window of 30 days around the invoice date and min_amount_tnd set to 95 percent of the amount. Compare number, date and amount of the results.
6. Choose the approval level from the exact amount in TND. Read references/approval_matrix.md if the amount is above 5000 TND or if the vendor is new.
7. Decide. APPROVE when all checks pass, REJECT when a check fails and cannot be fixed, HOLD when information is missing or a risk needs a human check.
8. Show the decision to the user and ask for confirmation. Only after an explicit yes, call update_invoice_status with the decision, a written reason and the approver identifier given by the user. For HOLD, do not call update_invoice_status: the invoice stays pending.

## Answer template
Decision: APPROVE, REJECT or HOLD
Amount: <amount> TND (original currency amount and rate if any)
Approval needed: <role> because <threshold applied>
Checks: vendor, tax id, bank account, matching, duplicate (one line each, passed or failed)
To check: <open points, or none>

## Example
Request: "Can you approve INV-2026-00457?"
The invoice is 6 200.000 TND from an active vendor, matching passes and there is no duplicate. Answer: Decision HOLD pending manager approval, because the amount is above 5000 TND. Do not call update_invoice_status.

## Edge cases
- Credit notes (negative amounts) follow the same checks but are never matched to a purchase order. Say that the matching was skipped.
- Partial delivery: if the goods receipt is lower than the invoiced quantity, the invoice can be approved only for the received quantity. Report the difference and HOLD.
- Missing purchase order: HOLD, except for the expense categories listed in references/invoice_schema.md.
- Tool error: report which check could not be performed. A decision with a missing check is HOLD.
- For the invoice fields and statuses, read references/invoice_schema.md.
