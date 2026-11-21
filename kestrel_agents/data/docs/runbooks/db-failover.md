---
title: "Runbook: database failover"
type: runbook
status: current
updated: 2026-03-30
---
## What happens
The primary database runs on RDS with Multi-AZ. If the primary fails, RDS promotes the standby automatically. Failover usually takes 60 to 120 seconds, during which writes fail.

## Steps
1. Confirm the failover event in the RDS console.
2. Watch the error rate. Services reconnect automatically; restart any service still failing after five minutes.
3. Post an update in the incident channel and record the timeline.
