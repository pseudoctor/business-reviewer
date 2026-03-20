# Business Sales & Inventory Turnover Analysis Report Template Specification

## Report Overview

**Report Name:** Business Sales & Inventory Turnover Analysis Report

**Data Period:** Typically 4 months (e.g., October 2025 - January 2026)

**Generation Date:** Date of report generation

**Data Source Files:**
- Monthly sales data files: `202510.xlsx`, `202511.xlsx`, `202512.xlsx`, `202601.xlsx`, etc.
- Inventory data file: `202601-inventory.xlsx`

---

## Report Structure

### I. Executive Summary

#### 1.1 KPI Cards (4 cards)
- **Sales Amount**: Total sales amount cumulative
- **Sales Quantity**: Total sales quantity cumulative
- **Average Transaction Value (ATV)**: Sales Amount / Sales Quantity
- **Inventory Turnover Rate**: Total Inventory / Monthly Sales

#### 1.2 Brand Sales Detail Table
**Table Fields:**
- Brand
- Sales Amount
- Sales Quantity
- Amount Percentage
- Quantity Percentage

**Tab Switching:**
- Cumulative: Cumulative data for all months
- Current Month: Data for the most recent month

#### 1.3 Key Findings
- Data Overview (record count, store count, SKU count, brand count)
- Sales Trends
- Brand Concentration
- Store Contribution
- Inventory Risks

---

### II. Dimensional Analysis

#### (I) Time Series Analysis

**1. Monthly Sales Amount Trend**
- Chart Type: Line Chart
- X-Axis: Month
- Y-Axis: Sales Amount

**2. Daily Sales Amount Trend**
- Chart Type: Line Chart
- X-Axis: Date
- Y-Axis: Sales Amount

**3. Brand Monthly Sales Amount Comparison**
- Chart Type: Stacked Bar Chart
- X-Axis: Month
- Y-Axis: Sales Amount
- Series: Each Brand

**4. Sales Quantity Monthly Trend**
- Chart Type: Line Chart
- X-Axis: Month
- Y-Axis: Sales Quantity

#### (II) Dimensional Comparison Analysis

**1. Brand Product Dimension Analysis**

**1.1 Brand Sales Details**
- Uses same data as brand sales details in Executive Summary
- Includes tab switching (cumulative/current month)

**1.2 Brand Sales Amount Percentage**
- Chart Type: Pie Chart
- Shows each brand's sales amount percentage

**1.3 Brand Sales Quantity Percentage**
- Chart Type: Pie Chart
- Shows each brand's sales quantity percentage

**1.4 Brand Sales Quantity Comparison**
- Chart Type: Bar Chart
- X-Axis: Brand
- Y-Axis: Sales Quantity

**1.5 Brand Monthly Percentage Change**
- Table showing each brand's percentage changes in Nov, Dec, Jan

**1.6 Top 20 Products Sales Amount**
- Chart Type: Horizontal Bar Chart
- Shows top 20 products by sales amount

**1.7 Top 30 Product Ranking Changes**
- Table Fields: Product, Nov Rank, Dec Rank, Jan Rank, Change
- Change indicated with arrows ↑↓, color coded (red=down, green=up)

**1.8 Hot Product Stability (TOP 10)**
- Chart Type: Horizontal Dual-Axis Bar Chart + Table
- Left Axis: Months in Top10
- Right Axis: Sales within Top10
- Table below shows detailed data

**2. Store Dimension Analysis**

**2.1 Top 20 Stores Sales Amount**
- Chart Type: Horizontal Bar Chart

**2.2 Top 10 Stores Performance**
- Table Fields: Store, Sales Amount, Percentage

**2.3 Top 30 Stores Ranking Changes**
- Table Fields: Store, Nov Rank, Dec Rank, Jan Rank

**2.4 Top 20 Stores Stability (Months in Top20)**
- Chart Type: Horizontal Dual-Axis Bar Chart + Table
- Left Axis: Months in Top20
- Right Axis: Sales within Top20

**2.5 Top 5 Store Efficiency Radar Chart**
- Chart Type: Radar Chart
- Dimensions: Sales, ATV, SKU Coverage, Active Days, Product Turnover
- Shows Top5 store comparison

#### (III) Cross Analysis

**3.1 Brand×Store Top10 Combinations**
- Table Fields: Brand, Store, Sales Amount
- Shows top10 combinations of each brand in each store

**3.2 High-Performance Store Feature Comparison (TOP10 vs All Store Average)**
- Table Fields: Metric, TOP10, All Store Average
- Metrics: ATV, SKU Coverage, Active Days Percentage

#### (IV) Structure & Concentration Analysis

**4.1 Concentration Metrics Cards**
- Brand Concentration: CR3, CR5
- SKU Concentration: Top20 Products Percentage
- Store Concentration: Top10 Store Percentage, Top20 Store Percentage, Gini Coefficient

