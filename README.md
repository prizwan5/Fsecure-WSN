# FSecure-WSN: independently authored reconstruction (NOT original experiment artifacts)

This package is a reproducible implementation **starting point** consistent with much of the paper's specified mathematical framework. It does not retrieve, authenticate, or recreate the historical code and measurements behind the paper. In particular, the native NS-3 source exports real ns-3 node geometry and instantiates LR-WPAN devices, while the Python forwarding simulation is an explicitly designated **analytical packet replay**, not native LR-WPAN PHY/MAC execution. EESM, Opportunistic and supervised-network baselines are **proxies**, not faithful replications of the cited publications. See `supplement/RECONSTRUCTION_PROTOCOL.md`.

## Files corresponding to the four requested categories

| Requested item | Delivered location |
|---|---|
| 1. Python/PyTorch preprocessing, transfer and MAML | `src/fsecure/{source,models,tasks}.py`, `tools/{pretrain_source,make_tasks,train_meta}.py` |
| 2. NS-3 C++ and configuration | `ns3/fsecure_scenario_export.cc`, `config/experiment.json`, `tools/build_ns3_scenarios.sh` |
| 3. Comparator implementations and exact NEW settings | `src/fsecure/{baselines,evaluate}.py`, `tools/train_supervised_baseline.py`, `config/experiment.json` |
| 4. Run CSVs and checkpoint creation | `tools/{run_replays,summarize}.py`, `outputs/smoke_*` (test data only); real datasets and runs generate `outputs/reference` etc. |

## Install and run the tested Python smoke pipeline

Python 3.10+ recommended. From the extracted package directory:

```bash
python -m pip install -r requirements.txt
python tools/make_tasks.py --smoke --out outputs/smoke
python tools/make_smoke_source.py --out outputs/SMOKE_SYNTHETIC_SOURCE_NOT_KDD.csv
python tools/pretrain_source.py --source-csv outputs/SMOKE_SYNTHETIC_SOURCE_NOT_KDD.csv --out outputs/SMOKE_SOURCE_NOT_PUBLIC_DATA.pt --epochs 2
python tools/train_meta.py --smoke --records outputs/smoke/candidate_probe_records.csv --source-checkpoint outputs/SMOKE_SOURCE_NOT_PUBLIC_DATA.pt --out outputs/SMOKE_TRANSFER_META.pt
python tools/train_supervised_baseline.py --records outputs/smoke/candidate_probe_records.csv --out outputs/smoke_ai.pt --epochs 2
python tools/run_replays.py --smoke --scenarios outputs/smoke/scenarios --records outputs/smoke/candidate_probe_records.csv --meta outputs/SMOKE_TRANSFER_META.pt --baseline outputs/smoke_ai.pt --out outputs/smoke_replays.csv
python tools/summarize.py --csv outputs/smoke_replays.csv --out outputs/smoke_summary.csv
python -m pytest tests -q
```

The output contains a **synthetic KDD-shaped fixture**; it is *not* an actual intrusion dataset. The small 120 m smoke geometry is *not* the paper's 500 m geometry. Do not publish any smoke-test metrics.

## Run the new complete reference experiment with real public source data

Download genuine KDD Cup 1999 / NSL-KDD CSV or `.txt` files from their public providers. Keep test files out of source pretraining. The parser accepts unlabeled-header files with 42 (KDD) or 43 (NSL) fields; it drops the NSL difficulty column and encodes the true class. It removes exact feature/label duplicates before the source split. Audit near-duplicates between KDD and NSL and document data release/checksums before publication.

```bash
python tools/pretrain_source.py --source-csv datasets/KDDTrain+.txt --out outputs/source_real.pt --epochs 15
python tools/make_tasks.py --out outputs/reference
python tools/train_meta.py --records outputs/reference/candidate_probe_records.csv --source-checkpoint outputs/source_real.pt --out outputs/fsecure_meta.pt
python tools/train_supervised_baseline.py --records outputs/reference/candidate_probe_records.csv --out outputs/ai_proxy.pt
python tools/run_replays.py --records outputs/reference/candidate_probe_records.csv --scenarios outputs/reference/scenarios --meta outputs/fsecure_meta.pt --baseline outputs/ai_proxy.pt --out outputs/replay_per_run.csv
python tools/summarize.py --csv outputs/replay_per_run.csv --out outputs/replay_summary.csv
```

The full reference configuration uses 100/150/200 nodes, a 500×500 m field, a sink at (250,525), 50 m nominal range, 10 independent test seeds (1–10), separate training seeds (101–106), validation (107–108), and 1000 routing rounds. The resulting outputs **will not necessarily match** the historical 1.0 J, 95% PDR or other paper figures; discrepancies must be reported, not overwritten.

## Run the ns-3 topology export (external ns-3 installation required)

Install a compatible ns-3 release with `lr-wpan` enabled, and define `NS3_ROOT` as the checkout containing `./ns3`:

```bash
export NS3_ROOT=/path/to/ns-3.x
bash tools/build_ns3_scenarios.sh
python tools/make_tasks.py --ns3-scenarios outputs/ns3_scenarios --out outputs/ns3_reference
# train_meta, train_supervised_baseline, run_replays, summarize as above,
# setting --records outputs/ns3_reference/candidate_probe_records.csv
# and --scenarios outputs/ns3_scenarios
```

**NS-3 compilation was not tested in the present environment**, which lacks an ns-3 installation. The C++ topology export uses established LrWpanHelper APIs; API differences may require adjustment for the local ns-3 release. It exports **geometry and analytic link proxies, not actual 802.15.4 packet performance**.

## Artifacts, data separation and limitations

`candidate_probe_records.csv` contains pre-decision five features and outcomes of a separate offline calibration/probe run (not events copied from subsequent scored packet replay), with explicit missing-component handling; `task_manifest.csv` records scenario-group splits; `task_preprocessing.json` fixes train-only normalization scales. PyTorch files `source_real.pt`, `fsecure_meta.pt`, `ai_proxy.pt` are newly trained checkpoints with metadata/checksums. `replay_per_run.csv` contains one row per test scenario and method; `replay_summary.csv` summarizes each attack/node/method stratum. Results do not estimate statistical significance against the original paper unless original run-level paired data become available.

Original packet captures, original baseline source, historical checkpoints, and historical 10-run CSVs were not provided and are **not** part of this archive. Do not call the newly generated outputs “original”.

`manuscript/FSecure_Reconstruction_Aligned_Blue.tex` appends a clearly identified reference-reconstruction protocol to the existing paper without falsely claiming that these reference scripts generated its historical figures.
