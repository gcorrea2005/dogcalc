"""ToolManager — registers tools, keeps one active at a time.

Identical pattern to cad2d-lite's ToolManager.
"""

from src.controller.tools.base_tool import BaseTool


class ToolManager:
    """Manages the set of interaction tools.

    Usage:
        tm = ToolManager(view, document)
        tm.register_tool("node", NodeTool(view, doc))
        tm.register_tool("select", SelectTool(view, doc))
        tm.activate_tool("orbit")  # default
    """

    def __init__(self, view, document):
        self._view = view
        self._document = document
        self._tools: dict[str, BaseTool] = {}
        self._active_tool: BaseTool | None = None

    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool with a unique name."""
        self._tools[name] = tool

    def activate_tool(self, name: str):
        """Deactivate current tool and activate the named one."""
        if self._active_tool:
            self._active_tool.deactivate()
        self._active_tool = self._tools.get(name)
        if self._active_tool:
            self._active_tool.activate()
            self._view.setCursor(self._active_tool.cursor())

    @property
    def active_tool(self) -> BaseTool | None:
        return self._active_tool

    @property
    def active_tool_name(self) -> str | None:
        for name, tool in self._tools.items():
            if tool is self._active_tool:
                return name
        return None

    @property
    def tools(self) -> dict:
        return self._tools
