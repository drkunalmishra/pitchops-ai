#!/usr/bin/env bash
# Deploy Cloud Run Jobs discover / harvest / score from the image built by 30_deploy.sh.
# Guardrails: 1 vCPU, 1 GiB, task-timeout 3600s, parallelism 1, max-retries 1, runs as sa-jobs.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
IMAGE="${IMAGE:-$(cat "$REPO_ROOT/.last_image")}"
FROZEN="${CORPUS_FROZEN:-false}"
ENVS="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,FIRESTORE_DATABASE=$FS_DB,CONTACT_EMAIL=$(env_get CONTACT_EMAIL),CORPUS_FROZEN=$FROZEN"
ENVS="$ENVS,GEMINI_LOCATION=$(env_get GEMINI_LOCATION global),GEMINI_MODEL_FLASH=$(env_get GEMINI_MODEL_FLASH)"
ENVS="$ENVS,GEMINI_BUDGET_USD=$(env_get GEMINI_BUDGET_USD 60),GEMINI_DAILY_USD=$(env_get GEMINI_DAILY_USD 25)"

# discover defaults trimmed after the first sweep: harvest gets quota priority (10 company searches = 1,000 units; corpus already has 700+ channels)
job_args() {
  case "$1" in
    discover) echo "-m,jobs.discover,--searches,10,--kw-searches,0" ;;
    *) echo "-m,jobs.$1" ;;
  esac
}
for job in discover harvest score; do
  step "Cloud Run Job: $job"
  verb=create; gcloud run jobs describe "$job" --region="$REGION" >/dev/null 2>&1 && verb=update
  gcloud run jobs "$verb" "$job" --image="$IMAGE" --region="$REGION" \
    --service-account="sa-jobs@$PROJECT_ID.iam.gserviceaccount.com" \
    --cpu=1 --memory=1Gi --task-timeout=3600s --parallelism=1 --tasks=1 --max-retries=1 \
    --set-secrets="YOUTUBE_API_KEY=YOUTUBE_API_KEY:latest" \
    --set-env-vars="$ENVS" \
    --command=python --args="$(job_args "$job")" --quiet
done
gcloud run jobs list --region="$REGION" --format='table(name,lastUpdatedTime)'
