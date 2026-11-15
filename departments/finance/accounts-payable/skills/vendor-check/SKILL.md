---
name: vendor-check
description: Check the status, tax id, payment terms and open invoices of a supplier. Use when the user asks whether a vendor is valid, active, blocked or safe to pay, or asks for a vendor summary.
allowed-tools: get_vendor query_invoices
---

# Vendor check

Report the standing of one supplier. This skill only reads data.

## Procedure
1. Identify the vendor. Use get_vendor with vendor_id if the user gives one, otherwise with tax_id. If the user gives only a name, ask for the vendor_id or the tax id. Do not search by name.
2. Report the legal name, the tax id, the status, the payment terms and the masked bank account.
3. Interpret the status with references/vendor_statuses.md. Active means the vendor can be paid. Pending means documents are missing and the vendor cannot be paid. Blocked means the vendor cannot be paid, and the block reason must be given.
4. Retrieve the open invoices with query_invoices (vendor_id, status pending, limit 20). Report their count, their total in TND and the oldest due date.
5. Flag these risks: bank account changed in the last 30 days, tax id missing or not matching, several invoices just under the 5000 TND approval threshold within 30 days.

## Answer template
Vendor: <legal name> (<vendor_id>)
Status: <status> and its meaning in one line
Payment terms: <terms>
Open invoices: <count> for <total> TND, oldest due <date>
To check: <risks, or none>

## Edge cases
- Two vendors share one tax id: report both records and flag a possible duplicate vendor.
- Vendor not found: say so. Never suggest a similar vendor by guess.
- A vendor with status pending that has open invoices: report that the invoices cannot be paid until the status changes.
