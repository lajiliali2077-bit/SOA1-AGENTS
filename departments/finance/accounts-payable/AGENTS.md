# AGENTS.md (Level 3: Finance / Accounts payable)

Rules for invoice and vendor skills. They override the Finance department rules where they differ.

## Approval thresholds (override)
- Invoices above 5000 TND require manager approval. This overrides the department threshold of 10000 TND for invoices.
- Invoices above 20000 TND also require the signature of the finance director.
- Never split an invoice or group invoices to stay under a threshold. If one vendor has several invoices just under 5000 TND within 30 days, report the pattern under "To check:".

## Vendor checks
- Always check the vendor before approving an invoice: the status must be active and the tax id on the invoice must match the vendor record.
- A vendor with the status blocked or pending cannot be paid. The invoice stays pending.
- A bank account that changed in the last 30 days is a risk. Report it, and do not approve the invoice until the user confirms.

## Invoice checks
- Run three-way matching (invoice, purchase order, goods receipt). A difference above 2 percent on quantity, unit price or total is a rejection reason unless the user explicitly accepts it.
- Look for a duplicate: same vendor and same amount with the same invoice date or number. A probable duplicate is never approved.
- Invoices in foreign currency are converted at the central bank rate of the invoice date.

## Decision format
- Answer with one of APPROVE, REJECT or HOLD. Then give the reason, the checks performed and the threshold applied.
- A decision is only recorded after the user confirms it. Do not call update_invoice_status before that.
