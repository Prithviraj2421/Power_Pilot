from app.rules.base_rule import BaseRule
from app.models.issue import Issue


class MissingValueRule(BaseRule):

    def evaluate(self, context):

        report = context.report

        total_missing = sum(
            report["missing_values"].values()
        )

        if total_missing == 0:
            return None

        return Issue(
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