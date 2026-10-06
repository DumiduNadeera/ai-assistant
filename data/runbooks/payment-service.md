# Payment Service Operations Runbook

Department: Payments
Document type: Runbook
Access level: Internal
Created date: 2025-01-10

## First Response

Check authorization success rate, connection pool saturation, gateway latency, and queue age. Compare metrics to the service dashboard baseline.

## Recovery

For pool saturation, verify active connections and apply the approved pool limit. For retry storms, reduce retry concurrency and enable exponential backoff. Record actions in the incident timeline.
