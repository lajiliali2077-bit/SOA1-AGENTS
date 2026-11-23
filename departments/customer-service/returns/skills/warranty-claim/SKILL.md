---
name: warranty-claim
description: Decide whether a broken product is still covered by the manufacturer warranty and what to offer (repair, replacement or refund). Use when the customer says a product stopped working, is broken or is defective after the return window.
allowed-tools: get_order get_product calculate
---

# Warranty claim

Check the warranty of one product of an order. This skill only reads data: a repair or a replacement is organised by the after-sales team.

## Procedure
1. Retrieve the order with get_order. Note the delivery date, days_since_delivery and the line of the product.
2. Retrieve the product with get_product to know the warranty in months. A warranty of 0 months means no warranty.
3. Convert the warranty in days with calculate (months times 30) and compare it with days_since_delivery.
4. Read references/warranty_rules.md to choose the solution.
5. Inside the return window, the customer can also choose a return: say so and name the return-request skill.

## Answer template
Covered: yes or no
Product: <name> (<sku>), warranty <n> months
Delivered: <days_since_delivery> days ago
Solution: <repair, replacement, refund or none> because <rule applied>
To check: <open points, or none>
Message to the customer: <two polite sentences in French>
