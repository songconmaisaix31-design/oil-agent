"""A dry run proves local intent handling only, never platform acceptance."""

from oil_agent.channels.common import budget, preflight, receipt
from oil_agent.contracts.dto import Delivery, DeliveryState, NotificationIntent
from oil_agent.contracts.services import CallContext


class DryRunChannel:
    async def send(self, intent: NotificationIntent, *, context: CallContext) -> Delivery:
        budget(context)
        preflight(intent, "dry_run")
        return receipt(intent, context, DeliveryState.DRY_RUN)
