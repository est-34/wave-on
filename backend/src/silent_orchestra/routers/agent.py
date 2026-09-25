from fastapi import APIRouter, Depends
from ..bootstrap import get_agent_dependencies
from ..modules.agent import api
from ..schemas import (
    ObserveRequest,
    ObserveResponse,
    TeachRequest,
    TeachResponse,
    SuggestionRead,
    SuggestionResponse,
    SuggestionResponseRequest,
    PatternRead,
    FeedbackCreate,
    FeedbackResponse,
    DashboardResponse,
)

router = APIRouter(tags=["agent"])


@router.post("/observe", response_model=ObserveResponse)
def observe(payload: ObserveRequest, db=Depends(get_agent_dependencies)):
    return api.observe(
        payload=api.contracts.ObserveRequest(
            user_id=payload.user_id,
            context=api.contracts.ContextInput(**payload.context.model_dump()),
            gesture=api.contracts.GestureInput(**payload.gesture.model_dump()),
            attempt_inference=payload.attempt_inference,
        ),
        db=db,
    )


@router.post("/teach", response_model=TeachResponse)
def teach(payload: TeachRequest, db=Depends(get_agent_dependencies)):
    return api.teach(payload=api.contracts.TeachRequest(**payload.model_dump()), db=db)


@router.get("/suggestions", response_model=list[SuggestionRead])
def list_suggestions(
    user_id: str,
    status: str | None = None,
    db=Depends(get_agent_dependencies),
):
    return api.list_suggestions(user_id=user_id, status=status, db=db)


@router.post("/suggestions/{suggestion_id}/respond", response_model=SuggestionResponse)
def respond_suggestion(
    suggestion_id: str,
    payload: SuggestionResponseRequest,
    db=Depends(get_agent_dependencies),
):
    return api.respond_suggestion(
        suggestion_id=suggestion_id,
        payload=api.contracts.SuggestionResponseRequest(**payload.model_dump()),
        db=db,
    )


@router.get("/memories", response_model=list[PatternRead])
def list_memories(
    user_id: str,
    gesture_key: str | None = None,
    context_scope: str | None = None,
    db=Depends(get_agent_dependencies),
):
    return api.list_memories(
        user_id=user_id, gesture_key=gesture_key, context_scope=context_scope, db=db
    )


@router.post("/executions/{execution_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    execution_id: str,
    payload: FeedbackCreate,
    db=Depends(get_agent_dependencies),
):
    return api.submit_feedback(
        execution_id=execution_id,
        payload=api.contracts.FeedbackCreate(**payload.model_dump()),
        db=db,
    )


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user_id: str, db=Depends(get_agent_dependencies)):
    return api.dashboard(user_id=user_id, db=db)
