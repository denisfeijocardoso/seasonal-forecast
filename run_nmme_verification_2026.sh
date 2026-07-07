#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/scripts/clima/denis/seasonal"
PYTHON="/scripts/subsaz/miniconda3/envs/subc/bin/python"

YEAR="${YEAR:-2026}"
BASE="${BASE:-nmme}"
MAP_WORKERS="${MAP_WORKERS:-4}"
LOG_DIR="${REPO_DIR}/src/logs"
RUN_LOG="${LOG_DIR}/verification_${BASE}_${YEAR}_all_months.log"

mkdir -p "${LOG_DIR}"
cd "${REPO_DIR}"

echo "Inicio da verificacao operacional: base=${BASE} year=${YEAR}" | tee -a "${RUN_LOG}"
date -u | tee -a "${RUN_LOG}"

for MONTH in $(seq 1 12); do
    MONTH_PADDED="$(printf "%02d" "${MONTH}")"
    echo "==== Mes ${MONTH_PADDED}: inicio ====" | tee -a "${RUN_LOG}"
    date -u | tee -a "${RUN_LOG}"

    "${PYTHON}" -m src.run.operational_verification \
        --base "${BASE}" \
        --year "${YEAR}" \
        --month "${MONTH}" \
        --skip-download \
        --skip-interpolation \
        --exclude-model cansips \
        --map-workers "${MAP_WORKERS}" 2>&1 | tee -a "${RUN_LOG}"

    echo "==== Mes ${MONTH_PADDED}: fim ====" | tee -a "${RUN_LOG}"
    date -u | tee -a "${RUN_LOG}"
done

echo "Fim da verificacao operacional: base=${BASE} year=${YEAR}" | tee -a "${RUN_LOG}"
date -u | tee -a "${RUN_LOG}"
