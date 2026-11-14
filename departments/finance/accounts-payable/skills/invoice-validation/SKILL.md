---
name: invoice-validation
description: Validate supplier invoices against purchase orders and approval thresholds. Use when the user asks to check, approve or reject a supplier invoice.
allowed-tools: query_invoices get_vendor
---

# invoice-validation

1. Retrieve the invoice with query_invoices.
2. Check the vendor tax id with get_vendor.
3. Apply the approval threshold of the accounts payable rules.
4. Answer with the decision and the reason.

For the table layout, read references/invoice_schema.md.
