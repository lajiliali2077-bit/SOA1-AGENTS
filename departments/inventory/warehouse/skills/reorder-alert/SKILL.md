---
name: reorder-alert
description: Detect items below their reorder threshold and propose quantities. Use when the user asks which items to reorder or about low stock.
allowed-tools: query_stock
---

# reorder-alert

1. Retrieve stock lines with query_stock.
2. Keep items below the reorder threshold of the warehouse rules.
3. Propose a quantity for each item.
