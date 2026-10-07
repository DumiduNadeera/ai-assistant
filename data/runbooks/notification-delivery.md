# Notification Delivery Recovery Runbook

Document ID: RUN-2025-003
Department: Customer Experience
Document type: Runbook
Access level: Confidential
Created date: 2025-08-12

## Purpose

Use this runbook when payment notifications are delayed, duplicated, rejected, accumulating in a dead-letter queue, or failing for one delivery provider. Notification incidents must be isolated from payment processing. Operators must never retry or reverse a payment to correct a message-delivery problem.

## Required Access

Operators need aggregate notification dashboards, queue administration, dispatcher deployment controls, provider status, and masked Delivery Ledger records. Access to message bodies or destinations requires the Customer Communications operations role.

## Triage

1. Identify affected channels: push, SMS, email, or all channels.
2. Record event intake, queue age, delivery success, provider latency, retry rate, duplicate ratio, dead-letter volume, and worker restarts.
3. Confirm Payment Authorization and Settlement Processing are healthy.
4. Check recent dispatcher, template, preference, and provider-configuration changes.
5. Determine whether jobs are delayed, duplicated, permanently rejected, or missing.

## Delayed Notifications

If provider latency or rate limiting is high, open the channel circuit breaker and keep jobs queued. Respect provider retry-after values. Do not increase workers beyond provider quota. When the provider recovers, resume at 10% capacity and increase every five minutes while queue age and provider errors improve.

If internal dispatch capacity is low and provider health is normal, increase workers by 25% while monitoring Delivery Ledger latency and broker acknowledgment time.

## Duplicate Notifications

1. Pause the affected channel consumers.
2. Confirm payment and ledger records are not duplicated.
3. Compare queue event ID, channel job ID, provider request ID, and Delivery Ledger status.
4. Roll back any release that changed acknowledgment or idempotency behavior.
5. Before resuming, enable the delivered-job suppression check.
6. Resume at 25% capacity and verify duplicate ratio remains zero.

Do not delete queued jobs based only on provider response logs. The Delivery Ledger is the operational source for suppression decisions.

## Dead-Letter Recovery

Group dead-letter jobs by reason code and schema version. Permanent destination or preference failures are closed without replay. Transient provider and infrastructure failures may be replayed after the cause is resolved. Replay retains the original channel job ID and records the replay operator and incident reference.

## Template Failure

Disable the affected template version and restore the last approved version. Quarantine events that cannot render. Do not substitute free-form text or manually edit production message content.

## Validation

Recovery is complete when p99 enqueue-to-provider time is below 60 seconds for 20 minutes, provider success exceeds 99%, duplicate ratio is below 0.01%, dead-letter growth is zero, queue age is below two minutes, and sampled events match one Delivery Ledger record per channel job.

## Customer Communication

If duplicate messages may be interpreted as duplicate charges, Customer Support must receive a verified statement confirming whether the ledger contains single or multiple postings. Do not make this statement before reconciliation is complete.

## Escalation

- Notification Platform: dispatcher, queue, templates, and Delivery Ledger
- Customer Communications: channel policy and message content
- Provider Management: SMS, push, or email provider incidents
- Payments Platform: confirmation of payment-state correctness
- Privacy Office: suspected destination or message-content exposure

## Related Documents

- ARCH-2025-002 — Event-Driven Payment Notification Architecture
- PROD-2025-012 — Instant Payment Notifications Specification
- INC-2025-0074 — Duplicate Payment Notification Incident
