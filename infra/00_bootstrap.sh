#!/usr/bin/env bash
# Idempotent GCP bootstrap for PitchOps AI. Safe to re-run. Never touches billing.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

step "APIs"
gcloud services enable \
  run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  cloudscheduler.googleapis.com cloudtasks.googleapis.com bigquery.googleapis.com \
  firestore.googleapis.com storage.googleapis.com secretmanager.googleapis.com \
  aiplatform.googleapis.com texttospeech.googleapis.com youtube.googleapis.com \
  iamcredentials.googleapis.com logging.googleapis.com monitoring.googleapis.com --quiet
echo "enabled"

step "Artifact Registry: pitchops"
if gcloud artifacts repositories describe pitchops --location="$REGION" >/dev/null 2>&1; then echo "exists"
else gcloud artifacts repositories create pitchops --repository-format=docker --location="$REGION" \
  --description="PitchOps images" --quiet; fi

step "Service accounts"
for sa in sa-jobs sa-api sa-scheduler; do
  if gcloud iam service-accounts describe "$sa@$PROJECT_ID.iam.gserviceaccount.com" >/dev/null 2>&1; then echo "$sa exists"
  else gcloud iam service-accounts create "$sa" --display-name="PitchOps $sa" --quiet; fi
done
SA_JOBS="sa-jobs@$PROJECT_ID.iam.gserviceaccount.com"
SA_API="sa-api@$PROJECT_ID.iam.gserviceaccount.com"
SA_SCHED="sa-scheduler@$PROJECT_ID.iam.gserviceaccount.com"

bind_project() {  # member role
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$1" --role="$2" \
    --condition=None --quiet >/dev/null
  echo "  $1 <- $2"
}
for r in roles/bigquery.dataEditor roles/bigquery.jobUser roles/aiplatform.user roles/datastore.user; do
  bind_project "$SA_JOBS" "$r"; done
for r in roles/datastore.user roles/bigquery.dataViewer roles/bigquery.jobUser roles/aiplatform.user roles/cloudtasks.enqueuer; do
  bind_project "$SA_API" "$r"; done
bind_project "$SA_SCHED" roles/run.invoker

step "Bucket gs://$BUCKET"
if gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then echo "exists"
else gcloud storage buckets create "gs://$BUCKET" --location="$REGION" --uniform-bucket-level-access \
  --public-access-prevention --quiet; fi
LC="$(mktemp)"; cat > "$LC" <<'JSON'
{"rule":[{"action":{"type":"Delete"},"condition":{"age":3,"matchesPrefix":["tmp/"]}}]}
JSON
gcloud storage buckets update "gs://$BUCKET" --lifecycle-file="$LC" --uniform-bucket-level-access \
  --public-access-prevention --quiet >/dev/null; rm -f "$LC"; echo "lifecycle: delete tmp/ after 3 days"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA_JOBS" \
  --role=roles/storage.objectAdmin --quiet >/dev/null && echo "  $SA_JOBS <- storage.objectAdmin (bucket)"
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member="serviceAccount:$SA_API" \
  --role=roles/storage.objectViewer --quiet >/dev/null && echo "  $SA_API <- storage.objectViewer (bucket)"

step "BigQuery dataset $DATASET"
if bq --project_id="$PROJECT_ID" show --format=none "$PROJECT_ID:$DATASET" >/dev/null 2>&1; then echo "exists"
else bq --project_id="$PROJECT_ID" --location="$REGION" mk --dataset "$PROJECT_ID:$DATASET"; fi

step "Firestore ($FS_DB)"
if gcloud firestore databases describe --database="$FS_DB" >/dev/null 2>&1; then
  echo "exists: $(gcloud firestore databases describe --database="$FS_DB" --format='value(locationId,type)')"
else gcloud firestore databases create --database="$FS_DB" --location="$REGION" --type=firestore-native --quiet; fi

step "Secret YOUTUBE_API_KEY"
YT_KEY="$(env_get YOUTUBE_API_KEY)"
[[ -n "$YT_KEY" ]] || { echo "YOUTUBE_API_KEY missing in .env" >&2; exit 1; }
if ! gcloud secrets describe YOUTUBE_API_KEY >/dev/null 2>&1; then
  gcloud secrets create YOUTUBE_API_KEY --replication-policy=automatic --quiet >/dev/null; echo "created"
fi
CUR="$(gcloud secrets versions access latest --secret=YOUTUBE_API_KEY 2>/dev/null || true)"
if [[ "$CUR" != "$YT_KEY" ]]; then
  printf '%s' "$YT_KEY" | gcloud secrets versions add YOUTUBE_API_KEY --data-file=- --quiet >/dev/null
  echo "new version added"
else echo "up to date"; fi
unset YT_KEY CUR
gcloud secrets add-iam-policy-binding YOUTUBE_API_KEY --member="serviceAccount:$SA_JOBS" \
  --role=roles/secretmanager.secretAccessor --condition=None --quiet >/dev/null \
  && echo "  $SA_JOBS <- secretAccessor (secret)"

step "Secret PII_HASH_PEPPER (32 random bytes, never printed)"
if ! gcloud secrets describe PII_HASH_PEPPER >/dev/null 2>&1; then
  python3 -c "import os,sys;sys.stdout.buffer.write(os.urandom(32))" | \
    gcloud secrets create PII_HASH_PEPPER --replication-policy=automatic --data-file=- --quiet >/dev/null
  echo "created"
else echo "exists"; fi
gcloud secrets add-iam-policy-binding PII_HASH_PEPPER --member="serviceAccount:$SA_JOBS" \
  --role=roles/secretmanager.secretAccessor --condition=None --quiet >/dev/null \
  && echo "  $SA_JOBS <- secretAccessor (PII_HASH_PEPPER)"

bash "$(dirname "$0")/guardrails.sh"
