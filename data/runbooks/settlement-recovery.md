# Settlement Backlog Recovery Runbook

Document ID: RUN-2025-002
Department: Payments
Document type: Runbook
Access level: Internal
Created date: 2025-05-06

## Purpose

Use this runbook when settlement queue age exceeds 15 minutes, settlement throughput falls below arrival rate, scheduled merchant reports are delayed, or a batch risks missing its completion objective. The procedure prioritizes financial correctness and controlled backlog drainage over maximum short-term throughput.

## Preconditions

- An incident or operations ticket exists.
- The operator can view queue, worker, database, ledger, and downstream acknowledgment metrics.
- Scaling beyond the normal worker maximum requires Payments Platform approval.
- Query-plan changes require Database Engineering approval.

## Initial Assessment

Record queue depth, oldest-message age, arrival rate, completion rate, estimated drain time, worker count, worker utilization, database latency, lock waits, replication lag, and downstream response time.

Determine whether the problem is caused by low consumer capacity, slow database work, downstream degradation, poison messages, or a paused partition. Do not increase worker count until the constraining dependency is known.

## Recovery Procedures

### Slow Database Query

1. Identify the query fingerprint consuming the most worker time.
2. Compare its execution plan with the approved baseline.
3. Pause report generation and nonessential analytical reads.
4. Apply the approved plan baseline or index mitigation.
5. Confirm query latency is below 150 milliseconds before scaling workers.

### Insufficient Worker Capacity

1. Confirm database CPU below 65%, replication lag below five seconds, and downstream success above 99%.
2. Increase workers by 25%.
3. Observe throughput, locks, CPU, and acknowledgment latency for five minutes.
4. Repeat up to the emergency maximum of 150% of normal worker count.
5. Stop scaling if throughput no longer improves proportionally.

### Poison Message

1. Identify repeated failures by event ID and reason code.
2. Confirm the message contains no evidence of a wider schema incompatibility.
3. Move the event to the settlement quarantine queue with its original metadata.
4. Resume the partition and monitor for related failures.
5. Do not edit or discard the original event.

### Downstream Service Degradation

1. Open the downstream circuit breaker according to its threshold.
2. Keep unacknowledged settlement work queued.
3. Contact the downstream owner with correlation IDs and aggregate counts.
4. Resume at 10% throughput after recovery, then increase in stages.

## Financial Safety Controls

Every instruction retains the original idempotency key and business date. Operators must not replay an entire batch without first checking processed-instruction records. Manual database updates, timestamp changes, and queue deletion are prohibited.

## Recovery Completion Criteria

- Oldest queue item is below five minutes for 20 minutes.
- Completion rate exceeds arrival rate with at least 20% headroom.
- Database p95 latency is below 150 milliseconds.
- Lock waits and replication lag are within normal thresholds.
- Dead-letter and quarantine counts are explained.
- Instruction count, total amount, currency totals, and idempotency keys reconcile.
- Merchant reports have been regenerated or released.

## Return to Normal

Reduce temporary workers in 25% stages. Resume reporting only after settlement queue age is stable. Remove plan overrides only through a reviewed database change. Record the maximum backlog, drain time, temporary controls, and reconciliation result in the incident timeline.

## Escalation

Escalate to Finance Control for any amount mismatch, missing instruction, duplicate settlement effect, or unexplained reconciliation difference. Escalate to Database Engineering for plan regression, persistent lock waits, or replication lag above 30 seconds.

## Related Documents

- INC-2025-0061 — Payment Settlement Processing Delay
- ARCH-2025-001 — Payment Platform Resilience Architecture
