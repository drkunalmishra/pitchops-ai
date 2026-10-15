#!/usr/bin/env bash
# Cloud Scheduler (Asia/Kolkata) -> Cloud Run Jobs, invoked as sa-scheduler. Idempotent (create or update).
set -euo pipefail
source "$(dirname "$0")/lib.sh"
SA="sa-scheduler@$PROJECT_ID.iam.gserviceaccount.com"
NUM="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"

sched() {  # name cron job
  local uri="https://run.googleapis.com/v2/projects/$PROJECT_ID/locations/$REGION/jobs/$3:run"
  local verb=create; gcloud scheduler jobs describe "$1" --location="$REGION" >/dev/null 2>&1 && verb=update
  gcloud scheduler jobs "$verb" http "$1" --location="$REGION" --schedule="$2" --time-zone="Asia/Kolkata" \
    --uri="$uri" --http-method=POST --oauth-service-account-email="$SA" \
    --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform" --attempt-deadline=180s --quiet >/dev/null
  echo "  $1  [$2 IST] -> $3"
}
step "Scheduler jobs"
sched discover-1300 "0 13 * * *" discover
sched harvest-1430  "30 14 * * *" harvest
sched harvest-2330  "30 23 * * *" harvest
sched score-1700    "0 17 * * *" score
sched score-0030    "30 0 * * *" score
sched comments-1245 "45 12 * * *" comments
sched finops-3h     "15 */3 * * *" finops    # FinOps dashboard refresh every 3 hours (P5)
gcloud scheduler jobs list --location="$REGION" --format='table(name.basename(),schedule,timeZone,state,scheduleTime)'
: "$NUM"
