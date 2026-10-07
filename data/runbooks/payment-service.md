# Payment Authorization Operations Runbook

Document ID: RUN-2025-001
Department: Payments
Document type: Runbook
Access level: Internal
Created date: 2025-01-10

## Purpose

Use this runbook when Payment Authorization has elevated errors, latency, connection-pool saturation, gateway degradation, or abnormal retry volume. The objective is to protect financial correctness, reduce demand safely, restore authorization availability, and produce enough evidence for reconciliation.

## Prerequisites and Access

The operator needs read access to payment dashboards, centralized logs, traces, gateway status, and deployment history. Changing retry budgets, circuit breakers, traffic weights, replica counts, or database pool limits requires the Payments on-call role and an incident or approved change reference.

Never paste account numbers, card data, credentials, or raw customer payloads into incident channels.

## Severity Guidance

| Condition | Suggested severity |
|---|---|
| Authorization success below 95% for two minutes | SEV-1 |
| Complete authorization outage for any channel | SEV-1 |
| Success between 95% and 99.5% for five minutes | SEV-2 |
| p95 latency above two seconds with normal success | SEV-2 |
| Single merchant or noncritical channel degradation | SEV-3 |

## First Five Minutes

1. Acknowledge the alert and record the start time.
2. Check authorization success, request rate, p50/p95/p99 latency, and HTTP status distribution.
3. Compare current traffic with the same weekday and business-event forecast.
4. Check gateway latency, timeout rate, circuit-breaker state, and provider advisories.
5. Check database pool utilization, waiting requests, connection wait time, query latency, and database failover status.
6. Check retry ratio and retry concurrency by caller and replica.
7. Review deployments and runtime configuration changes from the previous two hours.
8. Declare an incident if a severity threshold is met.

## Diagnosis Decision Tree

### Connection Pool Saturation

Symptoms include pool utilization above 90%, connection wait time above 500 milliseconds, low application CPU, and increasing HTTP 503 responses.

1. Confirm whether database sessions are active, idle, locked, or waiting.
2. Identify the top query or transaction by connection occupancy.
3. Reduce retry concurrency before increasing pool capacity.
4. Shed nonessential health, reporting, or test traffic.
5. If database headroom is confirmed, apply the approved pool override in increments no greater than 25%.
6. Stop if database CPU exceeds 75%, lock waits increase, or replication lag exceeds 10 seconds.

### Gateway Degradation

Symptoms include normal database health, increased downstream latency, timeouts concentrated on one provider, and an opening circuit breaker.

1. Confirm the affected provider and transaction type.
2. Verify that retries use the same idempotency key.
3. Keep the circuit breaker enabled; do not force it closed during active degradation.
4. Route eligible traffic to the approved alternate provider if the commercial and scheme rules permit.
5. Reduce the retry budget if retry ratio exceeds 15% of primary requests.

### Application Regression

Symptoms begin immediately after deployment or feature-flag change and affect all dependencies similarly.

1. Compare error and latency by version.
2. Stop rollout when the new version shows a statistically significant regression.
3. Roll back to the last healthy version using the standard deployment pipeline.
4. Do not roll back a database migration until Database Engineering confirms backward compatibility.

### Traffic Spike

Symptoms include healthy dependency latency, request rate above forecast, replica saturation, and even distribution across merchants.

1. Confirm whether the traffic is legitimate and expected.
2. Apply merchant and channel rate limits according to priority policy.
3. Scale stateless replicas while watching database connection demand.
4. Contact Product Operations if a campaign or partner event was not declared.

## Recovery Validation

Do not close the incident until all conditions remain true for at least 15 minutes:

- Authorization success is at or above 99.9%.
- p95 latency is below 800 milliseconds.
- Database pool utilization is below 75% and waiting requests are near zero.
- Retry ratio is below 5%.
- Circuit breakers are stable and no dependency is flapping.
- Outbox age is below two minutes.
- Reconciliation finds no successful gateway response without a matching audit record.

## Rollback and Configuration Restoration

Record every temporary runtime change. Restore retry budgets, pool limits, rate limits, and traffic weights one at a time after stability is confirmed. Observe for five minutes between changes. If the original setting immediately recreates saturation, restore the safe override and open a corrective-action item rather than forcing normalization.

## Reconciliation

Compare authorization audit records with gateway responses using correlation ID and idempotency key. Investigate any successful gateway response without a committed authorization record before settlement resumes. Never create a missing financial record manually without approval from Payments Operations and Finance Control.

## Communication

For SEV-1, update stakeholders every 15 minutes. Include customer impact, affected channels, current hypothesis, mitigation, and next update time. Avoid unsupported root-cause statements during active response.

## Escalation

- Payments Platform: application behavior, retries, idempotency, and deployment rollback
- Site Reliability: incident command, traffic controls, shared monitoring, and capacity
- Database Engineering: pool headroom, query plans, locks, failover, and replication
- External Provider Management: gateway-provider escalation
- Finance Control: reconciliation exceptions or suspected financial inconsistency

## Related Documents

- ARCH-2025-001 — Payment Platform Resilience Architecture
- INC-2025-0042 — Payment Gateway Authorization Outage
- PROD-2025-018 — Payment Retry Budget and Resilience Controls
