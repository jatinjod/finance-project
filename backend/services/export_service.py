# backend/services/export_service.py
# CSV and PDF export for reports and transactions

import io
import csv
from datetime import date
from models.income import Income
from models.expense import Expense


def export_transactions_csv(user_id, year=None, month=None,
                             trans_type='all'):
    """
    Export income and/or expense transactions as CSV.
    Returns a StringIO object ready to be sent as a file.
    """
    today = date.today()
    year  = year  or today.year
    month = month or today.month

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Date', 'Type', 'Category', 'Amount', 'Note'
    ])

    rows = []

    # Income records
    if trans_type in ('income', 'all'):
        income_q = Income.query.filter_by(user_id=user_id)
        if month and year:
            from sqlalchemy import extract
            from extensions import db
            income_q = income_q.filter(
                extract('month', Income.date) == month,
                extract('year',  Income.date) == year
            )
        for r in income_q.all():
            rows.append([
                r.date.strftime('%Y-%m-%d') if r.date else '',
                'Income',
                r.category.name if r.category else 'Unknown',
                f"{float(r.amount):.2f}",
                r.note or ''
            ])

    # Expense records
    if trans_type in ('expense', 'all'):
        expense_q = Expense.query.filter_by(user_id=user_id)
        if month and year:
            from sqlalchemy import extract
            from extensions import db
            expense_q = expense_q.filter(
                extract('month', Expense.date) == month,
                extract('year',  Expense.date) == year
            )
        for r in expense_q.all():
            rows.append([
                r.date.strftime('%Y-%m-%d') if r.date else '',
                'Expense',
                r.category.name if r.category else 'Unknown',
                f"{float(r.amount):.2f}",
                r.note or ''
            ])

    # Sort rows by date
    rows.sort(key=lambda x: x[0], reverse=True)

    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return output


def export_monthly_report_csv(user_id, year, month):
    """
    Export a formatted monthly summary report as CSV.
    """
    from services.monthly_analysis import get_monthly_summary

    summary = get_monthly_summary(user_id, year, month)
    output  = io.StringIO()
    writer  = csv.writer(output)

    # Report header
    writer.writerow([
        f"Monthly Financial Report — {summary['month_name']} {year}"
    ])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Income',   f"₹{summary['total_income']:,.2f}"])
    writer.writerow(['Total Expenses', f"₹{summary['total_expenses']:,.2f}"])
    writer.writerow(['Balance',        f"₹{summary['balance']:,.2f}"])
    writer.writerow(['Savings Rate',   f"{summary['savings_rate']}%"])
    writer.writerow([])

    # Expense by category
    writer.writerow(['Category', 'Amount Spent'])
    for cat, amt in summary['expense_by_category'].items():
        writer.writerow([cat, f"₹{amt:,.2f}"])
    writer.writerow([])

    # Income by source
    writer.writerow(['Income Source', 'Amount Received'])
    for source, amt in summary['income_by_source'].items():
        writer.writerow([source, f"₹{amt:,.2f}"])

    output.seek(0)
    return output


