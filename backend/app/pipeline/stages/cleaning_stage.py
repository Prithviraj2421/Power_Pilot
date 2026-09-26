from abc import abstractmethod

from backend.app.services import cleaning_engine
import backend.app.services.state_manager
from backend.app.pipeline.base_stage import BaseStage


class CleaningStage(BaseStage):

    @abstractmethod
    def execute(self, context):
        """Run the cleaning engine and update state."""
        context = cleaning_engine.execute(context)
        backend.app.services.state_manager.StateManager.transition(context, backend.app.services.state_manager.StateManagerState.CLEANED)
        
        return context

        