"""Regenerates the domain sample datasets in this directory.

Produces deterministic, domain-realistic CSVs that deliberately contain a small
amount of dirt -- missing values, a casing inconsistency, one exact duplicate
row and one numeric outlier -- so the Data Quality & Preparation Engine has
genuine work to do instead of scoring a trivially perfect dataset.

The RNG seed is fixed, so re-running this produces byte-identical output. Run it
only when you intend to change the fixtures; `tests/test_sample_datasets.py`
pins the expected shape, dirt and classified domain of each file.

    python tests/datasets/generate_samples.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
RNG = np.random.default_rng(20240501)
N = 60


def _dates(start: str, n: int) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(start, periods=n, freq="D")]


def retail() -> pd.DataFrame:
    categories = ["Electronics", "Clothing", "Home", "Grocery", "Sports"]
    regions = ["North", "South", "East", "West"]
    products = ["Laptop", "T-Shirt", "Blender", "Coffee Beans", "Yoga Mat",
                "Headphones", "Jacket", "Lamp", "Cereal", "Dumbbells"]

    quantity = RNG.integers(1, 9, N)
    unit_price = np.round(RNG.uniform(8.0, 1400.0, N), 2)
    discount = np.round(RNG.choice([0.0, 0.05, 0.10, 0.15, 0.20], N), 2)
    sales_amount = np.round(quantity * unit_price * (1 - discount), 2)
    profit = np.round(sales_amount * RNG.uniform(0.08, 0.34, N), 2)

    df = pd.DataFrame(
        {
            "order_id": np.arange(100001, 100001 + N),
            "order_date": _dates("2024-01-01", N),
            "customer_id": RNG.integers(1, 26, N),
            "product_name": RNG.choice(products, N),
            "category": RNG.choice(categories, N),
            "region": RNG.choice(regions, N),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount": discount,
            "sales_amount": sales_amount,
            "profit": profit,
        }
    )
    # Deliberate dirt
    df.loc[[7, 23, 41], "region"] = None          # missing categoricals
    df.loc[[12, 35], "profit"] = None             # missing numerics
    df.loc[5, "category"] = "electronics"         # casing inconsistency
    df.loc[50, "sales_amount"] = 480000.00        # outlier
    return df


def finance() -> pd.DataFrame:
    departments = ["Sales", "Marketing", "Engineering", "Operations", "Support"]
    cost_centers = ["CC-100", "CC-200", "CC-300", "CC-400"]

    revenue = np.round(RNG.uniform(12000.0, 190000.0, N), 2)
    expense = np.round(revenue * RNG.uniform(0.45, 0.95, N), 2)
    profit = np.round(revenue - expense, 2)
    budget = np.round(revenue * RNG.uniform(0.85, 1.20, N), 2)

    df = pd.DataFrame(
        {
            "transaction_id": [f"TXN-{i:05d}" for i in range(1, N + 1)],
            "transaction_date": _dates("2024-01-01", N),
            "account_id": RNG.integers(5000, 5031, N),
            "department": RNG.choice(departments, N),
            "cost_center": RNG.choice(cost_centers, N),
            "revenue": revenue,
            "expense": expense,
            "profit": profit,
            "budget_amount": budget,
            "budget_variance": np.round(revenue - budget, 2),
        }
    )
    df.loc[[9, 31], "cost_center"] = None
    df.loc[18, "expense"] = None
    df.loc[44, "revenue"] = 2750000.00            # outlier
    return df


def hr() -> pd.DataFrame:
    departments = ["Engineering", "Sales", "HR", "Finance", "Operations"]
    titles = ["Analyst", "Senior Analyst", "Manager", "Director", "Associate"]
    regions = ["North America", "EMEA", "APAC", "LATAM"]

    tenure = np.round(RNG.uniform(0.3, 18.0, N), 1)
    salary = np.round(42000 + tenure * RNG.uniform(1800, 5200, N), 2)
    bonus = np.round(salary * RNG.uniform(0.03, 0.22, N), 2)
    rating = np.round(RNG.uniform(2.1, 5.0, N), 1)

    df = pd.DataFrame(
        {
            "employee_id": [f"EMP-{i:04d}" for i in range(1, N + 1)],
            "hire_date": _dates("2015-03-01", N),
            "department": RNG.choice(departments, N),
            "job_title": RNG.choice(titles, N),
            "region": RNG.choice(regions, N),
            "tenure_years": tenure,
            "salary": salary,
            "bonus": bonus,
            "performance_rating": rating,
            "attrition_flag": RNG.choice([0, 1], N, p=[0.82, 0.18]),
        }
    )
    df.loc[[3, 27], "performance_rating"] = None
    df.loc[15, "bonus"] = None
    df.loc[8, "department"] = "engineering"       # casing inconsistency
    df.loc[52, "salary"] = 985000.00             # outlier
    return df


def healthcare() -> pd.DataFrame:
    departments = ["Cardiology", "Orthopedics", "Oncology", "Pediatrics", "Neurology"]
    diagnoses = ["I10", "E11", "J45", "M54", "N39", "K21"]
    regions = ["North", "South", "East", "West"]

    age = RNG.integers(18, 92, N)
    los = RNG.integers(1, 22, N)
    cost = np.round(1200 + los * RNG.uniform(680, 2400, N), 2)

    df = pd.DataFrame(
        {
            "patient_id": [f"PAT-{i:05d}" for i in range(1, N + 1)],
            "admission_date": _dates("2024-02-01", N),
            "department": RNG.choice(departments, N),
            "diagnosis_code": RNG.choice(diagnoses, N),
            "region": RNG.choice(regions, N),
            "age": age,
            "length_of_stay_days": los,
            "treatment_cost": cost,
            "readmission_flag": RNG.choice([0, 1], N, p=[0.86, 0.14]),
            "satisfaction_score": np.round(RNG.uniform(2.5, 5.0, N), 1),
        }
    )
    df.loc[[11, 38], "satisfaction_score"] = None
    df.loc[22, "region"] = None
    df.loc[47, "treatment_cost"] = 410000.00     # outlier
    return df


def main() -> None:
    builders = {
        "retail.csv": retail,
        "finance.csv": finance,
        "hr.csv": hr,
        "healthcare.csv": healthcare,
    }
    for name, build in builders.items():
        df = build()
        # One exact duplicate row per dataset so duplicate detection has a target.
        df = pd.concat([df, df.iloc[[2]]], ignore_index=True)
        path = OUT / name
        df.to_csv(path, index=False)
        print(f"{name}: {len(df)} rows x {len(df.columns)} cols -> {path}")


if __name__ == "__main__":
    main()
