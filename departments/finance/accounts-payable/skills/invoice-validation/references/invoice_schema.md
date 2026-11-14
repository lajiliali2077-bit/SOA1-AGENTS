# Invoice schema

| column | type | note |
|---|---|---|
| invoice_id | text | unique identifier |
| vendor_id | text | links to the vendor table |
| amount_tnd | numeric(12,3) | amount in TND |
| status | text | pending, approved or rejected |
