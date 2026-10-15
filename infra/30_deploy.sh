#!/usr/bin/env bash
# Build with Cloud Build and deploy Cloud Run service "api". Cost guardrails: min 0, max 2.
set -euo pipefail
source "$(dirname "$0")/lib.sh"
cd "$REPO_ROOT"

# Refuse to upload secrets / broker files.
if gcloud meta list-files-for-upload . | grep -qE '(^|/)\.env$|^inputs/|\.xlsx?$'; then
  echo "ABORT: .env / inputs / xls would be uploaded" >&2; exit 1
fi

IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/pitchops/pitchops:$(git rev-parse --short HEAD 2>/dev/null || echo dev)-$(date +%s)"
step "Cloud Build -> $IMAGE"
cat > /tmp/pitchops-cloudbuild.yaml <<YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: [build, -t, $IMAGE, .]
images: [$IMAGE]
options: {logging: CLOUD_LOGGING_ONLY}
YAML
gcloud builds submit . --config=/tmp/pitchops-cloudbuild.yaml --region="$REGION" --quiet

step "Cloud Run deploy api"
gcloud run deploy api --image="$IMAGE" --region="$REGION" \
  --service-account="sa-api@$PROJECT_ID.iam.gserviceaccount.com" \
  --min-instances=0 --max-instances=2 --memory=512Mi --cpu=1 --concurrency=40 \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=$REGION,FIRESTORE_DATABASE=$FS_DB,GEMINI_LOCATION=$(env_get GEMINI_LOCATION global),GEMINI_MODEL_FLASH=$(env_get GEMINI_MODEL_FLASH),GEMINI_BUDGET_USD=$(env_get GEMINI_BUDGET_USD 60),GEMINI_DAILY_USD=$(env_get GEMINI_DAILY_USD 25),ADMIN_EMAILS=$(env_get ADMIN_EMAILS "$(env_get CONTACT_EMAIL)")" \
  --quiet
URL="$(gcloud run services describe api --region="$REGION" --format='value(status.url)')"
echo "$IMAGE" > "$REPO_ROOT/.last_image"
echo "api: $URL"
echo "healthz: $(curl -s "$URL/api/healthz")"
echo "readyz:  $(curl -s "$URL/api/readyz")"
echo "stats without token -> HTTP $(curl -s -o /dev/null -w '%{http_code}' "$URL/v1/corpus/stats")"
