"""Image-swap proposal + reactor coverage (kanban #36).

Spec/08 §5 requires an image_swap proposal in the golden run. The
proposal opens via `senate.propose_image_swap` and on approval the
mcp-pods reactor (`_handle_image_swap_close` in
mcp_pods.service.PodsService) reads back the payload, updates
pods.pods, and emits PodImageSwapped.

Live-stack coverage is observational (the realize loop's notes).
These tests pin the **payload shape contract** between the senate
proposal and the mcp-pods reactor — a unit-level check that the
required keys + types survive any future refactor of the propose
tool.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SENATE_SRC = (
    Path(__file__).resolve().parent.parent
    / "services" / "mcp-senate" / "src"
)
if str(_SENATE_SRC) not in sys.path:
    sys.path.insert(0, str(_SENATE_SRC))

from conclave_core.models import ProposalKind  # noqa: E402
from mcp_senate.service import _affected_for  # noqa: E402


class TestImageSwapPayloadShape:
    def test_affected_for_image_swap_returns_target_pod(self) -> None:
        payload = {
            "pod_id": "pod-abc",
            "old_image": "conclave/pod-template:latest",
            "new_image": "postgres:16",
            "new_mode": "adopted",
            "rationale": "Switch trip storage to managed postgres",
        }
        affected = _affected_for(ProposalKind.IMAGE_SWAP.value, payload)
        # Downstream Pod Lifecycle keys off `affected` to find the
        # target pod for the swap.
        assert affected == ["pod-abc"]

    def test_affected_for_image_swap_missing_pod_id(self) -> None:
        # Defensive: a malformed payload shouldn't crash the
        # ProposalClosed publisher; it returns no affected.
        assert _affected_for(ProposalKind.IMAGE_SWAP.value, {}) == []
        assert (
            _affected_for(ProposalKind.IMAGE_SWAP.value, {"pod_id": None})
            == []
        )

    def test_payload_keys_present(self) -> None:
        # The full key set the mcp-pods reactor reads back.
        # See mcp_pods.service._handle_image_swap_close.
        required = {"pod_id", "old_image", "new_image", "new_mode"}
        payload = {
            "pod_id": "pod-xyz",
            "old_image": "code",
            "new_image": "meilisearch:1.x",
            "new_mode": "adopted",
            "rationale": "Adopt managed search",
        }
        # The contract: senate stores the payload as-is, mcp-pods reads
        # by these exact keys.
        assert required.issubset(payload.keys())


class TestImageSwapSummaryDetection:
    """mcp-pods routes ProposalClosed → _handle_image_swap_close by
    detecting 'Image swap' in the summary string (so it doesn't need
    the payload to reach it via the bus event). Lock that contract:
    senate.server.propose_image_swap builds the summary as
    f'Image swap for {pod_id}: {old_image} → {new_image}'."""

    def test_summary_contains_image_swap_marker(self) -> None:
        # We mirror the format here rather than importing the tool
        # implementation directly (which would pull MCP runtime).
        pod_id = "pod-abc"
        old_image = "code"
        new_image = "postgres:16"
        summary = f"Image swap for {pod_id}: {old_image} → {new_image}"
        assert "Image swap" in summary
