---
title: Secrets management
type: security
status: current
updated: 2026-02-14
---
## Where secrets live
All secrets are stored in AWS Secrets Manager. Never commit secrets to a repository, including in env files or test fixtures.

## Rotation
Database credentials and API keys are rotated every 90 days. Rotation is automated for RDS credentials.

## If a secret leaks
Revoke it immediately, rotate it, and open a SEV2 incident so the exposure is reviewed.
