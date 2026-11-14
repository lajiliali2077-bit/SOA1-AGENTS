# Generates the 3-level AGENTS.md / SKILL.md tree under departments/
# Run from the repository root: .\scripts\generate_departments.ps1

if (-not (Test-Path manage.py)) { throw "Run this script from the repository root (manage.py not found)." }

function Write-Utf8($path, $text) {
  $dir = Split-Path $path -Parent
  if ($dir) { New-Item -ItemType Directory -Force $dir | Out-Null }
  [System.IO.File]::WriteAllText((Join-Path $PWD $path), $text, (New-Object System.Text.UTF8Encoding $false))
}
function New-Agents($path, $title, $rules) {
  $body = "# AGENTS.md ($title)`n`n## Rules`n"
  foreach ($r in $rules) { $body += "- $r`n" }
  Write-Utf8 $path $body
}
function New-Skill($dir, $name, $desc, $tools, $steps, $extra = '') {
  $body = "# $name`n`n"
  $i = 1
  foreach ($s in $steps) { $body += "$i. $s`n"; $i++ }
  if ($extra) { $body += "`n$extra`n" }
  Write-Utf8 "$dir/SKILL.md" ("---`nname: $name`ndescription: $desc`nallowed-tools: $tools`n---`n`n" + $body)
}

# ---------- Level 1: global ----------
New-Agents 'AGENTS.md' 'Level 1: global' @(
  'Answer in the language of the user.',
  'Be concise and cite the skill used at the end of the answer.',
  'Never output a full IBAN. Mask everything except the last 4 characters.')

# ---------- Finance ----------
$FIN = 'departments/finance'; $AP = "$FIN/accounts-payable"; $TR = "$FIN/treasury"
New-Agents "$FIN/AGENTS.md" 'Level 2: Finance' @(
  'Express every amount in TND with 3 decimals.',
  'Any operation above 10000 TND requires manager approval.')
New-Agents "$AP/AGENTS.md" 'Level 3: Finance / Accounts payable' @(
  'Invoices above 5000 TND require manager approval (overrides the department threshold).',
  'Always check the vendor tax id before approving an invoice.')
New-Agents "$TR/AGENTS.md" 'Level 3: Finance / Treasury' @(
  'Forecasts cover 30 days and are given per week.',
  'Never give investment advice. Only report figures and trends.')
New-Skill "$AP/skills/invoice-validation" 'invoice-validation' 'Validate supplier invoices against purchase orders and approval thresholds. Use when the user asks to check, approve or reject a supplier invoice.' 'query_invoices get_vendor' @(
  'Retrieve the invoice with query_invoices.',
  'Check the vendor tax id with get_vendor.',
  'Apply the approval threshold of the accounts payable rules.',
  'Answer with the decision and the reason.') 'For the table layout, read references/invoice_schema.md.'
Write-Utf8 "$AP/skills/invoice-validation/references/invoice_schema.md" ("# Invoice schema`n`n| column | type | note |`n|---|---|---|`n| invoice_id | text | unique identifier |`n| vendor_id | text | links to the vendor table |`n| amount_tnd | numeric(12,3) | amount in TND |`n| status | text | pending, approved or rejected |`n")
New-Skill "$AP/skills/vendor-check" 'vendor-check' 'Check the status and tax id of a supplier. Use when the user asks whether a vendor is valid, active or blocked.' 'get_vendor' @(
  'Retrieve the vendor with get_vendor.',
  'Report status, tax id and any block reason.')
New-Skill "$TR/skills/cash-forecast" 'cash-forecast' 'Produce a weekly cash flow forecast for the next 30 days. Use when the user asks about cash position, incoming payments or expected balance.' 'query_payments' @(
  'Retrieve expected payments with query_payments.',
  'Group incoming and outgoing amounts per week.',
  'Report the expected balance at the end of each week.')

# ---------- HR ----------
$HR = 'departments/hr'; $RC = "$HR/recruitment"; $PY = "$HR/payroll"
New-Agents "$HR/AGENTS.md" 'Level 2: HR' @(
  'Employee personal data is confidential. Never reveal salaries to non-HR users.',
  'Use gender-neutral wording in all outputs.')
New-Agents "$RC/AGENTS.md" 'Level 3: HR / Recruitment' @(
  'Evaluate candidates only on skills and experience.',
  'Return a score from 0 to 10 with a one-line justification.')
New-Agents "$PY/AGENTS.md" 'Level 3: HR / Payroll' @(
  'Amounts are monthly gross in TND with 3 decimals.',
  'Overtime above 20 hours per month requires HR approval.')
New-Skill "$RC/skills/cv-screening" 'cv-screening' 'Screen candidate CVs against a job profile and score them. Use when the user asks to shortlist, rank or evaluate candidates.' 'get_candidates' @(
  'Retrieve the candidates with get_candidates.',
  'Compare each CV to the job profile.',
  'Return the ranking with scores.')
