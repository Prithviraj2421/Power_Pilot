"""Ground truth for the benchmark: what each column *is*, and a handful of KPI values computed by hand-written pandas.

Run `python -m eval.labels.build_labels` to (re)write eval/labels/<dataset>.json from the tables below. The JSON files are
committed; they are the labels. Nothing here was derived from PowerPilot's output: columns were labelled from their names
and values, and the pipeline was run afterwards.

Labelling rules (also in eval/README.md)
* The label set is the product's own semantic taxonomy: customer, product, revenue, profit, cost, quantity, date, region,
  employee, identifier, unknown. Every column not listed below is `unknown`.
* `date`: a column holding a full calendar date or timestamp. A month name or a day-of-week number is not a date.
* `identifier`: a key that only identifies a row or an entity outside the taxonomy (invoice no., patient no., row id).
  A key that identifies a taxonomy entity takes that entity's label (customer id -> customer, employee id -> employee).
* `product`: names, codes or groupings of what is sold (stock code, description, category).
* `revenue` / `profit` / `cost`: money earned, money kept, money spent *as an amount*. A price per unit, a limit, a rate and
  a yes/no flag called "Revenue" are not revenue.
* `quantity`: how many units / events were counted (units sold, rentals, traffic volume).
* `region`: geography (country, state, city, region, postal code).
* The `domain` label is the closest of the product's six domains by the dataset's business function, or `unknown` when none fits.
  Several are judgement calls (bike sharing as logistics); `domain_label_confidence` says which.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE.parent / "datasets" / "raw"
MANIFEST = HERE.parent / "datasets" / "manifest.json"

# --- column labels: only the non-`unknown` columns are listed -------------------------------------

WEEKS = {f"W{i}": "quantity" for i in range(52)}

COLUMNS: dict[str, dict[str, str]] = {
    "uci_online_retail": {
        "InvoiceNo": "identifier", "StockCode": "product", "Description": "product", "Quantity": "quantity",
        "InvoiceDate": "date", "CustomerID": "customer", "Country": "region",
    },
    "uci_wholesale": {c: "revenue" for c in ["Fresh", "Milk", "Grocery", "Frozen", "Detergents_Paper", "Delicassen"]} | {"Region": "region"},
    "uci_online_shoppers": {"Region": "region"},
    "uci_sales_weekly": {"Product_Code": "product", "MIN": "quantity", "MAX": "quantity"} | WEEKS,
    "uci_credit_default": {"ID": "customer"},
    "uci_german_credit": {},
    "uci_real_estate": {"No": "identifier", "X1 transaction date": "date"},
    "uci_absenteeism": {"ID": "employee"},
    "uci_garment_employees": {"date": "date", "incentive": "cost"},
    "uci_heart_disease": {},
    "uci_diabetes_hospitals": {"encounter_id": "identifier", "patient_nbr": "identifier"},
    "uci_heart_failure": {},
    "uci_hcv": {"ID": "identifier"},
    "uci_breast_cancer": {"ID": "identifier"},
    "uci_bank_marketing": {},
    "uci_bike_sharing": {"instant": "identifier", "dteday": "date", "casual": "quantity", "registered": "quantity", "cnt": "quantity"},
    "uci_metro_traffic": {"date_time": "date", "traffic_volume": "quantity"},
    "uci_seoul_bike": {"Date": "date", "Rented Bike Count": "quantity"},
    "uci_predictive_maintenance": {"UID": "identifier", "Product ID": "product"},
    "uci_power_tetouan": {"DateTime": "date"},
    "synthetic_retail": {
        "order_id": "identifier", "order_date": "date", "customer_id": "customer", "product_name": "product", "category": "product",
        "region": "region", "quantity": "quantity", "sales_amount": "revenue", "profit": "profit",
    },
    "synthetic_finance": {
        "transaction_id": "identifier", "transaction_date": "date", "account_id": "identifier", "revenue": "revenue",
        "expense": "cost", "profit": "profit",
    },
    "synthetic_hr": {"employee_id": "employee", "hire_date": "date", "region": "region", "salary": "cost", "bonus": "cost"},
    "synthetic_healthcare": {"patient_id": "identifier", "admission_date": "date", "region": "region", "treatment_cost": "cost"},
    "golden_superstore": {
        "Row ID": "identifier", "Order ID": "identifier", "Order Date": "date", "Ship Date": "date", "Customer ID": "customer",
        "Customer Name": "customer", "Country": "region", "City": "region", "State": "region", "Postal Code": "region",
        "Region": "region", "Product ID": "product", "Category": "product", "Sub-Category": "product", "Product Name": "product",
        "Sales": "revenue", "Quantity": "quantity", "Profit": "profit",
    },
}

# Domain judgement calls: labelled "medium" when a reasonable person could disagree.
DOMAIN_CONFIDENCE = {
    "uci_online_shoppers": "medium", "uci_bike_sharing": "medium", "uci_metro_traffic": "medium", "uci_seoul_bike": "medium",
    "uci_predictive_maintenance": "medium", "uci_real_estate": "medium", "uci_garment_employees": "medium",
    "uci_power_tetouan": "medium", "uci_sales_weekly": "medium", "uci_wholesale": "medium",
}

# --- KPIs: name -> hand-written pandas on the raw file --------------------------------------------

Kpi = tuple[str, Callable[[pd.DataFrame], float]]


def _margin(df: pd.DataFrame, profit: str, sales: str) -> float:
    return df[profit].sum() / df[sales].sum()


KPIS: dict[str, list[Kpi]] = {
    "uci_online_retail": [
        ("Total units sold", lambda d: d["Quantity"].sum()),
        ("Line items", lambda d: len(d)),
        ("Distinct customers", lambda d: d["CustomerID"].nunique()),
        ("Distinct invoices", lambda d: d["InvoiceNo"].nunique()),
        ("Gross revenue (Quantity x UnitPrice)", lambda d: (d["Quantity"] * d["UnitPrice"]).sum()),
        ("Average unit price", lambda d: d["UnitPrice"].mean()),
    ],
    "uci_wholesale": [
        ("Total fresh spend", lambda d: d["Fresh"].sum()),
        ("Total milk spend", lambda d: d["Milk"].sum()),
        ("Total grocery spend", lambda d: d["Grocery"].sum()),
        ("Average fresh spend per customer", lambda d: d["Fresh"].mean()),
        ("Total spend, all categories", lambda d: d[["Fresh", "Milk", "Grocery", "Frozen", "Detergents_Paper", "Delicassen"]].sum().sum()),
    ],
    "uci_online_shoppers": [
        ("Purchase rate", lambda d: d["Revenue"].astype(float).mean()),
        ("Average product-related duration", lambda d: d["ProductRelated_Duration"].mean()),
        ("Total product-related pages", lambda d: d["ProductRelated"].sum()),
        ("Average bounce rate", lambda d: d["BounceRates"].mean()),
        ("Weekend share of sessions", lambda d: d["Weekend"].astype(float).mean()),
    ],
    "uci_sales_weekly": [
        ("Products", lambda d: d["Product_Code"].nunique()),
        ("Units sold in week 0", lambda d: d["W0"].sum()),
        ("Units sold in week 51", lambda d: d["W51"].sum()),
        ("Average weekly maximum", lambda d: d["MAX"].mean()),
    ],
    "uci_credit_default": [
        ("Default rate", lambda d: d["Y"].mean()),
        ("Average credit limit", lambda d: d["X1"].mean()),
        ("Total credit limit", lambda d: d["X1"].sum()),
        ("Average age", lambda d: d["X5"].mean()),
    ],
    "uci_german_credit": [
        ("Average duration (months)", lambda d: d["Attribute2"].mean()),
        ("Average credit amount", lambda d: d["Attribute5"].mean()),
        ("Total credit amount", lambda d: d["Attribute5"].sum()),
        ("Bad-credit rate", lambda d: (d["class"] == 2).mean()),
    ],
    "uci_real_estate": [
        ("Average price per unit area", lambda d: d["Y house price of unit area"].mean()),
        ("Average house age", lambda d: d["X2 house age"].mean()),
        ("Total convenience stores", lambda d: d["X4 number of convenience stores"].sum()),
        ("Highest price per unit area", lambda d: d["Y house price of unit area"].max()),
    ],
    "uci_absenteeism": [
        ("Total absence hours", lambda d: d["Absenteeism time in hours"].sum()),
        ("Average absence hours", lambda d: d["Absenteeism time in hours"].mean()),
        ("Employees", lambda d: d["ID"].nunique()),
        ("Average age", lambda d: d["Age"].mean()),
        ("Average service time", lambda d: d["Service time"].mean()),
    ],
    "uci_garment_employees": [
        ("Average actual productivity", lambda d: d["actual_productivity"].mean()),
        ("Total incentive", lambda d: d["incentive"].sum()),
        ("Total overtime", lambda d: d["over_time"].sum()),
        ("Average workers per team-day", lambda d: d["no_of_workers"].mean()),
        ("Records", lambda d: len(d)),
    ],
    "uci_heart_disease": [
        ("Average age", lambda d: d["age"].mean()),
        ("Average cholesterol", lambda d: d["chol"].mean()),
        ("Disease rate", lambda d: (d["num"] > 0).mean()),
    ],
    "uci_diabetes_hospitals": [
        ("Average time in hospital", lambda d: d["time_in_hospital"].mean()),
        ("Total medications", lambda d: d["num_medications"].sum()),
        ("Average lab procedures", lambda d: d["num_lab_procedures"].mean()),
        ("Distinct patients", lambda d: d["patient_nbr"].nunique()),
        ("Readmission rate", lambda d: (d["readmitted"] != "NO").mean()),
    ],
    "uci_heart_failure": [
        ("Death rate", lambda d: d["death_event"].mean()),
        ("Average age", lambda d: d["age"].mean()),
        ("Average ejection fraction", lambda d: d["ejection_fraction"].mean()),
        ("Average serum creatinine", lambda d: d["serum_creatinine"].mean()),
    ],
    "uci_hcv": [
        ("Average albumin", lambda d: d["ALB"].mean()),
        ("Average ALT", lambda d: d["ALT"].mean()),
        ("Average age", lambda d: d["Age"].mean()),
        ("Records", lambda d: d["ID"].nunique()),
    ],
    "uci_breast_cancer": [
        ("Malignant share", lambda d: (d["Diagnosis"] == "M").mean()),
        ("Average radius", lambda d: d["radius1"].mean()),
        ("Average area", lambda d: d["area1"].mean()),
    ],
    "uci_bank_marketing": [
        ("Subscription rate", lambda d: (d["y"] == "yes").mean()),
        ("Average balance", lambda d: d["balance"].mean()),
        ("Total balance", lambda d: d["balance"].sum()),
        ("Average call duration", lambda d: d["duration"].mean()),
        ("Average contacts per client", lambda d: d["campaign"].mean()),
    ],
    "uci_bike_sharing": [
        ("Total rentals", lambda d: d["cnt"].sum()),
        ("Average rentals per hour", lambda d: d["cnt"].mean()),
        ("Total casual rentals", lambda d: d["casual"].sum()),
        ("Total registered rentals", lambda d: d["registered"].sum()),
        ("Registered share", lambda d: d["registered"].sum() / d["cnt"].sum()),
    ],
    "uci_metro_traffic": [
        ("Average traffic volume", lambda d: d["traffic_volume"].mean()),
        ("Total traffic volume", lambda d: d["traffic_volume"].sum()),
        ("Peak traffic volume", lambda d: d["traffic_volume"].max()),
    ],
    "uci_seoul_bike": [
        ("Total rented bikes", lambda d: d["Rented Bike Count"].sum()),
        ("Average rented bikes per hour", lambda d: d["Rented Bike Count"].mean()),
        ("Peak rented bikes", lambda d: d["Rented Bike Count"].max()),
        ("Average temperature", lambda d: d["Temperature"].mean()),
    ],
    "uci_predictive_maintenance": [
        ("Machine failure rate", lambda d: d["Machine failure"].mean()),
        ("Average torque", lambda d: d["Torque"].mean()),
        ("Average air temperature", lambda d: d["Air temperature"].mean()),
        ("Average tool wear", lambda d: d["Tool wear"].mean()),
    ],
    "uci_power_tetouan": [
        ("Total zone 1 consumption", lambda d: d["Zone 1 Power Consumption"].sum()),
        ("Average zone 1 consumption", lambda d: d["Zone 1 Power Consumption"].mean()),
        ("Average temperature", lambda d: d["Temperature"].mean()),
    ],
    "synthetic_retail": [
        ("Total sales", lambda d: d["sales_amount"].sum()),
        ("Total profit", lambda d: d["profit"].sum()),
        ("Profit margin", lambda d: _margin(d, "profit", "sales_amount")),
        ("Average order value", lambda d: d["sales_amount"].sum() / d["order_id"].nunique()),
        ("Total units sold", lambda d: d["quantity"].sum()),
        ("Distinct customers", lambda d: d["customer_id"].nunique()),
    ],
    "synthetic_finance": [
        ("Total revenue", lambda d: d["revenue"].sum()),
        ("Total expense", lambda d: d["expense"].sum()),
        ("Total profit", lambda d: d["profit"].sum()),
        ("Profit margin", lambda d: _margin(d, "profit", "revenue")),
        ("Total budget", lambda d: d["budget_amount"].sum()),
    ],
    "synthetic_hr": [
        ("Headcount", lambda d: d["employee_id"].nunique()),
        ("Average salary", lambda d: d["salary"].mean()),
        ("Total bonus", lambda d: d["bonus"].sum()),
        ("Attrition rate", lambda d: d["attrition_flag"].mean()),
        ("Average tenure (years)", lambda d: d["tenure_years"].mean()),
    ],
    "synthetic_healthcare": [
        ("Total treatment cost", lambda d: d["treatment_cost"].sum()),
        ("Average length of stay", lambda d: d["length_of_stay_days"].mean()),
        ("Readmission rate", lambda d: d["readmission_flag"].mean()),
        ("Patients", lambda d: d["patient_id"].nunique()),
        ("Average age", lambda d: d["age"].mean()),
    ],
    "golden_superstore": [
        ("Total sales", lambda d: d["Sales"].sum()),
        ("Total profit", lambda d: d["Profit"].sum()),
        ("Profit margin", lambda d: _margin(d, "Profit", "Sales")),
        ("Average order value", lambda d: d["Sales"].sum() / d["Order ID"].nunique()),
        ("Distinct customers", lambda d: d["Customer ID"].nunique()),
        ("Total units sold", lambda d: d["Quantity"].sum()),
    ],
}


def build() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["datasets"]:
        ident = entry["id"]
        frame = pd.read_csv(RAW / f"{ident}.csv", low_memory=False)
        listed = COLUMNS[ident]
        missing = sorted(set(listed) - set(frame.columns))
        if missing:
            raise SystemExit(f"{ident}: labelled columns not in the file: {missing}")
        kpis = []
        for name, compute in KPIS[ident]:
            kpis.append({"name": name, "value": float(compute(frame))})
        label = {
            "id": ident,
            "title": entry["title"],
            "domain": entry["domain"],
            "domain_label_confidence": DOMAIN_CONFIDENCE.get(ident, "high"),
            "columns": {column: listed.get(column, "unknown") for column in frame.columns},
            "kpis": kpis,
        }
        (HERE / f"{ident}.json").write_text(json.dumps(label, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"{ident:28} {sum(v != 'unknown' for v in label['columns'].values()):>3} labelled / {len(frame.columns)} columns, {len(kpis)} KPIs")


if __name__ == "__main__":
    build()