**4.2 Product Sales Concentration**
- Chart Type: Pareto Chart (Dual-Axis)
- Bar Chart: Top10 Product Sales Amount
- Line Chart: Cumulative Percentage

**4.3 Store Sales Distribution (Cumulative Percentage)**
- Chart Type: Line Chart
- X-Axis: Top5, Top10, Top15, Top20, Top25, Top30
- Y-Axis: Cumulative Sales Percentage

---

### III. Inventory Risk Analysis

#### 3.1 Inventory Turnover Overview
**Table Fields:**
- Product Name
- Inventory Quantity
- Past 3 Months Average Monthly Sales Quantity
- Inventory/Sales Ratio

**Display:** Top 10 products (sorted by inventory/sales ratio)

#### 3.2 Risk Warning Table
**Table Fields:**
- Product Barcode
- Product Name
- Brand
- Inventory
- Monthly Average Sales
- Inventory Turnover (Sales/Inventory)
- Risk Level

**Risk Classification Standards:**
- 🔴 Red High Risk: Inventory/Sales Ratio ≥ 20
- 🟡 Yellow Medium Risk: 5 ≤ Inventory/Sales Ratio < 20
- 🟢 Green Low Risk: Inventory/Sales Ratio < 5

**Sorting:** From high risk to low risk

---

### IV. Appendix

#### 4.1 Data Sources
- List all data files

#### 4.2 Data Quality
- Data volume (number of rows)
- Number of fields
- Key field completeness
- Abnormal data notes

---

## Core Calculation Logic

### 1. Basic Metrics Calculation

#### Sales Amount
```
Total Sales Amount = SUM(sales_amount field of all records)
```

#### Sales Quantity
```
Total Sales Quantity = SUM(sales_quantity field of all records)
```

#### Average Transaction Value (ATV)
```
ATV = Total Sales Amount / Total Sales Quantity
```

#### Inventory Turnover Rate
```
Inventory Turnover Rate = Total Inventory Quantity / Monthly Sales Quantity
```

### 2. Brand Analysis

#### Brand Sales Amount
```
Group by Brand -> SUM(Sales Amount)
```

#### Brand Percentage
```
Brand Sales Amount Percentage = Brand Sales Amount / Total Sales Amount × 100%
```

#### CR3 / CR5
```
CR3 = Sum of Top3 Brand Sales Amount Percentages
CR5 = Sum of Top5 Brand Sales Amount Percentages
```

### 3. Product Analysis

#### Top N Product Ranking
```
Sort by Sales Amount Descending -> Take first N
```

#### Product Stability
```
Months in Top10 = Number of months the product appears in monthly Top10
Sales within Top10 = Sum of sales when product is in Top10
```

### 4. Store Analysis

#### Store Sales Ranking
```
Group by Store -> SUM(Sales Amount) -> Sort Descending
```

#### Store Stability
```
Months in Top20 = Number of months the store appears in monthly Top20
```

#### Gini Coefficient
```
Used to measure inequality of store sales distribution
Gini = 0 indicates complete equality, Gini = 1 indicates complete inequality
```

### 5. Inventory Analysis

#### Past 3 Months Average Sales Quantity
```
Average Sales Quantity = (Nov Sales Quantity + Dec Sales Quantity + Jan Sales Quantity) / 3
```

#### Inventory/Sales Ratio
```
Inventory/Sales Ratio = Inventory Quantity / Past 3 Months Average Sales Quantity
```

**Note:** If average sales quantity is 0, set ratio to 999 (infinity)

#### Inventory Turnover Rate
```
Inventory Turnover Rate = Monthly Average Sales Quantity / Inventory Quantity
```

### 6. Risk Level Classification

```python
def get_risk_level(ratio):
    if ratio >= 20:
        return "red"    # High Risk
    elif ratio >= 5:
        return "yellow" # Medium Risk
    else:
        return "green"  # Low Risk
```

---

## Data Processing Specifications

### Data Loading
```python
import pandas as pd

# Load sales data
sales_files = {
    "2025-10": "path/to/202510.xlsx",
    "2025-11": "path/to/202511.xlsx",
    "2025-12": "path/to/202512.xlsx",
    "2026-01": "path/to/202601.xlsx"
}

# Load inventory data
inventory_file = "path/to/202601-inventory.xlsx"
```

### Data Cleaning
```python
# Standardize column names
df.columns = df.columns.str.strip()

# Convert date format
df['sales_time'] = pd.to_datetime(df['sales_time'], errors='coerce')
```

