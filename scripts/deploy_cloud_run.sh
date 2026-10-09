#!/usr/bin/env bash
# Deploy the API to Google Cloud Run (Frankfurt). Secrets live in Secret Manager.
#
# One-time setup per project:
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#       artifactregistry.googleapis.com secretmanager.googleapis.com
#   for s in ANTHROPIC_API_KEY DATABASE_URL SLACK_SIGNING_SECRET COPILOT_API_KEY; do
#     printf '%s' "<value>" | gcloud secrets create "$s" --data-file=-
#   done
#   (plus the IAM binding below so Cloud Run can read the secrets)
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${REGION:-europe-west3}"
SERVICE="${SERVICE:-recruiting-copilot}"
MODEL="${ANTHROPIC_MODEL:-claude-sonnet-5}"

gcloud run deploy "$SERVICE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --source . \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --timeout 120 \
  --set-env-vars "ANTHROPIC_MODEL=$MODEL" \
  --set-secrets "ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest,SLACK_SIGNING_SECRET=SLACK_SIGNING_SECRET:latest,COPILOT_API_KEY=COPILOT_API_KEY:latest"

gcloud run services describe "$SERVICE" --project "$PROJECT_ID" --region "$REGION" --format 'value(status.url)'
