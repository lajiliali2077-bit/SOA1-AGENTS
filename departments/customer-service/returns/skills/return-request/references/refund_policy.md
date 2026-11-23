# Refund policy of TechShop

## Return windows
| category | window after delivery | gold customer |
|---|---|---|
| electronics | 7 days | 14 days |
| accessories | 14 days | 21 days |
| clothing | 14 days | 21 days |

The window is counted from the delivery date (field days_since_delivery). A request on the last day of the window is accepted.

## Approval levels
| amount to refund | who prepares | who approves |
|---|---|---|
| up to 200.000 TND | customer service agent | the same agent confirms (identifier A-xx) |
| above 200.000 TND | customer service agent | a supervisor (identifier S-xx) |
| above 1000.000 TND | customer service agent | a supervisor and the customer service manager |

The approver identifier given by the user must differ from the agent who prepared the decision when a supervisor is needed.

## Missing item
- Check that the line exists in get_order. Quote its line number, product and price.
- Refund the unit price times the missing quantity. Never refund the full order for one missing line.
- If the order has more than 50 lines, quote only the line concerned, not the full list.

## Damaged item
- A photo of the damaged item is required. Without a photo: HOLD and ask for it in the message to the customer.
- With a photo: same rules as a return, but the window is 30 days for every category.

## Already refunded
- get_refunds gives the refunds already made. Never refund the same line twice.
- The total of all refunds of an order can never exceed the order total.

## Reasons accepted
- wrong size, item not as described, missing item, damaged item, change of mind (inside the window only).
