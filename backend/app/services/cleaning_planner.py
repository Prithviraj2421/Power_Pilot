from app.models.issue import Issue
from app.models.cleaning_plan import CleaningPlan


def create_cleaning_plan(report):

    issues = []

    predicted_score = report["quality_score"]

    # Missing Values
    total_missing = sum(report["missing_values"].values())

    if total_missing > 0:

        issues.append(

            Issue(

                type="Missing Values",

                severity="High",

                affected_columns=[
                    col
                    for col, value in report["missing_values"].items()
                    if value > 0
                ],

                recommendation="Fill using Median",

                expected_improvement=5,

                message=f"{total_missing} missing values detected."

            )

        )

        predicted_score += 5

    # Duplicate Rows

    if report["duplicate_rows"] > 0:

        issues.append(

            Issue(

                type="Duplicate Rows",

                severity="Medium",

                affected_columns=[],

                recommendation="Remove Duplicate Rows",

                expected_improvement=4,

                message=f"{report['duplicate_rows']} duplicate rows detected."

            )

        )

        predicted_score += 4

    # Empty Columns

    if len(report["empty_columns"]) > 0:

        issues.append(

            Issue(

                type="Empty Columns",

                severity="Medium",

                affected_columns=report["empty_columns"],

                recommendation="Drop Empty Columns",

                expected_improvement=3,

                message="Completely empty columns found."

            )

        )

        predicted_score += 3

    predicted_score = min(predicted_score, 100)

    return CleaningPlan(

        current_score=report["quality_score"],

        predicted_score=predicted_score,

        issues=issues

    )