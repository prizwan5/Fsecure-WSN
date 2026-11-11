# Actual executions completed in this session

**Experiment class:** independently implemented Python analytical packet-replay surrogate, *not* ns-3 IEEE 802.15.4 MAC/PHY. The C++ ns-3 program in the package is a geometry/device scenario exporter, not a native packet-delivery simulator.

## Completed runs
- 162 complete topology/attack/seed tasks; 48,600 candidate-probe records across training, validation and test groups.
- Pretraining: 15 epochs on a synthetic 300-record KDD-shaped fixture (`SYNTHETIC_SOURCE_FIXTURE.csv`) because no genuine KDD Cup 99 or NSL-KDD data were available. This does not test published-source pretraining.
- Full second-order MAML: 1,000 episodes, five inner adaptation steps, 4 tasks/meta-batch, Adam outer update. A new checkpoint was saved.
- Supervised MLP baseline: 50 training epochs. A new checkpoint was saved.
- Packet replay: 60 routing rounds × 2 generated packets/round × 3 node counts × 10 evaluation seeds × 3 attack proxies × 4 methods = 360 method-scenario records (43,200 generated application packets across methods).
- Automated tests: 4 passed.

The original attempted 1,000-round comparison exceeded the execution time limit and yielded no completed per-run CSV. **Do not describe the new data as a completed 1,000-round experiment.** The 60-round outputs are freshly calculated, not reconstructed from the paper's earlier values.

## Key caveats
- The three baseline algorithms are independently developed proxy policies, *not* the cited published baseline implementations.
- `sybil_proxy` simulates packet drops, not identity spoofing.
- 512-byte application packets use approximate frame segmentation; native IEEE 802.15.4 behavior was not simulated.
- 95% confidence intervals are formed across 10 seed-level quantities, after averaging the three attack scenarios within each seed. These intervals do not establish significance of method comparisons.
- Delay means condition on successful deliveries and may have fewer than ten contributing seeds, so comparison can be selection-biased; missing delays are not zero.
- First-node death is right-censored at 60 rounds when no node dies; the replay cannot estimate the 1,000-round lifetime metric.
- Original historical performance numbers in the manuscript remain unverified and must not be represented as reproduced by this reconstruction.

## Exact numeric parameters
See `config/experiment.json`, `executed_results/provenance.json`, `outputs/executed_full/task_preprocessing.json` and `outputs/baseline_parameter_log.json`.

## Reproduce 60-round summaries
`python tools/create_experiment_report.py` (requires outputs/EXECUTED_n{100,150,200}_60rounds.csv).
