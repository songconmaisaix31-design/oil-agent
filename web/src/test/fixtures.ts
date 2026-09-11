// Synthetic, isolated test data; never used by the application bundle.
import type { Schema } from "../api";

export const now = "2026-09-12T00:00:00Z";
export const actor: Schema<"Actor"> = {
  actor_id: "fixture-actor",
  recipient_id: "fixture-recipient",
  role: "viewer",
  session_id: "fixture-session",
  authenticated_at: now,
  expires_at: "2099-01-01T00:00:00Z",
};
export const event: Schema<"EventAssessment"> = {
  event_id: "fixture-event",
  revision: 2,
  title: "Synthetic test event",
  severity: "urgent",
  assertion_status: "planned",
  evidence_status: "credible_single_source",
  is_fixture: true,
  provenance: "fixture",
  fixture_dataset: "web-unit",
  supporting_record_ids: ["fixture-record"],
  evidence: [
    {
      record_id: "fixture-record",
      revision: 1,
      field: "content_excerpt",
      excerpt: "Synthetic evidence",
    },
  ],
  origin_groups: [
    { origin_publisher: "Synthetic publisher", record_ids: ["fixture-record"] },
  ],
  impact_path: ["Potential impact, not confirmed"],
  unknowns: ["Independent verification needed"],
  assessed_at: now,
  change_summary: "Synthetic revision update",
  supersedes_revision: 1,
  processing: {
    rule_version: "synthetic",
    model_version: null,
    prompt_version: null,
  },
};
export const detail: Schema<"EventDetail"> = {
  current: event,
  timeline: [
    {
      ...event,
      revision: 1,
      change_summary: "Original synthetic version",
      supersedes_revision: null,
    },
  ],
  can_ack: true,
  acknowledged_revision: null,
  deliveries: [
    {
      delivery_id: "fixture-delivery",
      intent_id: "fixture-intent",
      recipient_id: "fixture-recipient",
      revision: 2,
      attempt: 1,
      state: "dry_run",
      updated_at: now,
      accepted_at: null,
      platform_message_id: null,
    },
  ],
};
export const status: Schema<"RuntimeStatus"> = {
  stage: "runtime",
  database: "available",
  outbound_mode: "dry_run",
  first_report_policy: null,
  reminders_enabled: false,
  sms_enabled: false,
  phone_enabled: false,
  business_api_implemented: true,
  sources: [],
  capabilities: [],
};
