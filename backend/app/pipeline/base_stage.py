from abc import ABC, abstractmethod

class BaseStage(ABC):

    @abstractmethod
    def execute(self, context):
        pass