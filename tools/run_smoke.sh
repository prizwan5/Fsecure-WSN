#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python tools/make_tasks.py --smoke --out outputs/smoke
python tools/make_smoke_source.py --rows 180 --out outputs/SMOKE_SYNTHETIC_SOURCE_NOT_KDD.csv
python tools/pretrain_source.py --source-csv outputs/SMOKE_SYNTHETIC_SOURCE_NOT_KDD.csv --out outputs/SMOKE_SOURCE_NOT_PUBLIC_DATA.pt --epochs 2
python tools/train_meta.py --smoke --records outputs/smoke/candidate_probe_records.csv --source-checkpoint outputs/SMOKE_SOURCE_NOT_PUBLIC_DATA.pt --out outputs/SMOKE_TRANSFER_META.pt
python tools/train_supervised_baseline.py --records outputs/smoke/candidate_probe_records.csv --out outputs/smoke_ai.pt --epochs 2
python tools/run_replays.py --smoke --scenarios outputs/smoke/scenarios --records outputs/smoke/candidate_probe_records.csv --meta outputs/SMOKE_TRANSFER_META.pt --baseline outputs/smoke_ai.pt --out outputs/smoke_replays_transfer.csv
python tools/summarize.py --csv outputs/smoke_replays_transfer.csv --out outputs/smoke_summary_transfer.csv
python tools/export_provenance.py
python -m pytest tests -q
printf '\nDONE. All smoke artifacts are synthetic reference tests; not historical experimental data.\n'
