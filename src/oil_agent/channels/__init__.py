"""D-owned transport entrypoints for C runtime/bootstrap injection."""

from oil_agent.channels.callbacks import FeishuAckVerifier
from oil_agent.channels.common import FeishuSettings
from oil_agent.channels.dry_run import DryRunChannel
from oil_agent.channels.feishu import FeishuChannel, FeishuRecipient
from oil_agent.channels.identity import FeishuIdentityAdapter

__all__ = [
    "DryRunChannel",
    "FeishuAckVerifier",
    "FeishuChannel",
    "FeishuIdentityAdapter",
    "FeishuRecipient",
    "FeishuSettings",
]
