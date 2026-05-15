# Webhook Setup for CI/CD Pipeline Notifications

This guide explains how to set up webhook notifications to receive real-time updates when your mod conversion completes in CI/CD pipelines.

## Overview

When using the `ci-cd-integration.yml` GitHub Action, you can configure webhooks to notify your systems when conversions complete. This is useful for:

- Triggering downstream processes after successful conversions
- Alerting teams on failure
- Integrating with monitoring/alerting systems (PagerDuty, Slack, etc.)

## Webhook Payload

When a conversion completes (either success or failure), PortKit sends a POST request to your configured webhook URL with the following JSON payload:

```json
{
  "event": "conversion.complete",
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "original_filename": "mymod.jar",
  "progress_percentage": 100,
  "download_url": "/api/v1/conversions/550e8400-e29b-41d4-a716-446655440000/download",
  "timestamp": "2026-05-15T10:30:00Z",
  "workflow": {
    "run_id": "1234567890",
    "run_url": "https://github.com/anchapin/portkit/actions/runs/1234567890",
    "job_id": "convert-mod"
  }
}
```

On failure:

```json
{
  "event": "conversion.failed",
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error_type": "conversion_error",
  "error_message": "Unable to parse mod structure",
  "timestamp": "2026-05-15T10:30:00Z"
}
```

## Setting Up Webhook Notifications

### 1. Configure a Webhook URL in GitHub Variables

```bash
# Set your webhook URL as a GitHub variable
gh variable set PIPELINE_WEBHOOK_URL --body "https://your-ci-system.example.com/webhook/portkit"
```

### 2. Enable Webhook in Your Workflow

Add this step to your workflow after the conversion job:

```yaml
- name: Send webhook notification
  if: always()  # Run even on failure
  run: |
    curl -X POST ${{ vars.PIPELINE_WEBHOOK_URL }} \
      -H "Content-Type: application/json" \
      -H "X-PortKit-Event: conversion.complete" \
      -d '{
        "conversion_id": "${{ needs.convert-mod.outputs.conversion_id }}",
        "status": "${{ needs.convert-mod.outputs.conversion_status }}",
        "workflow": "ci-cd-integration",
        "run_id": "${{ github.run_id }}",
        "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
      }'
```

### 3. Alternative: Use PortKit's Native Webhook System

For more robust webhook handling with retries, signing, and event filtering, use PortKit's native webhook system:

```bash
# Register a webhook via the API
curl -X POST https://api.portkit.cloud/api/v1/webhooks \
  -H "Authorization: Bearer $PORTKIT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-ci-system.example.com/webhook/portkit",
    "events": ["conversion.complete", "conversion.failed"],
    "secret": "your-webhook-secret"
  }'
```

## Security Considerations

### Webhook Signatures

PortKit signs webhook payloads using HMAC-SHA256. Verify signatures in your webhook handler:

```python
import hmac
import hashlib

def verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Secret Rotation

Rotate webhook secrets periodically and update your registered webhooks:

```bash
# Rotate secret and update webhook
NEW_SECRET=$(openssl rand -hex 32)
curl -X PATCH https://api.portkit.cloud/api/v1/webhooks/{webhook_id} \
  -H "Authorization: Bearer $PORTKIT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"secret\": \"$NEW_SECRET\"}"
```

## Integration Examples

### Slack Integration

```yaml
- name: Notify Slack on completion
  if: always()
  run: |
    STATUS="${{ needs.convert-mod.outputs.conversion_status }}"
    if [ "$STATUS" = "complete" ]; then
      COLOR="good"
      TEXT="Conversion successful!"
    else
      COLOR="danger"
      TEXT="Conversion failed!"
    fi

    curl -X POST ${{ vars.SLACK_WEBHOOK_URL }} \
      -H "Content-Type: application/json" \
      -d "{
        \"attachments\": [{
          \"color\": \"$COLOR\",
          \"title\": \"PortKit Conversion $STATUS\",
          \"text\": \"$TEXT\",
          \"fields\": [
            {\"title\": \"Run\", \"value\": \"<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|#${{ github.run_number }}>\", \"short\": true}
          ]
        }]
      }"
```

### PagerDuty Integration

```yaml
- name: Alert on failure
  if: failure()
  run: |
    curl -X POST https://events.pagerduty.com/v2/enqueue \
      -H "Content-Type: application/json" \
      -d '{
        "routing_key": "${{ secrets.PAGERDUTY_ROUTING_KEY }}",
        "event_action": "trigger",
        "payload": {
          "summary": "PortKit mod conversion failed",
          "source": "github-actions",
          "severity": "error"
        }
      }'
```

## Troubleshooting

### Webhook Not Receiving Events

1. Check your webhook URL is publicly accessible
2. Verify the webhook is registered in PortKit
3. Check GitHub Actions logs for curl errors
4. Ensure your webhook endpoint responds with 2xx within 10 seconds

### Webhook Delivery Failures

PortKit retries webhook delivery up to 3 times with exponential backoff. If your endpoint is unavailable for an extended period, events may be lost. Consider:

- Using a webhook proxy service (e.g., ngrok, Smee.io) for testing
- Implementing a queue-based webhook receiver for production
- Using the polling approach in `ci-cd-integration.yml` as a fallback