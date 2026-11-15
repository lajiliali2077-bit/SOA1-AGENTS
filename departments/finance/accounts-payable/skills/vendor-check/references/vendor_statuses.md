# Vendor statuses

| status | meaning | can be paid | typical action |
|---|---|---|---|
| active | documents complete, tax id verified, bank account confirmed | yes | none |
| pending | vendor created, documents or bank confirmation missing | no | ask the procurement team to complete the file |
| blocked | blocked by finance or compliance | no | report the block reason, do not suggest a workaround |

## Block reasons
- tax_id_invalid: the tax id does not match the national registry.
- bank_change_unverified: the bank account changed and was not confirmed by a call back.
- duplicate_vendor: another record exists for the same tax id.
- compliance_hold: the compliance department opened a case. Do not give details, only the fact that a hold exists.

## Payment terms
Terms are stored as a number of days after the invoice date, for example NET30 or NET60. The due date of an invoice is the invoice date plus the terms, unless the invoice states a later date.

## Bank details
Bank account numbers are always shown masked, with the last 4 characters only.
