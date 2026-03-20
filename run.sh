#!/bin/bash
# Pseudoctor Business Reviewer - Data Processing Script

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " Pseudoctor Business Reviewer"
echo " Data Processing Pipeline"
echo "=========================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo ""
    echo "[Setup] Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Keep environment in sync with requirements
pip install -r requirements.txt

# Run data processor
echo ""
echo "[Processing] Running data processor..."
python scripts/data_processor.py "$@"

# Generate final report with embedded data
echo ""
echo "[Reporting] Building full HTML report..."
python scripts/create_final_report.py "$@"

# Validate consistency between analysis_data.json and embedded report chartData
echo ""
echo "[Validation] Checking analysis/report consistency..."
python - <<'PY'
import json
import sys
from pathlib import Path

analysis_path = Path("data/analysis_data.json")
report_path = Path("reports/report_with_data.html")

if not analysis_path.exists():
    print("Error: Missing data/analysis_data.json for consistency check")
    sys.exit(1)
if not report_path.exists():
    print("Error: Missing reports/report_with_data.html for consistency check")
    sys.exit(1)

analysis_data = json.loads(analysis_path.read_text(encoding="utf-8"))
overview = analysis_data.get("overview") or []
analysis_total_records = int(sum(int(float(row.get("rows", 0) or 0)) for row in overview))
analysis_total_sales = float(sum(float(row.get("sales_amount", 0) or 0) for row in overview))
analysis_months = list(analysis_data.get("months") or [])

report_html = report_path.read_text(encoding="utf-8")
marker = "const chartData ="
start = report_html.find(marker)
if start < 0:
    print("Error: Could not find chartData declaration in reports/report_with_data.html")
    sys.exit(1)

json_start = report_html.find("{", start)
if json_start < 0:
    print("Error: Could not find chartData JSON start")
    sys.exit(1)

depth = 0
in_string = False
escaped = False
json_end = -1
for i in range(json_start, len(report_html)):
    ch = report_html[i]
    if in_string:
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == '"':
            in_string = False
        continue

    if ch == '"':
        in_string = True
    elif ch == "{":
        depth += 1
    elif ch == "}":
        depth -= 1
        if depth == 0:
            json_end = i + 1
            break

if json_end < 0:
    print("Error: Could not parse chartData JSON block")
    sys.exit(1)

chart_data = json.loads(report_html[json_start:json_end])
report_total_records = int(chart_data.get("totalRecordsCount") or 0)
report_total_sales = float(sum(float(v or 0) for v in (chart_data.get("monthlySales") or [])))
report_months = list(chart_data.get("months") or [])

record_diff = report_total_records - analysis_total_records
sales_diff = report_total_sales - analysis_total_sales
month_mismatch = analysis_months != report_months

if record_diff != 0 or abs(sales_diff) > 0.01 or month_mismatch:
    print("Error: analysis/report consistency check failed")
    print(f"  totalRecordsCount: analysis={analysis_total_records}, report={report_total_records}, diff={record_diff}")
    print(f"  totalSales(sum by month): analysis={analysis_total_sales:.2f}, report={report_total_sales:.2f}, diff={sales_diff:.2f}")
    if month_mismatch:
        print(f"  months mismatch: analysis={analysis_months}, report={report_months}")
    sys.exit(1)

print("Consistency check passed.")
print(f"  totalRecordsCount={report_total_records}")
print(f"  totalSales(sum by month)={report_total_sales:.2f}")
print(f"  months={report_months}")
PY

# Check if data was generated
if [ -f "data/analysis_data.json" ]; then
    echo ""
    echo "=========================================="
    echo " SUCCESS!"
    echo "=========================================="
    echo "Data file: data/analysis_data.json"
    echo "Report:    reports/report_with_data.html"
    echo ""
    echo "To view the report, open the HTML file in your browser."
else
    echo ""
    echo "Error: Data file was not generated"
    exit 1
fi
