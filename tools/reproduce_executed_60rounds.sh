#!/usr/bin/env bash
# Reproduce NEW ANALYTICAL-SURROGATE PILOT ONLY. Not native NS-3 or original paper.
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python tools/make_tasks.py --out outputs/executed_full
python tools/make_smoke_source.py --out outputs/SYNTHETIC_SOURCE_FIXTURE.csv
python tools/pretrain_source.py --source-csv outputs/SYNTHETIC_SOURCE_FIXTURE.csv --out outputs/EXECUTED_SYNTHETIC_SOURCE.pt --epochs 15
python tools/train_meta.py --records outputs/executed_full/candidate_probe_records.csv --source-checkpoint outputs/EXECUTED_SYNTHETIC_SOURCE.pt --out outputs/EXECUTED_FSECURE.pt
python tools/train_supervised_baseline.py --records outputs/executed_full/candidate_probe_records.csv --out outputs/EXECUTED_SUPERVISED.pt
for n in 100 150 200; do
  mkdir -p "outputs/part$n"
  for scenario in outputs/executed_full/scenarios/n${n}_seed*; do
    ln -sfn "$(realpath "$scenario")" "outputs/part$n/$(basename "$scenario")"
  done
  python tools/run_replays.py --records outputs/executed_full/candidate_probe_records.csv --scenarios "outputs/part$n" --meta outputs/EXECUTED_FSECURE.pt --baseline outputs/EXECUTED_SUPERVISED.pt --rounds 60 --out "outputs/EXECUTED_n${n}_60rounds.csv"
done
python tools/create_experiment_report.py
python tools/append_executed_results.py
python -m pytest tests -q
