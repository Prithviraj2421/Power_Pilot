import pandas as pd


def analyze_dataset(df: pd.DataFrame):

    report = {}

    # -------------------------
    # Basic Information
    # -------------------------

    report["rows"] = len(df)
    report["columns"] = len(df.columns)

    report["column_names"] = list(df.columns)

    report["data_types"] = {
        col: str(dtype)
        for col, dtype in df.dtypes.items()
    }

    # -------------------------
    # Missing Values
    # -------------------------

    missing_values = df.isnull().sum()

    report["missing_values"] = {
        col: int(value)
        for col, value in missing_values.items()
    }

    total_missing = int(missing_values.sum())

    # -------------------------
    # Duplicate Rows
    # -------------------------

    duplicate_rows = int(df.duplicated().sum())

    report["duplicate_rows"] = duplicate_rows

    # -------------------------
    # Empty Columns
    # -------------------------

    empty_columns = [
        col
        for col in df.columns
        if df[col].isnull().all()
    ]

    report["empty_columns"] = empty_columns

    # -------------------------
    # Constant Columns
    # -------------------------

    constant_columns = [
        col
        for col in df.columns
        if df[col].nunique(dropna=False) <= 1
    ]

    report["constant_columns"] = constant_columns

    # -------------------------
    # Memory
    # -------------------------

    report["memory_usage_mb"] = float(round(
        df.memory_usage(deep=True).sum() / 1024 / 1024,
        2
    ))

    # -------------------------
    # Preview
    # -------------------------

    report["preview"] = df.head(10).where(
        pd.notnull(df.head(10)),
        None
    ).to_dict(orient="records")

    # -------------------------
    # Quality Score
    # -------------------------

    score = 100

    score -= duplicate_rows * 2

    score -= len(empty_columns) * 10

    score -= len(constant_columns) * 5

    score -= int(total_missing * 0.25)

    score = max(score, 0)

    report["quality_score"] = score

    # -------------------------
    # Recommendations
    # -------------------------

    recommendations = []

    if duplicate_rows:
        recommendations.append("Remove duplicate rows")

    if empty_columns:
        recommendations.append("Drop empty columns")

    if constant_columns:
        recommendations.append("Review constant columns")

    if total_missing:
        recommendations.append("Handle missing values")

    report["recommendations"] = recommendations

    return report