New-Skill "$RC/skills/interview-scheduling" 'interview-scheduling' 'Propose interview slots for shortlisted candidates. Use when the user asks to plan, schedule or move an interview.' 'get_calendar' @(
  'Read the available slots with get_calendar.',
  'Propose three slots per candidate.')
New-Skill "$PY/skills/payslip-check" 'payslip-check' 'Verify a payslip against contract terms and attendance. Use when the user asks to check, explain or correct a payslip.' 'get_payslip get_contract' @(
  'Retrieve the payslip with get_payslip and the contract with get_contract.',
  'Compare base salary, overtime and deductions.',
  'List any difference with its amount.')

# ---------- Inventory ----------
$INV = 'departments/inventory'; $WH = "$INV/warehouse"; $PR = "$INV/procurement"
New-Agents "$INV/AGENTS.md" 'Level 2: Inventory' @(
  'Quantities are integers in units. Dates use the YYYY-MM-DD format.',
  'Reorder when stock falls below 100 units.')
New-Agents "$WH/AGENTS.md" 'Level 3: Inventory / Warehouse' @(
  'Reorder when stock falls below 50 units (overrides the department threshold).',
  'Report stock by location code.')
New-Agents "$PR/AGENTS.md" 'Level 3: Inventory / Procurement' @(
  'Purchase orders above 10000 TND need two quotes.',
  'Prefer vendors already approved in the vendor table.')
New-Skill "$WH/skills/stock-check" 'stock-check' 'Report current stock levels by item and location. Use when the user asks how many units are available or where an item is stored.' 'query_stock' @(
  'Retrieve stock lines with query_stock.',
  'Report quantity per location code.')
New-Skill "$WH/skills/reorder-alert" 'reorder-alert' 'Detect items below their reorder threshold and propose quantities. Use when the user asks which items to reorder or about low stock.' 'query_stock' @(
  'Retrieve stock lines with query_stock.',
  'Keep items below the reorder threshold of the warehouse rules.',
  'Propose a quantity for each item.')
New-Skill "$PR/skills/purchase-order-review" 'purchase-order-review' 'Review a purchase order for quotes, vendor approval and amount limits. Use when the user asks to check or approve a purchase order.' 'get_purchase_order get_vendor' @(
  'Retrieve the order with get_purchase_order.',
  'Check the vendor with get_vendor.',
  'Check the number of quotes against the procurement rules.',
  'Answer with the decision and the reason.')

# ---------- Compliance (read-only skills) ----------
$CMP = 'departments/compliance'; $AU = "$CMP/audit"; $DP = "$CMP/data-privacy"
New-Agents "$CMP/AGENTS.md" 'Level 2: Compliance' @(
  'Compliance skills are read-only. Never modify or delete a record.',
  'Every finding must cite a record identifier or a document.',
  'The review period is 90 days unless the user gives another one.')
New-Agents "$AU/AGENTS.md" 'Level 3: Compliance / Audit' @(
  'The review period is 180 days (overrides the department period).',
  'Rate every finding with a severity of low, medium or high.')
New-Agents "$DP/AGENTS.md" 'Level 3: Compliance / Data privacy' @(
  'Never display personal data in clear. Mask emails and phone numbers.',
  'Access requests must be answered within 30 days according to internal policy.')
New-Skill "$AU/skills/audit-trail-review" 'audit-trail-review' 'Review the audit log for unusual or unauthorized changes. Use when the user asks about audit trails, who changed a record or suspicious activity.' 'query_audit_log' @(
  'Retrieve audit log entries with query_audit_log for the review period.',
  'Flag changes made outside working hours or by unexpected users.',
  'List each flagged change with its record identifier.')
New-Skill "$AU/skills/finding-report" 'finding-report' 'Summarize audit findings by severity in a short report. Use when the user asks for an audit report, a findings summary or a list of open issues.' 'query_audit_log get_findings' @(
  'Retrieve the findings with get_findings.',
  'Group the findings by severity.',
  'Write a short summary with one line per finding.')
New-Skill "$DP/skills/pii-scan" 'pii-scan' 'Detect personal data such as emails, phone numbers and national ids in a text or dataset. Use when the user asks to check, scan or anonymize personal data.' 'scan_text' @(
  'Run scan_text on the provided content.',
  'List the type and the location of each match.',
  'Return the masked version of the content.')

# ---------- Summary ----------
$a = (Get-ChildItem departments -Recurse -Filter AGENTS.md).Count
$s = (Get-ChildItem departments -Recurse -Filter SKILL.md).Count
Write-Host "Done: $a AGENTS.md and $s SKILL.md under departments/ (plus the root AGENTS.md)."