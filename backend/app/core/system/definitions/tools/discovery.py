"""Tools de découverte MCP pour les agents."""

from app.core.services.llm.types import ToolDefinition

DISCOVERY_TOOLS = [
    ToolDefinition(
        name="list_user_mcp_servers",
        description="List all MCP servers available to the current user. Use this to discover which servers and integrations are available before creating an automation. Returns server IDs, names, descriptions, and status.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        },
        is_default=False,
        is_removable=True
    ),
    ToolDefinition(
        name="list_server_tools",
        description="""List all tools available on a specific MCP server.

CRITICAL: The response includes 'input_schema' for each tool - you MUST use this schema to fill the 'arguments' field when creating a workflow step with step_subtype='mcp_call'.

Returns:
- name: Tool name (use this for config.tool_name)
- description: What the tool does
- input_schema: JSON schema showing required/optional parameters
  → Use input_schema.properties to see all parameters
  → Use input_schema.required to see which are mandatory
  → Fill config.arguments with these parameters!
- enabled: Whether the tool is active

Example: If input_schema shows {"properties": {"location": {"type": "string"}}, "required": ["location"]}
Then your config must include: {"arguments": {"location": "Paris"}}""",
        input_schema={
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "ID of the MCP server to list tools from (e.g., 'srv_abc123'). Get this from list_user_mcp_servers first."
                }
            },
            "required": ["server_id"]
        },
        is_default=False,
        is_removable=True
    )
]
