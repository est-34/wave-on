from sqlalchemy import (
    Table,
    Column,
    Integer,
    Float,
    Boolean,
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from ..database import Base
from ..modules.identity.domain.entities import User
from ..modules.agent.domain.entities import (
    Context,
    GestureObservation,
    Action,
    GesturePattern,
    AgentSuggestion,
    Execution,
    Feedback,
    utcnow,
)

user_table = Table(
    "users",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column("name", String(100), nullable=False),
    Column("created_at", DateTime(timezone=True), default=utcnow, nullable=False),
)

context_table = Table(
    "contexts",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("active_app", String(100), nullable=False),
    Column("activity", String(32), nullable=False),
    Column("space", String(100), default="unspecified", nullable=False),
    Column("device", String(100), default="laptop", nullable=False),
    Column("captured_at", DateTime(timezone=True), default=utcnow, nullable=False),
    CheckConstraint("activity IN ('presentation','music')", name="ck_context_activity"),
    Index("ix_contexts_user_activity", "user_id", "activity"),
)

gestureobservation_table = Table(
    "gesture_observations",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "context_id",
        String(36),
        ForeignKey("contexts.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("gesture_key", String(120), nullable=False),
    Column("gesture_embedding", JSON, nullable=False),
    Column("motion_type", String(50), nullable=False),
    Column("direction", String(30), default="none", nullable=False),
    Column("duration_ms", Integer, nullable=False),
    Column("speed", Float, nullable=True),
    Column("amplitude", Float, nullable=True),
    Column("frame_stored", Boolean, default=False, nullable=False),
    Column("detected_at", DateTime(timezone=True), default=utcnow, nullable=False),
    CheckConstraint("duration_ms >= 0", name="ck_observation_duration"),
    CheckConstraint("frame_stored = false", name="ck_raw_frame_never_stored"),
    CheckConstraint(
        "(speed IS NULL) = (amplitude IS NULL)", name="ck_observation_features_paired"
    ),
    Index("ix_observations_user_gesture", "user_id", "gesture_key"),
    Index("ix_observations_detected_at", "detected_at"),
)

action_table = Table(
    "actions",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "observation_id",
        String(36),
        ForeignKey("gesture_observations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    ),
    Column("action_type", String(64), nullable=False),
    Column("target", String(100), nullable=False),
    Column("parameters", JSON, default=dict, nullable=False),
    Column("executed_by", String(16), default="USER", nullable=False),
    Column("executed_at", DateTime(timezone=True), default=utcnow, nullable=False),
    CheckConstraint("executed_by IN ('USER','AGENT')", name="ck_action_executor"),
    Index("ix_actions_user_type", "user_id", "action_type"),
)

gesturepattern_table = Table(
    "gesture_patterns",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("gesture_key", String(120), nullable=False),
    Column("gesture_embedding", JSON, nullable=False),
    Column("motion_type", String(50), nullable=False),
    Column("direction", String(30), nullable=False),
    Column("intent", String(64), nullable=False),
    Column("context_scope", String(32), nullable=False),
    Column("target", String(100), nullable=False),
    Column("confidence", Float, default=0.0, nullable=False),
    Column("observation_count", Integer, default=0, nullable=False),
    Column("positive_feedback_count", Integer, default=0, nullable=False),
    Column("negative_feedback_count", Integer, default=0, nullable=False),
    Column("auto_execute", Boolean, default=False, nullable=False),
    Column("status", String(16), default="CANDIDATE", nullable=False),
    Column("created_at", DateTime(timezone=True), default=utcnow, nullable=False),
    Column(
        "updated_at",
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    ),
    CheckConstraint(
        "confidence >= 0 AND confidence <= 1", name="ck_pattern_confidence"
    ),
    CheckConstraint("observation_count >= 0", name="ck_pattern_count"),
    CheckConstraint(
        "status IN ('CANDIDATE','ACTIVE','REJECTED')", name="ck_pattern_status"
    ),
    CheckConstraint(
        "context_scope IN ('presentation','music')", name="ck_pattern_context"
    ),
    UniqueConstraint(
        "user_id",
        "gesture_key",
        "context_scope",
        "intent",
        name="uq_personal_gesture_memory",
    ),
    Index("ix_patterns_memory_lookup", "user_id", "context_scope", "status"),
)

agentsuggestion_table = Table(
    "agent_suggestions",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "gesture_pattern_id",
        String(36),
        ForeignKey("gesture_patterns.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("suggested_intent", String(64), nullable=False),
    Column("modified_intent", String(64), nullable=True),
    Column("reason", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("status", String(16), default="PENDING", nullable=False),
    Column("created_at", DateTime(timezone=True), default=utcnow, nullable=False),
    Column("responded_at", DateTime(timezone=True), nullable=True),
    CheckConstraint(
        "status IN ('PENDING','ACCEPTED','REJECTED','MODIFIED')",
        name="ck_suggestion_status",
    ),
    CheckConstraint(
        "confidence >= 0 AND confidence <= 1", name="ck_suggestion_confidence"
    ),
    Index("ix_suggestions_user_status", "user_id", "status"),
)

execution_table = Table(
    "executions",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "gesture_pattern_id",
        String(36),
        ForeignKey("gesture_patterns.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "observation_id",
        String(36),
        ForeignKey("gesture_observations.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("intent", String(64), nullable=False),
    Column("target", String(100), nullable=False),
    Column("parameters", JSON, default=dict, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("execution_mode", String(16), default="DRY_RUN", nullable=False),
    Column("status", String(16), nullable=False),
    Column("error_message", Text, nullable=True),
    Column("executed_at", DateTime(timezone=True), default=utcnow, nullable=False),
    CheckConstraint(
        "confidence >= 0 AND confidence <= 1", name="ck_execution_confidence"
    ),
    CheckConstraint("execution_mode IN ('DRY_RUN','OS')", name="ck_execution_mode"),
    CheckConstraint(
        "status IN ('SIMULATED','SUCCEEDED','FAILED')", name="ck_execution_status"
    ),
    Index("ix_executions_user_time", "user_id", "executed_at"),
)

feedback_table = Table(
    "feedback",
    Base.metadata,
    Column("id", String(36), primary_key=True, nullable=False),
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "gesture_pattern_id",
        String(36),
        ForeignKey("gesture_patterns.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "execution_id",
        String(36),
        ForeignKey("executions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    ),
    Column("feedback_type", String(32), nullable=False),
    Column("corrected_intent", String(64), nullable=True),
    Column("created_at", DateTime(timezone=True), default=utcnow, nullable=False),
    CheckConstraint(
        "feedback_type IN ('CORRECT','WRONG_ACTION','ACCIDENTAL_GESTURE','IGNORE')",
        name="ck_feedback_type",
    ),
    Index("ix_feedback_pattern_time", "gesture_pattern_id", "created_at"),
)

Base.registry.map_imperatively(
    User,
    user_table,
    properties={
        "contexts": relationship(
            "Context", back_populates="user", cascade="all, delete-orphan"
        )
    },
)

Base.registry.map_imperatively(
    Context,
    context_table,
    properties={
        "user": relationship("User", back_populates="contexts"),
        "observations": relationship(
            "GestureObservation", back_populates="context", cascade="all, delete-orphan"
        ),
    },
)

Base.registry.map_imperatively(
    GestureObservation,
    gestureobservation_table,
    properties={
        "context": relationship("Context", back_populates="observations"),
        "action": relationship(
            "Action",
            back_populates="observation",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    },
)

Base.registry.map_imperatively(
    Action,
    action_table,
    properties={
        "observation": relationship("GestureObservation", back_populates="action")
    },
)

Base.registry.map_imperatively(
    GesturePattern,
    gesturepattern_table,
    properties={
        "suggestions": relationship(
            "AgentSuggestion", back_populates="pattern", cascade="all, delete-orphan"
        ),
        "executions": relationship(
            "Execution", back_populates="pattern", cascade="all, delete-orphan"
        ),
    },
)

Base.registry.map_imperatively(
    AgentSuggestion,
    agentsuggestion_table,
    properties={
        "pattern": relationship("GesturePattern", back_populates="suggestions")
    },
)

Base.registry.map_imperatively(
    Execution,
    execution_table,
    properties={
        "pattern": relationship("GesturePattern", back_populates="executions"),
        "feedback": relationship(
            "Feedback", back_populates="execution", cascade="all, delete-orphan"
        ),
    },
)

Base.registry.map_imperatively(
    Feedback,
    feedback_table,
    properties={"execution": relationship("Execution", back_populates="feedback")},
)

# Preserve the historical model inspection API for scripts and integrations.
for mapper in Base.registry.mappers:
    mapper.class_.__tablename__ = mapper.local_table.name
