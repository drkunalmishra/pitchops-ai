#!/usr/bin/env bash
# Read-only guardrail summary. Lists, never creates or changes anything.
set -uo pipefail
source "$(dirname "$0")/lib.sh"

count_or_disabled() {  # cmd...  -> prints count, or "0 (API disabled)"
  local out
  if out="$("$@" --format='value(name)' 2>&1)"; then
    printf '%s' "$out" | grep -c . || true
  elif grep -qiE 'not (been )?(used|enabled)|SERVICE_DISABLED|has not been used' <<<"$out"; then echo "0 (API disabled)"
  else echo "ERROR: ${out%%$'\n'*}"; fi
}

echo; echo "================ GUARDRAIL SUMMARY ================"
BILL="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingAccountName,billingEnabled)' 2>&1)"
echo "Billing link        : $BILL"
echo "                      (free-trial status is only visible in Console > Billing > Overview; never upgrade)"
echo "Compute VMs         : $(count_or_disabled gcloud compute instances list)"
echo "Cloud SQL instances : $(count_or_disabled gcloud sql instances list)"
echo "GKE clusters        : $(count_or_disabled gcloud container clusters list)"
echo "Cloud Run services  :"
gcloud run services list --region="$REGION" \
  --format='table[no-heading](metadata.name,spec.template.metadata.annotations."autoscaling.knative.dev/minScale",spec.template.metadata.annotations."autoscaling.knative.dev/maxScale")' 2>/dev/null \
  | sed 's/^/    name min max: /' || true
echo "    (policy: min-instances 0 (blank = 0); api max 2; worker max 1)"
echo "Billing reports     : https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo "==================================================="
