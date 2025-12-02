# Human Task Workflows Extension

Stage-based workflows with human-triggered transitions, approvals, comments, and audit trails.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FORECAST CYCLE                          │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────┤
│  Upload  │ Classify │  Review  │ Forecast │  Final   │ Complete│
│    ●     │    ○     │    ○     │    ○     │    ○     │    ○    │
├──────────┴──────────┴──────────┴──────────┴──────────┴─────────┤
│ Assignee: @john     │ Comments: 3  │ Last update: 2h ago       │
└─────────────────────────────────────────────────────────────────┘
```

**This is NOT:**
- DAG orchestration (use Airflow/Prefect)
- Automated pipelines (use Jobs/Queue)
- BPMN workflows (use Camunda/SpiffWorkflow)

**This IS:**
- Human-triggered stage transitions
- Approval workflows with comments
- Stage-based tracking with audit trail
- Role-based step permissions

## When to Use This

**Add this extension when:**
- Multi-step approval processes needed
- Stage-based tracking (upload → review → approve)
- Human-in-the-loop operations
- Need comments and collaboration per stage

**Don't use when:**
- Simple status field suffices
- Automated pipelines (use Jobs instead)
- Complex BPMN with parallel paths (use Camunda)
- Single-user operations

## Tech Stack Options

| Option | Complexity | Best For |
|--------|------------|----------|
| `transitions` library | Low | Simple 3-7 stage workflows |
| `django-viewflow/viewflow.fsm` | Medium | Django/FastAPI integration |
| `SpiffWorkflow` | High | Full BPMN, visual designer |
| `Temporal.io` | High | Long-running, fault-tolerant |

**Recommended:** `transitions` library for most cases.

## Implementation Effort

| Phase | Effort | Description |
|-------|--------|-------------|
| Core models | 2-3 days | Workflow, stages, history |
| State machine | 2-3 days | transitions integration |
| API routes | 2-3 days | Transitions, comments |
| UI components | 1 week | Stage tracker, forms |
| **Total** | **2-3 weeks** | Full feature |

---

## Phase 1: Install Dependencies

```bash
pip install transitions
```

---

## Phase 2: Database Models

### 2.1 Workflow Definition

```python
# src/extensions/workflows/models.py

from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey, JSON, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin


class WorkflowDefinition(Base, TimestampMixin):
    """
    Workflow template defining stages and transitions.

    Can be system-defined or tenant-defined.
    """
    __tablename__ = "workflow_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    # tenant_id=None means system-wide template

    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Stage definitions
    stages: Mapped[list] = mapped_column(JSON)
    # Example:
    # [
    #     {"key": "upload", "name": "Upload Data", "order": 1},
    #     {"key": "classify", "name": "Classification", "order": 2},
    #     {"key": "review", "name": "Manual Review", "order": 3},
    #     {"key": "forecast", "name": "Run Forecast", "order": 4},
    #     {"key": "final_review", "name": "Final Review", "order": 5},
    #     {"key": "complete", "name": "Complete", "order": 6, "final": True},
    # ]

    # Transition definitions
    transitions: Mapped[list] = mapped_column(JSON)
    # Example:
    # [
    #     {"trigger": "submit", "source": "upload", "dest": "classify"},
    #     {"trigger": "classify_done", "source": "classify", "dest": "review"},
    #     {"trigger": "approve", "source": "review", "dest": "forecast"},
    #     {"trigger": "reject", "source": ["review", "final_review"], "dest": "upload"},
    #     {"trigger": "run_forecast", "source": "forecast", "dest": "final_review"},
    #     {"trigger": "finalize", "source": "final_review", "dest": "complete"},
    # ]

    # Stage permissions (which roles can act at each stage)
    stage_permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example:
    # {
    #     "upload": ["data_entry", "analyst"],
    #     "classify": ["classifier", "analyst"],
    #     "review": ["reviewer", "manager"],
    #     "forecast": ["analyst", "manager"],
    #     "final_review": ["manager", "admin"],
    # }

    initial_stage: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)


