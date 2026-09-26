from app.services.cleaning_planner import create_cleaning_plan
from app.services.data_quality import analyze_dataset
from app.services.rule_engine import RuleEngine


class DatasetWorkflow:
    """Legacy quality-and-plan workflow behind the ``/upload`` route."""

    def process(self, context):
        # Step 1: profile the dataset.
        context.report = analyze_dataset(context.dataframe)

        # Step 2: evaluate business rules. The result is attached to the context
        # rather than discarded -- it was previously assigned to an unused local,
        # so every rule ran on every upload and the findings were thrown away.
        context.rule_issues = RuleEngine().evaluate(context)

        # Step 3: derive a cleaning plan from the profile.
        context.cleaning_plan = create_cleaning_plan(context.report)

        return context