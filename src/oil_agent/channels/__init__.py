"""D-owned transport entrypoints for C runtime/bootstrap injection."""

from oil_agent.channels.c1 import C1_BODY, C1_DATASET, C1_TITLE, build_c1_card, create_c1_preview
from oil_agent.channels.callbacks import FeishuAckVerifier
from oil_agent.channels.common import FeishuSettings, feishu_identity
from oil_agent.channels.dry_run import DryRunChannel
from oil_agent.channels.feishu import FeishuChannel, FeishuRecipient
from oil_agent.channels.identity import FeishuIdentityAdapter
from oil_agent.channels.tenant import FeishuTenantLookup

__all__ = [
    "C1_BODY",
    "C1_DATASET",
    "C1_TITLE",
    "DryRunChannel",
    "FeishuAckVerifier",
    "FeishuChannel",
    "FeishuIdentityAdapter",
    "FeishuRecipient",
    "FeishuSettings",
    "FeishuTenantLookup",
    "build_c1_card",
    "create_c1_preview",
    "feishu_identity",
]
