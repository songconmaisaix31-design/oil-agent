"""Frozen QuoteParser seam; provenance comes from C's trusted envelope."""

import asyncio
import base64
import binascii
from pathlib import PurePosixPath

from oil_agent.contracts.http import ParsedQuotes, QuoteParseRequest, QuoteRowIssue
from oil_agent.contracts.services import CallContext, ErrorCode, ServiceError
from oil_agent.ingestion.common import remaining
from oil_agent.ingestion.quotes import UploadLimits, preview_quotes


class SafeQuoteParser:
    def __init__(self, *, limits: UploadLimits | None = None):
        self.limits = limits or UploadLimits()

    async def preview(self, request: QuoteParseRequest, *, context: CallContext) -> ParsedQuotes:
        seconds = remaining(context)
        upload = request.upload
        extension = PurePosixPath(upload.filename).suffix.casefold()
        expected = {
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        if expected.get(extension) != upload.media_type:
            raise ServiceError(ErrorCode.INVALID_INPUT, "Upload media type and extension disagree")
        if len(upload.content_base64) > 4 * ((self.limits.max_bytes + 2) // 3):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Encoded upload exceeds size limit")
        try:
            data = base64.b64decode(upload.content_base64, validate=True)
        except (ValueError, binascii.Error):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Upload is not valid base64") from None
        try:
            async with asyncio.timeout(seconds):
                preview = await asyncio.to_thread(
                    preview_quotes,
                    data,
                    upload.filename,
                    upload.field_mapping,
                    rights_ref=upload.rights_ref,
                    origin_publisher=request.origin_publisher,
                    discovered_at=request.discovered_at,
                    is_fixture=request.is_fixture,
                    provenance=request.provenance,
                    fixture_dataset=request.fixture_dataset,
                    limits=self.limits,
                )
        except TimeoutError:
            raise ServiceError(ErrorCode.TIMEOUT, "Quote preview deadline exceeded") from None
        remaining(context)
        return ParsedQuotes(
            records=tuple(row.record for row in preview.rows if row.record is not None),
            observations=tuple(
                row.observation for row in preview.rows if row.observation is not None
            ),
            issues=tuple(
                QuoteRowIssue(row_number=row.row_number, code=code, message=code.replace("_", " "))
                for row in preview.rows
                for code in row.errors
            ),
            duplicate_rows=tuple(
                row.row_number for row in preview.rows if row.duplicate_of is not None
            ),
            file_hash=preview.file_sha256,
        )
