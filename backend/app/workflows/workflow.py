from app.services.data_quality import analyze_dataset
from app.services.cleaning_planner import create_cleaning_plan
from app.services.rule_engine import RuleEngine


class DatasetWorkflow:

    def process(self, context):

        # Step 1
        context.report = analyze_dataset(
            context.dataframe
        )

        # Step 2
        issues = RuleEngine().evaluate(context)

        # Step 3
        context.cleaning_plan = create_cleaning_plan(
            context.report
        )

        return context