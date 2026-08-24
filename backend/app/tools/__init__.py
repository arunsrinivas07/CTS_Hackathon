"""
Wires up concrete tool instances into the controlled TOOL_REGISTRY.

This is the ONLY place tool instances are constructed. Swap a mock for a
real implementation here (or behind an env-var flag) when Member 2 ships
real tools -- nothing else in the codebase needs to change.
"""
from app.tools.base import TOOL_REGISTRY, register_tool, is_registered, get_tool  # noqa: F401
from app.tools.rag_tool import RagTool
from app.tools.ml_tool import MlTool
from app.tools.ml_scenario_tool import MlScenarioTool
from app.tools.provider_db_tool import (
    ProviderStatisticsTool,
    ProviderHistoryTool,
    ProviderPeerComparisonTool,
)
from app.tools.claim_db_tool import ClaimHistoryTool
from app.tools.ml_verification_tool import MLVerificationTool

for _tool in [
    RagTool(),
    MlTool(),
    MlScenarioTool(),
    ProviderStatisticsTool(),
    ProviderHistoryTool(),
    ProviderPeerComparisonTool(),
    ClaimHistoryTool(),
    MLVerificationTool(),
]:
    register_tool(_tool)
