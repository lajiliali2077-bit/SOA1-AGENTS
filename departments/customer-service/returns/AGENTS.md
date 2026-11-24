# AGENTS.md (Level 3: Customer service / Returns and refunds)

Rules for return and refund skills. They override the department rules where they differ.

## Return window (override)
- The standard return window is 14 days after delivery.
- Electronics (category electronics) can only be returned within 7 days after delivery. This overrides the standard window.
- Gold customers get 7 more days on any window.
- The window is checked with the field days_since_delivery of the order, never with the order date.

## Approval threshold (override)
- A refund above 200 TND requires the approval of a supervisor. This overrides the department threshold of 300 TND.
- The person who prepares the refund cannot be the person who approves it.

## Refund checks
- Check the refunds already made for the order. A second refund of the same line is never approved.
- A missing item in a delivered order is refunded for that line only, after the check of the order lines.
- A damaged item needs a photo from the customer. Without a photo: HOLD.

## Decision format
- Answer with one of APPROVE, REJECT or HOLD. Then give the amount, the window applied and the checks performed.
- Call create_refund only after an explicit confirmation of the agent with an approver identifier.

## Test
- ceci est un test