"""Current v2 card callback security, verified against the official SDK in REFERENCES.md.

No callback logs, user provisioning, durable replay store or business authorization.
Reject stale/forged/cross-tenant events before looking up a server-side identity.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import ValidationError

from oil_agent.channels.common import FeishuSettings, budget
from oil_agent.contracts.dto import AckPayload, ExternalIdentity, VerifiedAck
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError

IdentityResolver = Callable[[ExternalIdentity], Awaitable[tuple[str, str]]]


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _decode(body: bytes) -> dict:
    data = json.loads(body, object_pairs_hook=_object)
    if not isinstance(data, dict):
        raise ValueError("Expected object")
    return data


class FeishuAckVerifier:
    def __init__(
        self,
        settings: FeishuSettings,
        *,
        identity_resolver: IdentityResolver,
        delivery_matches: Callable[[str, str], Awaitable[bool]],
        max_age_seconds: int = 300,
    ):
        if not 1 <= max_age_seconds <= 300:
            raise ValueError("Callback age limit must be between 1 and 300 seconds")
        self.settings = settings
        self.identity_resolver = identity_resolver
        self.delivery_matches = delivery_matches
        self.max_age = max_age_seconds

    def _configuration(self):
        if not (
            self.settings.encrypt_key
            and self.settings.verification_token
            and self.settings.app_id
            and self.settings.tenant_key
        ):
            raise ServiceError(ErrorCode.NOT_IMPLEMENTED, "Callback verification is not configured")

    def _plaintext(self, body: bytes) -> dict:
        if len(body) > 262144:
            raise ValueError("Callback too large")
        data = _decode(body)
        if "encrypt" not in data:
            return data
        ciphertext = base64.b64decode(data["encrypt"], validate=True)
        if len(ciphertext) < 32 or len(ciphertext) % 16:
            raise ValueError("Invalid ciphertext")
        key = hashlib.sha256(self.settings.encrypt_key.get_secret_value().encode()).digest()
        decryptor = Cipher(algorithms.AES(key), modes.CBC(ciphertext[:16])).decryptor()
        padded = decryptor.update(ciphertext[16:]) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return _decode(unpadder.update(padded) + unpadder.finalize())

    def _fresh(self, timestamp: float, now: float):
        if not now - self.max_age <= timestamp <= now + 30:
            raise ValueError("Stale callback")

    def _verified_event(self, payload: AckPayload) -> dict:
        self._configuration()
        headers = {}
        for key, value in payload.headers.items():
            if key.lower() in headers:
                raise ValueError("Duplicate header")
            headers[key.lower()] = value
        timestamp = headers["x-lark-request-timestamp"]
        nonce = headers["x-lark-request-nonce"]
        signature = headers["x-lark-signature"]
        if not re.fullmatch(r"[0-9]{10}", timestamp) or not 1 <= len(nonce) <= 256:
            raise ValueError("Invalid signature metadata")
        now = datetime.now(UTC).timestamp()
        self._fresh(float(timestamp), now)
        self._fresh(payload.received_at.timestamp(), now)
        key = self.settings.encrypt_key.get_secret_value()
        digest = hashlib.sha256((timestamp + nonce + key).encode() + payload.body).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", signature) or not hmac.compare_digest(
            digest, signature
        ):
            raise ValueError("Invalid signature")
        data = self._plaintext(payload.body)
        header = data["header"]
        if data.get("schema") != "2.0" or header["event_type"] != "card.action.trigger":
            raise ValueError("Unsupported callback")
        if (
            header["app_id"] != self.settings.app_id
            or header["tenant_key"] != self.settings.tenant_key
        ):
            raise ValueError("Callback application mismatch")
        if not hmac.compare_digest(
            header["token"], self.settings.verification_token.get_secret_value()
        ):
            raise ValueError("Invalid verification token")
        # Official callback create_time is MICROSECONDS, not milliseconds.
        if not re.fullmatch(r"[0-9]{16}", header["create_time"]):
            raise ValueError("Invalid event time")
        self._fresh(int(header["create_time"]) / 1_000_000, now)
        return data

    async def verify(self, payload: AckPayload, *, context: CallContext) -> VerifiedAck:
        try:
            async with asyncio.timeout(min(2, budget(context))):
                data = self._verified_event(payload)
                event = data["event"]
                operator = event["operator"]
                if operator["tenant_key"] != self.settings.tenant_key:
                    raise ValueError("Operator tenant mismatch")
                open_id = operator["open_id"]
                if not re.fullmatch(r"ou_[A-Za-z0-9_-]+", open_id):
                    raise ValueError("Invalid operator")
                message_id = event["context"]["open_message_id"]
                if not isinstance(message_id, str) or not message_id.startswith("om_"):
                    raise ValueError("Missing message context")
                action = event["action"]
                value = action["value"]
                if (
                    action["tag"] != "button"
                    or set(value) != {"operation", "delivery_id", "subject_id", "revision"}
                    or value["operation"] != "ack"
                ):
                    raise ValueError("Invalid acknowledgement action")
                identity = ExternalIdentity(
                    provider="feishu", subject=f"{self.settings.tenant_key}:{open_id}"
                )
                if not await self.delivery_matches(value["delivery_id"], message_id):
                    raise ValueError("Message does not match delivery")
                actor_id, recipient_id = await self.identity_resolver(identity)
                return VerifiedAck(
                    delivery_id=value["delivery_id"],
                    subject_id=value["subject_id"],
                    revision=value["revision"],
                    recipient_id=recipient_id,
                    actor_id=actor_id,
                    callback_id=data["header"]["event_id"],
                    verified_at=datetime.now(UTC),
                )
        except TimeoutError:
            raise ServiceError(
                ErrorCode.TIMEOUT, "Callback verification deadline elapsed"
            ) from None
        except (ValueError, TypeError, KeyError, UnicodeError, ValidationError, RecursionError):
            raise ServiceError(ErrorCode.FORBIDDEN, "Callback verification failed") from None

    async def challenge(self, payload: AckPayload, *, context: CallContext) -> str | None:
        """URL verification is not an acknowledgement and MUST NOT enter C's ack path.

        Official URL verification omits signature checking. Require encrypted body
        and the configured verification token; return only the bounded challenge.
        """
        self._configuration()
        try:
            budget(context)
            data = self._plaintext(payload.body)
            if data.get("type") != "url_verification":
                return None
            if "encrypt" not in _decode(payload.body):
                raise ValueError("Encrypted challenge required")
            self._fresh(payload.received_at.timestamp(), datetime.now(UTC).timestamp())
            if data["type"] != "url_verification" or not hmac.compare_digest(
                data["token"], self.settings.verification_token.get_secret_value()
            ):
                raise ValueError("Invalid challenge")
            challenge = data["challenge"]
            if not isinstance(challenge, str) or not 1 <= len(challenge) <= 4096:
                raise ValueError("Invalid challenge")
            return challenge
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            raise ServiceError(ErrorCode.FORBIDDEN, "Challenge verification failed") from None
