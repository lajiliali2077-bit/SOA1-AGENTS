# Invoice schema

Reference for the invoice tools (get_invoice, query_invoices, match_invoice_to_po, update_invoice_status).

## Invoice header
| field | type | note |
|---|---|---|
| invoice_id | text | unique identifier, format INV-YYYY-NNNNN |
| invoice_number | text | number printed by the vendor, unique per vendor |
| vendor_id | text | links to the vendor table, format V-NNNNN |
| vendor_tax_id | text | tax id written on the invoice, must match the vendor record |
| invoice_date | date | format YYYY-MM-DD |
| due_date | date | format YYYY-MM-DD |
| currency | text | ISO 4217 code, TND when not stated |
| amount_excl_tax | numeric(12,3) | total before tax, in the invoice currency |
| tax_amount | numeric(12,3) | VAT and stamp duty |
| amount_incl_tax | numeric(12,3) | total to pay, in the invoice currency |
| amount_tnd | numeric(12,3) | total to pay converted to TND at the invoice date |
| po_reference | text | purchase order identifier, empty if none |
| status | text | see the status list below |
| approver_id | text | filled when the invoice is approved or rejected |
| approval_reason | text | free text kept in the approval history |

## Invoice lines
| field | type | note |
|---|---|---|
| line_no | integer | position in the invoice |
| item_code | text | product or service code |
| description | text | line label |
| quantity | numeric(12,3) | quantity invoiced |
| unit_price | numeric(12,3) | price per unit, in the invoice currency |
| line_total | numeric(12,3) | quantity times unit price |

## Statuses
- pending: received, not yet decided. This is the only status that update_invoice_status accepts.
- approved: accepted, waiting for a payment order.
- rejected: refused. A new invoice from the vendor is needed.
- paid: a payment order was executed.

## Purchase order exemptions
These expense categories may be approved without a purchase order: electricity, water, telecom, rent, bank fees, government fees and taxes. Any other invoice without a purchase order is put on HOLD.

## Matching tolerance
Three-way matching compares the invoice with the purchase order and the goods receipt. The default tolerance is 2 percent on quantity, unit price and total. A difference inside the tolerance passes. A difference outside the tolerance is reported line by line.

## Credit notes
A credit note has a negative amount and references the invoice it corrects. It is checked for vendor, tax id and duplicate. It is not matched against a purchase order.
