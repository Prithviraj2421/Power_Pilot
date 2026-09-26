from app.models.workflow_state import WorkflowState


class StateManager:

    VALID_TRANSITIONS = {
        WorkflowState.CREATED: [WorkflowState.UPLOADED],
        WorkflowState.UPLOADED: [WorkflowState.ANALYZED],
        WorkflowState.ANALYZED: [WorkflowState.PLAN_READY],
        WorkflowState.PLAN_READY: [WorkflowState.CLEANED],
        WorkflowState.CLEANED: [WorkflowState.PROFILED],
        WorkflowState.PROFILED: [WorkflowState.KPI_READY],
        WorkflowState.KPI_READY: [WorkflowState.EXPORTED],
    }

    @staticmethod
    def transition(context, new_state):

        allowed = StateManager.VALID_TRANSITIONS.get(context.state, [])

        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {context.state.value} → {new_state.value}"
            )

        context.state = new_state

        return context