class WorkflowInstance(Base, TimestampMixin):
    """
    Active instance of a workflow.

    Tracks current stage and history for a specific entity.
    """
    __tablename__ = "workflow_instances"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    definition_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_definitions.id"))

    # Current state
    current_stage: Mapped[str] = mapped_column(String(100))

    # Link to business entity (polymorphic)
    entity_type: Mapped[str] = mapped_column(String(100))
    # "forecast_cycle", "document", "request"
    entity_id: Mapped[UUID]

    # Metadata
    name: Mapped[str] = mapped_column(String(200))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    # Workflow-specific data

    # Assignment
    current_assignee_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Status
    is_completed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[datetime] = mapped_column(nullable=True)

    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Relationships
    definition = relationship("WorkflowDefinition")
    history = relationship("WorkflowHistory", back_populates="workflow", order_by="WorkflowHistory.created_at")
    comments = relationship("WorkflowComment", back_populates="workflow", order_by="WorkflowComment.created_at")


class WorkflowHistory(Base, TimestampMixin):
    """Audit trail of stage transitions."""
    __tablename__ = "workflow_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_instances.id"))

    # Transition details
    from_stage: Mapped[str] = mapped_column(String(100))
    to_stage: Mapped[str] = mapped_column(String(100))
    trigger: Mapped[str] = mapped_column(String(100))

    # Who and when
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str] = mapped_column(Text, nullable=True)

    # Additional data
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    # Can store form data, attachments, etc.

    # Relationships
    workflow = relationship("WorkflowInstance", back_populates="history")
    user = relationship("User")


class WorkflowComment(Base, TimestampMixin):
    """Comments on workflow (not transitions)."""
    __tablename__ = "workflow_comments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflow_instances.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    content: Mapped[str] = mapped_column(Text)

    # Optional: attach to specific stage
    stage: Mapped[str] = mapped_column(String(100), nullable=True)

    # Relationships
    workflow = relationship("WorkflowInstance", back_populates="comments")
    user = relationship("User")
```

---

## Phase 3: State Machine Service

### 3.1 Workflow Engine

```python
# src/extensions/workflows/engine.py

from transitions import Machine
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from .models import WorkflowDefinition, WorkflowInstance, WorkflowHistory


