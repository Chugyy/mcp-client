from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from app.api.v1.schemas.base import BaseCreateSchema, BaseUpdateSchema


class TriggerType(str, Enum):
    CRON = "cron"
    WEBHOOK = "webhook"
    DATE = "date"
    EVENT = "event"
    MANUAL = "manual"


class StepType(str, Enum):
    """
    Main step types in a workflow.

    - ACTION: Executes an action (MCP tool, AI agent, internal tool)
    - CONTROL: Controls the execution flow (condition, loop, delay)

    This simple architecture allows adding new step_subtype
    without modifying this enum.
    """
    ACTION = "action"
    CONTROL = "control"


class MCPCallConfig(BaseModel):
    """
    Strict config for MCP call steps.
    Ensures that an MCP step has all required fields.
    """
    model_config = ConfigDict(strict=False)  # Allows additional fields

    server_id: str = Field(..., pattern=r"^srv_[A-Za-z0-9]+$", description="MCP server ID (e.g., srv_G5BGds)")
    tool_name: str = Field(..., min_length=1, description="MCP tool name to call")
    arguments: Dict[str, Any] = Field(..., description="MCP tool arguments (cannot be empty)")

    @field_validator('arguments')
    @classmethod
    def arguments_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("MCP arguments cannot be empty - at least one parameter is required")
        return v

    @field_validator('server_id')
    @classmethod
    def server_id_format(cls, v):
        if not v.startswith('srv_'):
            raise ValueError("server_id must start with 'srv_'")
        return v


class AutomationCreate(BaseCreateSchema):
    """Inherits name, description, enabled with validations."""
    model_config = ConfigDict(strict=True)


class AutomationUpdate(BaseUpdateSchema):
    """Inherits name, description, enabled (optional)."""
    model_config = ConfigDict(strict=True)


class WorkflowStepCreate(BaseModel):
    # Strict mode disabled to allow string → Enum conversion for step_type
    model_config = ConfigDict(strict=False)

    step_order: int = Field(..., ge=0, le=100)
    step_name: str = Field(..., min_length=1, max_length=100)
    step_type: StepType = Field(..., description="Main step type (action or control)")
    step_subtype: str = Field(..., min_length=1, description="Subtype for details - For action: mcp_call, ai_action, ai_agent, internal_tool. For control: condition, loop, delay")
    config: Dict[str, Any] = Field(default_factory=dict)
    run_condition: Optional[str] = None
    enabled: bool = Field(default=True)

    @field_validator('config')
    @classmethod
    def validate_mcp_config(cls, v, info):
        """
        Validates the config structure according to step_subtype.
        For MCP steps, uses the strict MCPCallConfig schema.
        """
        # Retrieve step_subtype from validated data
        step_subtype = info.data.get('step_subtype')

        if step_subtype == 'mcp_tool':
            # Validate with strict MCP schema
            try:
                MCPCallConfig(**v)
            except Exception as e:
                raise ValueError(f"Invalid MCP config: {str(e)}")

        return v


class WorkflowStepUpdate(BaseModel):
    model_config = ConfigDict(strict=False)

    step_order: Optional[int] = Field(None, ge=0, le=100)
    step_name: Optional[str] = Field(None, min_length=1, max_length=100)
    step_type: Optional[StepType] = Field(None, description="Main step type (action or control)")
    step_subtype: Optional[str] = Field(None, min_length=1, description="Subtype for details")
    config: Optional[Dict[str, Any]] = None
    run_condition: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator('config')
    @classmethod
    def validate_mcp_config(cls, v, info):
        """
        Validates the config structure according to step_subtype.
        For MCP steps, uses the strict MCPCallConfig schema.
        """
        if v is None:
            return v

        # Retrieve step_subtype from validated data
        step_subtype = info.data.get('step_subtype')

        if step_subtype == 'mcp_tool':
            # Validate with strict MCP schema
            try:
                MCPCallConfig(**v)
            except Exception as e:
                raise ValueError(f"Invalid MCP config: {str(e)}")

        return v


class TriggerCreate(BaseModel):
    # Strict mode disabled to allow string → Enum conversion
    trigger_type: TriggerType = Field(...)
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = Field(default=True)


class TriggerUpdate(BaseModel):
    model_config = ConfigDict(strict=False)

    trigger_type: Optional[TriggerType] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ExecutionCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    automation_id: str = Field(..., min_length=1)
    trigger_id: Optional[str] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)


class ExecutionParams(BaseModel):
    model_config = ConfigDict(strict=True)

    params: Optional[Dict[str, Any]] = Field(default_factory=dict)