def generate_pdf_report(user_id, year, month):
    """
    Generate a simple PDF monthly report.
    Uses only Python standard library — no external PDF lib needed.
    Returns HTML string that the browser can print as PDF.
    """
    from services.monthly_analysis import get_monthly_summary

    summary  = get_monthly_summary(user_id, year, month)
    today    = date.today()

    # Build category rows
    cat_rows = ''
    for cat, amt in summary['expense_by_category'].items():
        pct      = round(amt / summary['total_expenses'] * 100, 1) \
                   if summary['total_expenses'] > 0 else 0
        cat_rows += f"""
            <tr>
              <td>{cat}</td>
              <td>₹{amt:,.2f}</td>
              <td>{pct}%</td>
            </tr>"""

    income_rows = ''
    for src, amt in summary['income_by_source'].items():
        income_rows += f"""
            <tr><td>{src}</td><td>₹{amt:,.2f}</td></tr>"""

    top_exp_rows = ''
    for tx in summary.get('top_expenses', []):
        top_exp_rows += f"""
            <tr>
              <td>{tx.get('date','')}</td>
              <td>{tx.get('category_name','')}</td>
              <td>₹{float(tx.get('amount',0)):,.2f}</td>
              <td>{tx.get('note','—')}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Report — {summary['month_name']} {year}</title>
<style>
  body {{
    font-family: Arial, sans-serif; margin: 40px;
    color: #1e293b; font-size: 13px;
  }}
  .header  {{ background:#1e293b; color:#fff; padding:20px; border-radius:8px; }}
  .header h1 {{ margin:0; font-size:1.4rem; }}
  .header p  {{ margin:5px 0 0; opacity:.7; font-size:.85rem; }}
  .summary-grid {{
    display:grid; grid-template-columns:repeat(4,1fr);
    gap:16px; margin:24px 0;
  }}
  .summary-box {{
    border:1px solid #e2e8f0; border-radius:8px; padding:16px;
  }}
  .summary-box .label {{ color:#64748b; font-size:.75rem; margin-bottom:4px; }}
  .summary-box .value {{ font-size:1.2rem; font-weight:700; color:#1e293b; }}
  .income-val  {{ color:#16a34a; }}
  .expense-val {{ color:#dc2626; }}
  h2 {{
    font-size:1rem; border-bottom:2px solid #e2e8f0;
    padding-bottom:8px; margin:24px 0 12px;
  }}
  table {{ width:100%; border-collapse:collapse; font-size:.85rem; }}
  th {{
    background:#f8fafc; color:#64748b; padding:10px 12px;
    text-align:left; border-bottom:1px solid #e2e8f0;
  }}
  td {{
    padding:9px 12px; border-bottom:1px solid #f1f5f9;
    color:#334155;
  }}
  tr:hover td {{ background:#f8fafc; }}
  .footer {{
    margin-top:40px; border-top:1px solid #e2e8f0;
    padding-top:12px; color:#94a3b8; font-size:.75rem;
    text-align:center;
  }}
  @media print {{
    body {{ margin:20px; }}
    .no-print {{ display:none; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>Monthly Financial Report</h1>
  <p>{summary['month_name']} {year} &nbsp;·&nbsp; Generated on {today.strftime('%d %b %Y')}</p>
</div>

<div class="summary-grid">
  <div class="summary-box">
    <div class="label">Total Income</div>
    <div class="value income-val">₹{summary['total_income']:,.2f}</div>
  </div>
  <div class="summary-box">
    <div class="label">Total Expenses</div>
    <div class="value expense-val">₹{summary['total_expenses']:,.2f}</div>
  </div>
  <div class="summary-box">
    <div class="label">Balance</div>
    <div class="value" style="color:{'#16a34a' if summary['balance']>=0 else '#dc2626'}">
      ₹{summary['balance']:,.2f}
    </div>
  </div>
  <div class="summary-box">
    <div class="label">Savings Rate</div>
    <div class="value">{summary['savings_rate']}%</div>
  </div>
</div>

<h2>Expense by Category</h2>
<table>
  <thead>
    <tr><th>Category</th><th>Amount</th><th>% of Total</th></tr>
  </thead>
  <tbody>
    {cat_rows if cat_rows else '<tr><td colspan="3">No expense data</td></tr>'}
  </tbody>
</table>

<h2>Income by Source</h2>
<table>
  <thead><tr><th>Source</th><th>Amount</th></tr></thead>
  <tbody>
    {income_rows if income_rows else '<tr><td colspan="2">No income data</td></tr>'}
  </tbody>
</table>

<h2>Top Expenses This Month</h2>
<table>
  <thead><tr><th>Date</th><th>Category</th><th>Amount</th><th>Note</th></tr></thead>
  <tbody>
    {top_exp_rows if top_exp_rows else '<tr><td colspan="4">No data</td></tr>'}
  </tbody>
</table>

<div class="footer">
  AI-Powered Personal Finance System &nbsp;·&nbsp;
  This report is auto-generated and is for personal reference only.
</div>

<div class="no-print" style="text-align:center;margin-top:30px">
  <button onclick="window.print()"
          style="background:#4361ee;color:#fff;border:none;
                 padding:10px 24px;border-radius:8px;
                 font-size:.9rem;cursor:pointer">
    🖨️ Print / Save as PDF
  </button>
</div>

</body>
</html>"""

    return html