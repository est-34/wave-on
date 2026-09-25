from sqlalchemy import func, select
from ....adapters.unit_of_work import SqlUnitOfWork
from ....adapters.mapping import (Context, GestureObservation, Action, GesturePattern, AgentSuggestion, Execution, Feedback)


class DemoRepository(SqlUnitOfWork):
    def dependent_counts(self, user_id):
        return {
            model.__table__.name: self.session.scalar(
                select(func.count()).select_from(model).where(model.user_id == user_id)
            )
            for model in (
                Context,
                GestureObservation,
                Action,
                GesturePattern,
                AgentSuggestion,
                Execution,
                Feedback,
            )
        }
