---
name: exchange-request
description: Check whether a product can be exchanged for another size or color. Use when the customer asks to exchange, swap or change the size or the color of a product.
allowed-tools: get_order get_customer get_refunds
---

# Exchange request

Check one exchange request. This skill only reads data: the exchange is shipped by the warehouse.

## Procedure
1. Retrieve the order with get_order. Note the category of the line and days_since_delivery.
2. Retrieve the customer with get_customer to know the loyalty tier.
3. Apply the return window of the returns rules (an exchange follows the same window as a return).
4. Retrieve the refunds with get_refunds: a line already refunded cannot be exchanged.
5. Exchanges are only possible for clothing and accessories. Electronics can only be returned (return-request skill).

## Answer template
Exchange: possible or not possible
Window: <days_since_delivery> days since delivery, window of <n> days
Reason: <rule applied>
To check: <open points, or none>
Message to the customer: <two polite sentences in French>
