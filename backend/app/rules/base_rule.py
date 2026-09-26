from abc import ABC, abstractmethod

from app.models.issue import Issue


class BaseRule(ABC):

    @abstractmethod
    def evaluate(self, context):
        pass