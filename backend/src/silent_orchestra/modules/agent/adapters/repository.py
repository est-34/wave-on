from datetime import datetime, timedelta, timezone
from sqlalchemy import desc, func, select, update
from ....adapters.unit_of_work import SqlUnitOfWork
from ..domain.entities import (Context, GestureObservation, Action, GesturePattern, AgentSuggestion, Execution, Feedback)
from ..domain.learning import EvidenceRow


class AgentRepository(SqlUnitOfWork):
    def observation_has_action(self, observation_id):
        return (
            self.session.scalar(
                select(Action.id).where(Action.observation_id == observation_id)
            )
            is not None
        )

    def duplicate_memory(self, intent, pattern):
        return self.session.scalar(
            select(GesturePattern).where(
                GesturePattern.user_id == pattern.user_id,
                GesturePattern.gesture_key == pattern.gesture_key,
                GesturePattern.context_scope == pattern.context_scope,
                GesturePattern.intent == intent,
                GesturePattern.id != pattern.id,
            )
        )

    def learning_evidence(self, user_id, gesture_key, activity, now, window, limit):
        return [
            EvidenceRow(action=row.Action, observation=row.GestureObservation)
            for row in self.session.execute(
                select(Action, GestureObservation)
                .join(
                    GestureObservation, Action.observation_id == GestureObservation.id
                )
                .join(Context, GestureObservation.context_id == Context.id)
                .where(
                    Action.user_id == user_id,
                    Action.executed_by == "USER",
                    Action.executed_at >= now - window,
                    Action.executed_at <= now,
                    GestureObservation.gesture_key == gesture_key,
                    Context.activity == activity,
                )
                .order_by(Action.executed_at.desc(), Action.id.desc())
                .limit(limit)
            ).all()
        ]

    def last_rejection(self, user_id, gesture_key, activity, intent):
        return self.session.scalar(
            select(func.max(AgentSuggestion.responded_at))
            .join(
                GesturePattern, AgentSuggestion.gesture_pattern_id == GesturePattern.id
            )
            .where(
                GesturePattern.user_id == user_id,
                GesturePattern.gesture_key == gesture_key,
                GesturePattern.context_scope == activity,
                AgentSuggestion.suggested_intent == intent,
                AgentSuggestion.status == "REJECTED",
            )
        )

    def matching_memory(self, user_id, gesture_key, activity, intent):
        return self.session.scalar(
            select(GesturePattern).where(
                GesturePattern.user_id == user_id,
                GesturePattern.gesture_key == gesture_key,
                GesturePattern.context_scope == activity,
                GesturePattern.intent == intent,
            )
        )

    def scope_memories(self, user_id, gesture_key, activity):
        return self.session.scalars(
            select(GesturePattern).where(
                GesturePattern.user_id == user_id,
                GesturePattern.gesture_key == gesture_key,
                GesturePattern.context_scope == activity,
            )
        ).all()

    def pending_suggestions(self, scope_patterns):
        return list(
            self.session.scalars(
                select(AgentSuggestion).where(
                    AgentSuggestion.gesture_pattern_id.in_(
                        [item.id for item in scope_patterns]
                    ),
                    AgentSuggestion.status == "PENDING",
                )
            )
        )

    def deactivate_other_memories(self, pattern):
        self.session.execute(
            update(GesturePattern)
            .where(
                GesturePattern.user_id == pattern.user_id,
                GesturePattern.gesture_key == pattern.gesture_key,
                GesturePattern.context_scope == pattern.context_scope,
                GesturePattern.id != pattern.id,
                GesturePattern.status == "ACTIVE",
            )
            .values(status="CANDIDATE", auto_execute=False)
        )

    def accidental_embeddings(self, context, observation):
        return list(
            self.session.scalars(
                select(GestureObservation.gesture_embedding)
                .join(Execution, Execution.observation_id == GestureObservation.id)
                .join(Feedback, Feedback.execution_id == Execution.id)
                .join(Context, Context.id == GestureObservation.context_id)
                .where(
                    Feedback.user_id == observation.user_id,
                    Feedback.feedback_type == "ACCIDENTAL_GESTURE",
                    Feedback.created_at
                    >= datetime.now(timezone.utc) - timedelta(minutes=5),
                    Context.activity == context.activity,
                )
            )
        )

    def executable_memories(self, context, observation):
        return list(
            self.session.scalars(
                select(GesturePattern).where(
                    GesturePattern.user_id == observation.user_id,
                    GesturePattern.context_scope == context.activity,
                    GesturePattern.status == "ACTIVE",
                    GesturePattern.auto_execute.is_(True),
                )
            )
        )

    def execution_feedback(self, execution):
        return self.session.scalar(
            select(Feedback).where(Feedback.execution_id == execution.id)
        )

    def pending_confirmation(self, activity, user_id):
        return self.session.scalar(
            select(AgentSuggestion)
            .join(
                GesturePattern, AgentSuggestion.gesture_pattern_id == GesturePattern.id
            )
            .where(
                AgentSuggestion.user_id == user_id,
                AgentSuggestion.status == "PENDING",
                GesturePattern.context_scope == activity,
            )
            .order_by(desc(AgentSuggestion.created_at))
        )

    def unrated_execution(self, activity, cutoff, user_id):
        return self.session.scalar(
            select(Execution)
            .join(GesturePattern, Execution.gesture_pattern_id == GesturePattern.id)
            .outerjoin(Feedback, Feedback.execution_id == Execution.id)
            .where(
                Execution.user_id == user_id,
                GesturePattern.context_scope == activity,
                Execution.executed_at >= cutoff,
                Feedback.id.is_(None),
            )
            .order_by(desc(Execution.executed_at))
        )

    def list_suggestions(self, user_id, status=None):
        stmt = select(AgentSuggestion).where(AgentSuggestion.user_id == user_id)
        if status:
            stmt = stmt.where(AgentSuggestion.status == status.upper())
        return list(
            self.session.scalars(stmt.order_by(desc(AgentSuggestion.created_at))).all()
        )

    def list_memories(self, user_id, gesture_key=None, context_scope=None, *, threshold):
        stmt = select(GesturePattern).where(
            GesturePattern.user_id == user_id,
            GesturePattern.status == "ACTIVE",
            GesturePattern.confidence >= threshold,
        )
        if gesture_key:
            stmt = stmt.where(GesturePattern.gesture_key == gesture_key)
        if context_scope:
            stmt = stmt.where(GesturePattern.context_scope == context_scope)
        return list(
            self.session.scalars(stmt.order_by(desc(GesturePattern.updated_at))).all()
        )

    def dashboard(self, user_id, *, suggestion_threshold):

        def recent(model, order_column, *conditions, limit: int | None = None) -> list:
            stmt = (
                select(model)
                .where(model.user_id == user_id, *conditions)
                .order_by(desc(order_column))
                .limit(limit)
            )
            return list(self.session.scalars(stmt).all())

        def total(model) -> int:
            return (
                self.session.scalar(
                    select(func.count(model.id)).where(model.user_id == user_id)
                )
                or 0
            )

        memories = recent(
            GesturePattern, GesturePattern.updated_at, GesturePattern.status == "ACTIVE"
        )
        candidates = recent(
            GesturePattern,
            GesturePattern.updated_at,
            GesturePattern.status == "CANDIDATE",
        )
        suggestions = recent(
            AgentSuggestion,
            AgentSuggestion.created_at,
            AgentSuggestion.status == "PENDING",
        )
        observations = recent(
            GestureObservation, GestureObservation.detected_at, limit=8
        )
        actions = recent(Action, Action.executed_at, limit=8)
        executions = recent(Execution, Execution.executed_at, limit=8)

        audit_rows = self.session.execute(
            select(Execution, GesturePattern, Feedback)
            .join(GesturePattern, Execution.gesture_pattern_id == GesturePattern.id)
            .outerjoin(Feedback, Feedback.execution_id == Execution.id)
            .where(Execution.user_id == user_id)
            .order_by(desc(Execution.executed_at))
            .limit(10)
        ).all()
        execution_audit = [
            {
                "id": execution.id,
                "executed_at": execution.executed_at,
                "gesture_key": pattern.gesture_key,
                "motion_type": pattern.motion_type,
                "direction": pattern.direction,
                "context_scope": pattern.context_scope,
                "intent": execution.intent,
                "target": execution.target,
                "confidence": execution.confidence,
                "execution_mode": execution.execution_mode,
                "status": execution.status,
                "error_message": execution.error_message,
                "feedback_type": feedback.feedback_type if feedback else None,
            }
            for execution, pattern, feedback in audit_rows
        ]

        events = (
            [
                {
                    "time": item.detected_at,
                    "type": "observation",
                    "title": f"{item.motion_type} / {item.direction}",
                    "detail": "원본 프레임은 저장하지 않고 특징 벡터만 기록",
                }
                for item in observations
            ]
            + [
                {
                    "time": item.executed_at,
                    "type": "action",
                    "title": item.action_type,
                    "detail": f"사용자 후속 행동 / {item.target}",
                }
                for item in actions
            ]
            + [
                {
                    "time": item.executed_at,
                    "type": "execution",
                    "title": item.intent,
                    "detail": item.error_message
                    or f"Agent {item.status} / confidence {item.confidence:.0%}",
                    "status": item.status,
                }
                for item in executions
            ]
        )
        events.sort(key=lambda event: event["time"], reverse=True)

        return {
            "context": next(iter(recent(Context, Context.captured_at, limit=1)), None),
            "counts": {
                "observations": total(GestureObservation),
                "learned_memories": len(memories),
                "pending_suggestions": len(suggestions),
                "feedback": total(Feedback),
            },
            "memories": memories,
            "candidates": candidates,
            "suggestions": suggestions,
            "events": events[:12],
            "execution_audit": execution_audit,
            "threshold": suggestion_threshold,
        }


