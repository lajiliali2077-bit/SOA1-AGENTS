# Bank accounts and account groups

Identifiers are internal. Bank account numbers are never shown in full.

| account_id | purpose | currency | group | masked number |
|---|---|---|---|---|
| ACC-OP-01 | main operating account | TND | operating | ending 4821 |
| ACC-OP-02 | export receipts and foreign suppliers | EUR | operating | ending 7710 |
| ACC-PAY-01 | salaries and social contributions | TND | payroll | ending 3305 |
| ACC-TAX-01 | VAT and tax payments | TND | tax | ending 9054 |

## Groups
- operating: ACC-OP-01 and ACC-OP-02. Default group when the user asks for the cash position without naming an account.
- payroll: ACC-PAY-01. Funded from the operating group around the 25th of each month.
- tax: ACC-TAX-01. Receives the VAT amount due before the 28th of each month.
- all: the four accounts. Use it only when the user asks for the whole company.

## Notes
- The minimum buffer of 50000.000 TND applies to each group as a whole, not to each account.
- Transfers between accounts of the same company are not incoming or outgoing flows of a consolidated forecast. Remove them when consolidating a group.
