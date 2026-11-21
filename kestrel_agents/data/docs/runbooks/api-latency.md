---
title: "Runbook: high API latency"
type: runbook
status: current
updated: 2026-07-15
---
## When this alert fires
The alert pages when p95 API latency stays above 800 ms for 10 minutes.

## Steps
1. Open the API dashboard and check whether latency is high for all endpoints or only some.
2. Check deploys from the last hour. If a deploy lines up with the spike, roll it back first and investigate after.
3. Check database CPU and slow queries. A missing index after a migration is the most common cause.
4. If traffic is simply higher than usual, scale the API deployment up and open a capacity ticket.
