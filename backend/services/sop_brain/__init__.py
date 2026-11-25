"""Pakej Otak SOP KKM Pindaan 2024 untuk i-UIP Nerus (Dual Knowledge Store: Statut + 22 SOP Aktif)."""

from backend.services.sop_brain.system_prompts import (
    AUDIT_PRA_TPR_SYSTEM_PROMPT,
    PAKAR_UIP_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
)
from backend.services.sop_brain.uip_brain import (
    IUIPNerusBrain,
    RouteDecision,
    build_statutory_context_for_question,
    get_sop_brain,
)

__all__ = [
    "AUDIT_PRA_TPR_SYSTEM_PROMPT",
    "PAKAR_UIP_SYSTEM_PROMPT",
    "ROUTER_SYSTEM_PROMPT",
    "IUIPNerusBrain",
    "RouteDecision",
    "build_statutory_context_for_question",
    "get_sop_brain",
]