class WorkflowEngine:
    """
    Workflow engine using transitions library.

    Manages state transitions with permission checks and audit logging.
    """

    def __init__(
        self,
        db: AsyncSession,
        definition: WorkflowDefinition,
        instance: WorkflowInstance,
    ):
        self.db = db
        self.definition = definition
        self.instance = instance
        self._init_machine()

    def _init_machine(self):
        """Initialize transitions state machine from definition."""
        # Extract states from definition
        states = [stage["key"] for stage in self.definition.stages]

        # Create machine
        self.machine = Machine(
            model=self,
            states=states,
            initial=self.instance.current_stage,
            auto_transitions=False,
            send_event=True,  # Pass event data to callbacks
        )

        # Add transitions from definition
        for t in self.definition.transitions:
            self.machine.add_transition(
                trigger=t["trigger"],
                source=t["source"],
                dest=t["dest"],
                before="_check_permission",
                after="_record_transition",
            )

    @property
    def state(self) -> str:
        """Current state (required by transitions)."""
        return self.instance.current_stage

    @state.setter
    def state(self, value: str):
        """Update state (called by transitions)."""
        self.instance.current_stage = value

    def _check_permission(self, event):
        """Check if user has permission to perform transition."""
        user_id = event.kwargs.get("user_id")
        user_roles = event.kwargs.get("user_roles", [])

        # Get allowed roles for current stage
        allowed_roles = self.definition.stage_permissions.get(
            self.instance.current_stage, []
        )

        # Check permission
        if allowed_roles and not any(r in allowed_roles for r in user_roles):
            raise PermissionError(
                f"User does not have permission to perform '{event.event.name}' "
                f"at stage '{self.instance.current_stage}'"
            )

    def _record_transition(self, event):
        """Record transition in history."""
        # Store for later (actual DB write happens in execute_transition)
        self._pending_history = {
            "from_stage": event.transition.source,
            "to_stage": event.transition.dest,
            "trigger": event.event.name,
            "user_id": event.kwargs.get("user_id"),
            "comment": event.kwargs.get("comment"),
            "data": event.kwargs.get("data", {}),
        }

    def get_available_transitions(self) -> list[str]:
        """Get list of valid transitions from current state."""
        triggers = self.machine.get_triggers(self.state)
        return [t for t in triggers if getattr(self, f"may_{t}", lambda: False)()]

    def get_stage_info(self) -> dict:
        """Get information about current stage."""
        for stage in self.definition.stages:
            if stage["key"] == self.state:
                return stage
        return {}

    async def execute_transition(
        self,
        trigger: str,
        user_id: UUID,
        user_roles: list[str],
        comment: str = None,
        data: dict = None,
    ) -> bool:
        """
        Execute a transition with permission check and audit.

        Args:
            trigger: Transition name (e.g., "approve", "reject")
            user_id: User performing the action
            user_roles: User's roles for permission check
            comment: Optional comment
            data: Optional additional data

        Returns:
            True if transition succeeded

        Raises:
            PermissionError: If user lacks permission
            MachineError: If transition is invalid
        """
        # Execute transition (triggers _check_permission and _record_transition)
        trigger_method = getattr(self, trigger)
        trigger_method(
            user_id=user_id,
            user_roles=user_roles,
            comment=comment,
            data=data or {},
        )

        # Record history
        history = WorkflowHistory(
            workflow_id=self.instance.id,
            **self._pending_history,
        )
        self.db.add(history)

        # Check if workflow is complete
        stage_info = self.get_stage_info()
        if stage_info.get("final"):
            self.instance.is_completed = True
            self.instance.completed_at = datetime.utcnow()

        # Save changes
        await self.db.commit()

        return True
```

### 3.2 Workflow Service

```python
# src/extensions/workflows/service.py

from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import WorkflowDefinition, WorkflowInstance, WorkflowComment
from .engine import WorkflowEngine


