from app.models.workflow_state import WorkflowState
from app.services.data_quality import analyze_dataset
from app.services.state_manager import StateManager
from backend.app.pipeline.base_stage import BaseStage

class QualityStage(BaseStage):

    def execute(self, context):

        context.report = analyze_dataset(
            context.dataframe
        )

        StateManager.transition(
            context,
            WorkflowState.ANALYZED
        )

        return context
