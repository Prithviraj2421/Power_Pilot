from app.rules.missing_value_rule import MissingValueRule


class RuleEngine:

    def __init__(self):

        self.rules = [

            MissingValueRule(),

        ]

    def evaluate(self, context):

        issues = []

        for rule in self.rules:

            issue = rule.evaluate(context)

            if issue:

                issues.append(issue)

        return issues   