class WorkflowService:
    """High-level workflow operations."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def create_workflow(
        self,
        definition_key: str,
        entity_type: str,
        entity_id: UUID,
        name: str,
        created_by_id: UUID,
        data: dict = None,
    ) -> WorkflowInstance:
        """Create a new workflow instance."""

        # Get definition
        definition = await self._get_definition(definition_key)

        # Create instance
        instance = WorkflowInstance(
            tenant_id=self.tenant_id,
            definition_id=definition.id,
            current_stage=definition.initial_stage,
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            data=data or {},
            created_by_id=created_by_id,
        )

        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        return instance

    async def get_workflow(self, workflow_id: UUID) -> WorkflowInstance:
        """Get workflow instance with definition."""
        instance = await self.db.get(WorkflowInstance, workflow_id)
        if not instance or instance.tenant_id != self.tenant_id:
            raise ValueError("Workflow not found")
        return instance

    async def transition(
        self,
        workflow_id: UUID,
        trigger: str,
        user_id: UUID,
        user_roles: list[str],
        comment: str = None,
        data: dict = None,
    ) -> WorkflowInstance:
        """Execute a stage transition."""

        instance = await self.get_workflow(workflow_id)
        definition = await self.db.get(WorkflowDefinition, instance.definition_id)

        engine = WorkflowEngine(self.db, definition, instance)
        await engine.execute_transition(
            trigger=trigger,
            user_id=user_id,
            user_roles=user_roles,
            comment=comment,
            data=data,
        )

        await self.db.refresh(instance)
        return instance

    async def add_comment(
        self,
        workflow_id: UUID,
        user_id: UUID,
        content: str,
        stage: str = None,
    ) -> WorkflowComment:
        """Add a comment to workflow."""

        instance = await self.get_workflow(workflow_id)

        comment = WorkflowComment(
            workflow_id=workflow_id,
            user_id=user_id,
            content=content,
            stage=stage or instance.current_stage,
        )

        self.db.add(comment)
        await self.db.commit()

        return comment

    async def get_available_actions(
        self,
        workflow_id: UUID,
        user_roles: list[str],
    ) -> list[str]:
        """Get available transitions for user at current stage."""

        instance = await self.get_workflow(workflow_id)
        definition = await self.db.get(WorkflowDefinition, instance.definition_id)

        engine = WorkflowEngine(self.db, definition, instance)

        # Filter by permission
        allowed_roles = definition.stage_permissions.get(instance.current_stage, [])
        if allowed_roles and not any(r in allowed_roles for r in user_roles):
            return []

        return engine.get_available_transitions()

    async def list_workflows(
        self,
        entity_type: str = None,
        is_completed: bool = None,
        assignee_id: UUID = None,
    ) -> list[WorkflowInstance]:
        """List workflows with filters."""

        query = select(WorkflowInstance).where(
            WorkflowInstance.tenant_id == self.tenant_id
        )

        if entity_type:
            query = query.where(WorkflowInstance.entity_type == entity_type)
        if is_completed is not None:
            query = query.where(WorkflowInstance.is_completed == is_completed)
        if assignee_id:
            query = query.where(WorkflowInstance.current_assignee_id == assignee_id)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _get_definition(self, key: str) -> WorkflowDefinition:
        """Get workflow definition by key."""
        query = select(WorkflowDefinition).where(
            WorkflowDefinition.key == key,
            WorkflowDefinition.is_active == True,
        )
        result = await self.db.execute(query)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Workflow definition '{key}' not found")

        return definition
```

---

## Phase 4: API Routes

```python
# src/extensions/workflows/routes.py

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel

from src.core.auth import CurrentUser, require
from src.core.auth.tenant import TenantUser
from .service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    definition_key: str
    entity_type: str
    entity_id: UUID
    name: str
    data: dict = {}


class TransitionRequest(BaseModel):
    trigger: str
    comment: str | None = None
    data: dict = {}


class CommentCreate(BaseModel):
    content: str
    stage: str | None = None


@router.post("/")
@require("workflows:create")
async def create_workflow(
    data: WorkflowCreate,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new workflow instance."""
    service = WorkflowService(db, tenant.tenant_id)

    workflow = await service.create_workflow(
        definition_key=data.definition_key,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        name=data.name,
        created_by_id=tenant.user.id,
        data=data.data,
    )

    return workflow


