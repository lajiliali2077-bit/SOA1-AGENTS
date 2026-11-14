---
name: purchase-order-review
description: Review a purchase order for quotes, vendor approval and amount limits. Use when the user asks to check or approve a purchase order.
allowed-tools: get_purchase_order get_vendor
---

# purchase-order-review

1. Retrieve the order with get_purchase_order.
2. Check the vendor with get_vendor.
3. Check the number of quotes against the procurement rules.
4. Answer with the decision and the reason.
