#!/usr/bin/env bash
# Re-runs the whole project from the raw CSV. Usage: bash run_all.sh
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"

mkdir -p data outputs
if [ ! -f data/telco_raw.csv ]; then
  curl -sSL -o data/telco_raw.csv \
    https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv
fi

$PY src/01_clean.py data/telco_raw.csv data/telco_clean.csv
$PY src/02_run_sql.py data/telco_clean.csv sql/queries.sql outputs
$PY src/03_stats_and_model.py data/telco_clean.csv outputs
$PY src/04_dashboard.py data/telco_clean.csv outputs
echo "Done. See outputs/ and README.md"
