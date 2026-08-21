"""
Wires up concrete tool instances into the controlled TOOL_REGISTRY.

This is the ONLY place tool instances are constructed. Swap a mock for a
real implementation here (or behind an env-var flag) when Member 2 ships
real tools -- nothing else in the codebase needs to change.
"""
from tools.base import TOOL_REGISTRY, register_tool, is_registered, get_tool  # noqa: F401
from tools.rag_tool import RagTool
from tools.ml_tool import MlTool
from tools.ml_scenario_tool import MlScenarioTool
from tools.provider_db_tool import (
    ProviderStatisticsTool,
    ProviderHistoryTool,
    ProviderPeerComparisonTool,
)
from tools.claim_db_tool import ClaimHistoryTool

for _tool in [
    RagTool(),
    MlTool(),
    MlScenarioTool(),
    ProviderStatisticsTool(),
    ProviderHistoryTool(),
    ProviderPeerComparisonTool(),
    ClaimHistoryTool(),
]:
    register_tool(_tool)
