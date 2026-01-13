"""Tools internes pour l'automation."""

from app.core.services.llm.types import ToolDefinition

AUTOMATION_TOOLS = [
    ToolDefinition(
        name="create_automation",
        description="Create a new automation workflow. Returns the automation ID.",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the automation"
                },
                "description": {
                    "type": "string",
                    "description": "Description of what this automation does"
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Whether the automation is enabled",
                    "default": True
                }
            },
            "required": ["name", "description"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="add_workflow_step",
        description="Add a step to an automation workflow. Steps are executed in order.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to add the step to"
                },
                "step_order": {
                    "type": "integer",
                    "description": "Execution order of this step (0-based)"
                },
                "step_name": {
                    "type": "string",
                    "description": "Name of this step"
                },
                "step_type": {
                    "type": "string",
                    "description": "Type of step - 'action' for executing actions (MCP tools, AI agents, internal tools) or 'control' for flow control (conditions, loops, delays)",
                    "enum": ["action", "control"]
                },
                "step_subtype": {
                    "type": "string",
                    "description": "Subtype providing implementation details. For action: 'mcp_call' (MCP tool), 'ai_action' (simple AI call), 'ai_agent' (full AI agent), 'internal_tool' (internal function). For control: 'condition' (if/else), 'loop' (for_each), 'delay' (pause)"
                },
                "config": {
                    "type": "object",
                    "description": """Step-specific configuration (varies by step_subtype):

For step_subtype='mcp_call' (REQUIRED fields):
  CRITICAL: arguments CANNOT be empty {} - it MUST contain at least one parameter!

  Example 1 - Weather tool:
  {
    "server_id": "srv_weather_abc",
    "tool_name": "get_forecast",
    "arguments": {
      "location": "Paris",
      "days": 5
    }
  }

  Example 2 - Database query:
  {
    "server_id": "srv_database_xyz",
    "tool_name": "execute_query",
    "arguments": {
      "query": "SELECT * FROM users",
      "limit": 10
    }
  }

  Always use list_server_tools first to see the exact parameters required!

For step_subtype='ai_action':
  {
    "agent_id": "agent_xxx",       (REQUIRED: Agent ID)
    "prompt": "Your prompt here"   (REQUIRED: Prompt text)
  }

For step_subtype='ai_agent':
  {
    "model": "gpt-4",
    "messages": [...],
    "system_prompt": "...",
    "temperature": 0.7,
    "max_tokens": 2000
  }

For step_subtype='internal_tool':
  {
    "tool_name": "search_resources",
    "arguments": {...}
  }

For step_subtype='condition':
  {
    "expression": "{{step_0.result.temp}} > 25",
    "target_step": 3,
    "action": "jump"
  }

For step_subtype='loop':
  {
    "list": [1, 2, 3] or "{{trigger.items}}",
    "variable": "item",
    "loop_steps": [1, 2]
  }

For step_subtype='delay':
  {
    "duration_seconds": 5
  }""",
                    "additionalProperties": True
                },
                "run_condition": {
                    "type": "string",
                    "description": "Optional condition to determine if this step should run",
                    "default": None
                }
            },
            "required": ["automation_id", "step_order", "step_name", "step_type", "step_subtype", "config"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="add_trigger",
        description="Add a trigger to an automation. Triggers determine when the automation executes.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to add the trigger to"
                },
                "trigger_type": {
                    "type": "string",
                    "description": "Type of trigger (cron, webhook, date, event, manual)",
                    "enum": ["manual", "webhook", "cron", "date", "event"]
                },
                "config": {
                    "type": "object",
                    "description": "Trigger-specific configuration (cron expression, webhook URL, event type, etc.)",
                    "additionalProperties": True
                }
            },
            "required": ["automation_id", "trigger_type", "config"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="test_automation",
        description="Test an automation by executing it with optional test parameters. Returns execution result.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to test"
                },
                "params": {
                    "type": "object",
                    "description": "Optional parameters to pass to the automation",
                    "additionalProperties": True,
                    "default": {}
                }
            },
            "required": ["automation_id"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="list_automations",
        description="List all automations for the current user. Returns automation metadata including name, enabled state, etc.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="get_automation",
        description="Get detailed information about a specific automation including its configuration and metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to retrieve"
                }
            },
            "required": ["automation_id"]
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="update_automation",
        description="Update an automation's properties (name, description, enabled state). Use this to enable/disable automations.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to update"
                },
                "name": {
                    "type": "string",
                    "description": "New name for the automation"
                },
                "description": {
                    "type": "string",
                    "description": "New description"
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Enable or disable the automation"
                }
            },
            "required": ["automation_id"]
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="list_workflow_steps",
        description="List all workflow steps for a specific automation in execution order.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation"
                }
            },
            "required": ["automation_id"]
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="delete_automation",
        description="Permanently delete an automation. Cannot be undone. Cannot delete system automations.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation to delete"
                }
            },
            "required": ["automation_id"]
        },
        is_default=False,  # Only for Builder
        is_removable=True
    ),
    ToolDefinition(
        name="list_executions",
        description="Get execution history for an automation, including status, timestamps, and results.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of executions to return",
                    "default": 50
                }
            },
            "required": ["automation_id"]
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="get_execution",
        description="Get detailed information about a specific execution, including input parameters, output, errors, and execution state.",
        input_schema={
            "type": "object",
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "ID of the execution"
                }
            },
            "required": ["execution_id"]
        },
        is_default=True,  # Available to all agents
        is_removable=False
    ),
    ToolDefinition(
        name="cancel_execution",
        description="Cancel a running or paused execution. Can only cancel executions with status 'running' or 'paused'.",
        input_schema={
            "type": "object",
            "properties": {
                "execution_id": {
                    "type": "string",
                    "description": "ID of the execution to cancel"
                }
            },
            "required": ["execution_id"]
        },
        is_default=False,  # Only for Builder
        is_removable=True
    ),
    ToolDefinition(
        name="update_workflow_step",
        description="Update an existing workflow step. Use this to modify step configuration, order, or enabled state.",
        input_schema={
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "ID of the workflow step to update"
                },
                "step_order": {
                    "type": "integer",
                    "description": "New execution order (0-100)"
                },
                "step_name": {
                    "type": "string",
                    "description": "New name for the step"
                },
                "step_type": {
                    "type": "string",
                    "description": "New step type (action or control)",
                    "enum": ["action", "control"]
                },
                "step_subtype": {
                    "type": "string",
                    "description": "New step subtype"
                },
                "config": {
                    "type": "object",
                    "description": "New configuration object. For mcp_call steps, remember: arguments CANNOT be empty {} - must contain at least one parameter!",
                    "additionalProperties": True
                },
                "run_condition": {
                    "type": "string",
                    "description": "New run condition expression"
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Enable or disable this step"
                }
            },
            "required": ["step_id"]
        },
        is_default=True,
        is_removable=False
    ),
    ToolDefinition(
        name="delete_workflow_step",
        description="Delete a workflow step from an automation. Cannot be undone.",
        input_schema={
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "ID of the workflow step to delete"
                }
            },
            "required": ["step_id"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="update_trigger",
        description="Update an existing trigger. Use this to modify trigger configuration or enable/disable it.",
        input_schema={
            "type": "object",
            "properties": {
                "trigger_id": {
                    "type": "string",
                    "description": "ID of the trigger to update"
                },
                "trigger_type": {
                    "type": "string",
                    "description": "New trigger type",
                    "enum": ["manual", "webhook", "cron", "date", "event"]
                },
                "config": {
                    "type": "object",
                    "description": "New trigger configuration (cron expression, webhook URL, etc.)",
                    "additionalProperties": True
                },
                "enabled": {
                    "type": "boolean",
                    "description": "Enable or disable this trigger"
                }
            },
            "required": ["trigger_id"]
        },
        is_default=True,
        is_removable=False
    ),
    ToolDefinition(
        name="delete_trigger",
        description="Delete a trigger from an automation. Cannot be undone. For CRON triggers, will automatically unregister from scheduler.",
        input_schema={
            "type": "object",
            "properties": {
                "trigger_id": {
                    "type": "string",
                    "description": "ID of the trigger to delete"
                }
            },
            "required": ["trigger_id"]
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="list_triggers",
        description="List all triggers for a specific automation.",
        input_schema={
            "type": "object",
            "properties": {
                "automation_id": {
                    "type": "string",
                    "description": "ID of the automation"
                }
            },
            "required": ["automation_id"]
        },
        is_default=True,
        is_removable=False
    )
]