### Data Aggregation
```python
# Aggregate by brand
brand_sales = df.groupby('brand')['sales_amount'].sum()

# Aggregate by product
product_sales = df.groupby('product_name').agg({
    'sales_amount': 'sum',
    'sales_quantity': 'sum'
})

# Aggregate by store
store_sales = df.groupby('store_name')['sales_amount'].sum()
```

---

## Style Specifications

### Color Scheme
```css
--primary: #1a237e;   /* Deep Blue - Primary */
--blue: #2196f3;      /* Blue - Secondary */
--green: #4caf50;     /* Green - Positive */
--red: #f44336;       /* Red - Negative/Warning */
--bg: #f5f7fb;        /* Background */
--card: #ffffff;      /* Card Background */
--text: #0f172a;      /* Text Color */
--muted: #6b7280;     /* Muted Text */
```

### Brand Color Tags
- Brand A: Blue background `#dbeafe`, Dark blue text `#1e40af`
- Brand B: Yellow background `#fef3c7`, Brown text `#92400e`
- Brand C: Green background `#d1fae5`, Dark green text `#065f46`
- Brand D: Pink background `#fce7f3`, Pink text `#9d174d`

### Risk Level Styles
- Red High Risk: `risk-red`
- Yellow Medium Risk: `risk-yellow`
- Green Low Risk: `risk-green`

---

## Chart Configuration Specifications

### Chart Type Mapping
| Analysis Dimension | Chart Type | Description |
|--------------------|------------|-------------|
| Trend Analysis | Line Chart | Show time series changes |
| Comparison Analysis | Bar Chart | Horizontal comparison |
| Percentage Analysis | Pie Chart | Show distribution |
| Cumulative Analysis | Stacked Bar Chart | Show composition changes |
| Dual-Metric Analysis | Multi-Axis Chart | Display two metrics simultaneously |
| Ranking Analysis | Horizontal Bar Chart | Easy to read long labels |
| Multi-Dimensional Comparison | Radar Chart | Multi-dimensional comprehensive comparison |
| Concentration | Pareto Chart | Bar chart + cumulative line |

### Chart.js Standard Configuration
```javascript
{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top'  // or 'bottom', 'right', 'left'
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      title: {
        display: true,
        text: 'Y-Axis Title'
      }
    }
  }
}
```

---

## Tech Stack

- **HTML5** - Page structure
- **CSS3** - Styling (Grid + Flexbox layout)
- **JavaScript (ES6+)** - Interactive logic
- **Chart.js 4.4.1** - Chart library
- **Pandas** - Data processing
- **Python 3.x** - Data calculation

---

## Data File Naming Conventions

**Sales Data:** `YYYYMM.xlsx` (e.g., 202601.xlsx)
**Inventory Data:** `YYYYMM-inventory.xlsx` (e.g., 202601-inventory.xlsx)

**Key Fields:**
- `sales_time` - Sales date and time
- `product_name` - Product name
- `brand` - Brand name
- `store_name` - Store name
- `sales_amount` - Sales amount
- `sales_quantity` - Sales quantity
- `product_code` - Product barcode
- `quantity` - Inventory quantity

---

## Quality Checklist

### Data Completeness Check
- [ ] All sales data files loaded
- [ ] Inventory data file loaded
- [ ] No duplicate data
- [ ] No missing key fields

### Calculation Accuracy Check
- [ ] Total sales amount = Sum of monthly sales amounts
- [ ] Total sales quantity = Sum of monthly sales quantities
- [ ] Sum of brand percentages = 100%
- [ ] Inventory/sales ratio calculated correctly
- [ ] Risk level classification correct

### Report Completeness Check
- [ ] All sections complete
- [ ] All charts display correctly
- [ ] All table data correct
- [ ] Tab switching functions properly
- [ ] Risk warning table sorted by risk level

---

## Template Update History

| Version | Date | Update Content | Updated By |
|---------|------|---------------|------------|
| v1.0 | 2026-01-31 | Initial version | Claude |
|        |        | Defined report structure, calculation logic, style specifications |         |

---

## Usage Instructions

1. **Prepare Data Files**
   - Ensure sales data files are named correctly (YYYYMM.xlsx format)
   - Ensure inventory data files are named correctly (YYYYMM-inventory.xlsx format)
   - Ensure data files are in the designated directory

2. **Run Data Calculation Script**
   - Execute Python script to calculate all metrics
   - Generate chartData data structure

3. **Generate HTML Report**
   - Use template HTML structure
   - Fill with calculated data
   - Verify all charts and data

4. **Quality Check**
   - Use quality checklist to verify each item
   - Open report in browser to verify display
   - Confirm all data and charts are correct

5. **Export/Share**
   - HTML format can be opened directly in browser
   - Can be printed to PDF for sharing
   - Can be screenshotted for presentations

---

**Template Maintainer:** Data Analysis Team
**Last Updated:** 2026-01-31
**Template Status:** ✅ Confirmed