@router.get("/")
@require("workflows:view")
async def list_workflows(
    entity_type: str = None,
    is_completed: bool = None,
    my_tasks: bool = False,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """List workflow instances."""
    service = WorkflowService(db, tenant.tenant_id)

    workflows = await service.list_workflows(
        entity_type=entity_type,
        is_completed=is_completed,
        assignee_id=tenant.user.id if my_tasks else None,
    )

    return workflows


@router.get("/{workflow_id}")
@require("workflows:view")
async def get_workflow(
    workflow_id: UUID,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Get workflow details with history and comments."""
    service = WorkflowService(db, tenant.tenant_id)
    workflow = await service.get_workflow(workflow_id)

    # Get available actions for this user
    user_roles = await get_user_roles(tenant.user.id, db)
    available_actions = await service.get_available_actions(workflow_id, user_roles)

    return {
        "workflow": workflow,
        "available_actions": available_actions,
        "history": workflow.history,
        "comments": workflow.comments,
    }


@router.post("/{workflow_id}/transition")
@require("workflows:transition")
async def execute_transition(
    workflow_id: UUID,
    data: TransitionRequest,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Execute a stage transition."""
    service = WorkflowService(db, tenant.tenant_id)

    user_roles = await get_user_roles(tenant.user.id, db)

    try:
        workflow = await service.transition(
            workflow_id=workflow_id,
            trigger=data.trigger,
            user_id=tenant.user.id,
            user_roles=user_roles,
            comment=data.comment,
            data=data.data,
        )
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(400, f"Invalid transition: {e}")

    return workflow


@router.post("/{workflow_id}/comments")
@require("workflows:comment")
async def add_comment(
    workflow_id: UUID,
    data: CommentCreate,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to workflow."""
    service = WorkflowService(db, tenant.tenant_id)

    comment = await service.add_comment(
        workflow_id=workflow_id,
        user_id=tenant.user.id,
        content=data.content,
        stage=data.stage,
    )

    return comment


@router.get("/{workflow_id}/history")
@require("workflows:view")
async def get_history(
    workflow_id: UUID,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Get workflow transition history."""
    service = WorkflowService(db, tenant.tenant_id)
    workflow = await service.get_workflow(workflow_id)
    return workflow.history
```

---

## Phase 5: Auth Integration

### 5.1 Permissions

```python
# Add to RBAC setup

WORKFLOW_PERMISSIONS = [
    ("workflows", "view"),
    ("workflows", "create"),
    ("workflows", "transition"),
    ("workflows", "comment"),
    ("workflows", "assign"),
    ("workflows", "admin"),  # Manage definitions
]

# Example roles
WORKFLOW_ROLES = {
    "viewer": ["workflows:view"],
    "participant": ["workflows:view", "workflows:transition", "workflows:comment"],
    "manager": ["workflows:*"],
}
```

### 5.2 Stage-Level Permissions

Stage permissions are defined in WorkflowDefinition.stage_permissions:

```python
# Example: Forecast cycle workflow
stage_permissions = {
    "upload": ["data_entry", "analyst"],
    "classify": ["classifier", "analyst"],
    "review": ["reviewer", "manager"],
    "forecast": ["analyst", "manager"],
    "final_review": ["manager", "admin"],
}
```

---

## Phase 6: Example Workflow Definitions

### 6.1 Forecast Cycle

```python
forecast_workflow = WorkflowDefinition(
    key="forecast_cycle",
    name="Forecast Cycle",
    initial_stage="upload",
    stages=[
        {"key": "upload", "name": "Data Upload", "order": 1},
        {"key": "classify", "name": "Classification", "order": 2},
        {"key": "review", "name": "Manual Review", "order": 3},
        {"key": "forecast", "name": "Run Forecast", "order": 4},
        {"key": "final_review", "name": "Final Review", "order": 5},
        {"key": "complete", "name": "Complete", "order": 6, "final": True},
    ],
    transitions=[
        {"trigger": "submit", "source": "upload", "dest": "classify"},
        {"trigger": "classify_done", "source": "classify", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "forecast"},
        {"trigger": "reject", "source": ["review", "final_review"], "dest": "upload"},
        {"trigger": "run", "source": "forecast", "dest": "final_review"},
        {"trigger": "finalize", "source": "final_review", "dest": "complete"},
    ],
    stage_permissions={
        "upload": ["analyst", "data_entry"],
        "classify": ["analyst"],
        "review": ["reviewer", "manager"],
        "forecast": ["analyst"],
        "final_review": ["manager"],
    },
)
```

### 6.2 Document Approval

```python
document_workflow = WorkflowDefinition(
    key="document_approval",
    name="Document Approval",
    initial_stage="draft",
    stages=[
        {"key": "draft", "name": "Draft", "order": 1},
        {"key": "submitted", "name": "Submitted", "order": 2},
        {"key": "review", "name": "Under Review", "order": 3},
        {"key": "approved", "name": "Approved", "order": 4, "final": True},
        {"key": "rejected", "name": "Rejected", "order": 5, "final": True},
    ],
    transitions=[
        {"trigger": "submit", "source": "draft", "dest": "submitted"},
        {"trigger": "start_review", "source": "submitted", "dest": "review"},
        {"trigger": "approve", "source": "review", "dest": "approved"},
        {"trigger": "reject", "source": ["submitted", "review"], "dest": "rejected"},
        {"trigger": "reopen", "source": "rejected", "dest": "draft"},
    ],
    stage_permissions={
        "draft": ["author"],
        "submitted": ["author", "reviewer"],
        "review": ["reviewer", "manager"],
    },
)
```

---

## Phase 7: Frontend Components

### 7.1 Stage Tracker

```tsx
// apps/web/src/components/workflows/StageTracker.tsx

interface Stage {
  key: string;
  name: string;
  order: number;
}

export function StageTracker({
  stages,
  currentStage,
}: {
  stages: Stage[];
  currentStage: string;
}) {
  const currentIndex = stages.findIndex((s) => s.key === currentStage);

  return (
    <div className="flex items-center justify-between">
      {stages.map((stage, index) => (
        <React.Fragment key={stage.key}>
          <div className="flex flex-col items-center">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center ${
                index < currentIndex
                  ? 'bg-green-500 text-white'
                  : index === currentIndex
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200'
              }`}
            >
              {index < currentIndex ? '✓' : index + 1}
            </div>
            <span className="text-sm mt-1">{stage.name}</span>
          </div>
          {index < stages.length - 1 && (
            <div
              className={`flex-1 h-1 mx-2 ${
                index < currentIndex ? 'bg-green-500' : 'bg-gray-200'
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
```

### 7.2 Transition Actions

```tsx
// apps/web/src/components/workflows/TransitionActions.tsx

export function TransitionActions({
  workflowId,
  availableActions,
  onTransition,
}: {
  workflowId: string;
  availableActions: string[];
  onTransition: () => void;
}) {
  const [comment, setComment] = useState('');
  const [selectedAction, setSelectedAction] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (data: { trigger: string; comment: string }) =>
      api.post(`/workflows/${workflowId}/transition`, data),
    onSuccess: () => {
      onTransition();
      setComment('');
      setSelectedAction(null);
    },
  });

  const actionLabels: Record<string, string> = {
    submit: 'Submit',
    approve: 'Approve',
    reject: 'Reject',
    classify_done: 'Mark Classification Complete',
    run: 'Run Forecast',
    finalize: 'Finalize',
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {availableActions.map((action) => (
          <Button
            key={action}
            variant={action === 'reject' ? 'destructive' : 'default'}
            onClick={() => setSelectedAction(action)}
          >
            {actionLabels[action] || action}
          </Button>
        ))}
      </div>

      {selectedAction && (
        <Dialog open onOpenChange={() => setSelectedAction(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{actionLabels[selectedAction]}</DialogTitle>
            </DialogHeader>
            <Textarea
              placeholder="Add a comment (optional)"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedAction(null)}>
                Cancel
              </Button>
              <Button
                onClick={() =>
                  mutation.mutate({ trigger: selectedAction, comment })
                }
              >
                Confirm
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
```

---

## Alternatives

| Alternative | Pros | Cons |
|-------------|------|------|
| **Temporal.io** | Fault-tolerant, long-running | Complex, separate service |
| **Camunda** | Full BPMN, visual designer | Heavy, Java-centric |
| **SpiffWorkflow** | Pure Python, BPMN | Steeper learning curve |
| **django-viewflow** | Django integration | Django-specific |
| **Simple status field** | Dead simple | No history, no permissions |

## Resources

- [transitions library](https://github.com/pytransitions/transitions)
- [State Machine Patterns](https://refactoring.guru/design-patterns/state)
- [Temporal.io](https://temporal.io/) (for complex workflows)
- [Camunda](https://camunda.com/) (enterprise BPMN)
