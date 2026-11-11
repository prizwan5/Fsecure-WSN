# FSecure-WSN — newly executed preliminary reconstruction (11 November 2026)

**Evidence level:** Executed Python analytical packet replay, **not** full ns-3 IEEE 802.15.4 simulation and **not** recovery of the original paper's data.

## Execution

Training: synthetic (not KDD/NSL-KDD) source classifier, 15 epochs; second-hidden-layer transfer of 2,080 parameters; full second-order MAML, 1,000 episodes, five inner updates; supervised MLP baseline, 50 epochs. Ten evaluation seeds (1–10) were distinct from training seeds 101–106 and validation seeds 107–108. The packet replay ran **60 rounds** per node-count/attack/method combination, with two application packets per round. There were 360 complete method–scenario output rows, 162 generated scenario tasks across training/validation/testing, and 48,600 candidate-probe records.

## Observed packet delivery ratio (%)

Values below are means across ten seed-level values, after averaging the three attack categories within each seed. The reported interval widths are Student-t 95% confidence-interval half-widths, not significance tests.

| Nodes | EESM-style proxy | Opportunistic-style proxy | Supervised MLP proxy | FSecure reconstruction |
|--:|--:|--:|--:|--:|
| 100 | 4.39 ± 5.92 | 4.17 ± 6.21 | 3.92 ± 5.82 | 3.72 ± 5.53 |
| 150 | 7.42 ± 7.92 | 5.00 ± 4.46 | 2.78 ± 2.62 | 2.83 ± 2.63 |
| 200 | 19.06 ± 14.44 | 16.39 ± 14.32 | 14.22 ± 11.80 | 11.72 ± 10.56 |

Values at the low end can produce negative unbounded t-interval lower limits; these are not physically meaningful probability estimates. The plotted vertical axis is truncated at zero, without altering the calculations.

## Important engineering finding

The sink is outside the 500×500 m² field at (250,525) m, and the 50 m geometric radio limit often results in disconnected deployments. Mean numbers of sink-reachable sensor nodes across ten seeds were 5.4/100, 43.8/150, and 113.6/200. Twelve node-count/seed geometries had no sensor able to reach the sink at all. The reconstructed FSecure model does not beat the EESM-style proxy on aggregate PDR under these settings. Packet-delivery comparisons cannot be interpreted independently of topology connectivity.

## What these results do NOT show

- They do not replicate the original 1,000-round numerical results, including the original paper's 44.4% energy reduction or 94% attack-detection accuracy.
- They are not based on genuine KDD Cup 99 or NSL-KDD source training data (a **synthetic fixture** is used).
- They do not use real ns-3 MAC/PHY packet transmissions or faithful reproductions of the cited baseline implementations.
- The Sybil-labeled proxy does not implement fraudulent identities.
- 60-round experiments cannot establish the network lifetime metric over 1,000 rounds.
- No formal between-method hypothesis tests were performed.

## Artifacts

- `per_run_360_rows.csv`: detailed run-level results.
- `per_seed_120_rows.csv`: attack-averaged, seed-level independent reporting units.
- `seed_level_summary_95CI.csv`: sample SD, means and t-interval half-widths.
- `pdr_seed_ci.png`, `energy_seed_ci.png`: graphs derived solely from executed CSVs.
- `provenance.json`: exact source configuration and checkpoint SHA-256 hashes.
- `../outputs/executed_full/task_manifest.csv`: scenario task split manifest.
- `../outputs/executed_full/task_preprocessing.json`: training-only normalizers.
- `../outputs/EXECUTED_FSECURE.pt`: new MAML checkpoint.
- `../outputs/EXECUTED_SUPERVISED.pt`: new supervised baseline checkpoint.
- `../tools/reproduce_executed_60rounds.sh`: reproducible commands.

**Manuscript handling:** The experiment appendix reports this pilot separately. Do not replace original 1,000-round performance claims with these 60-round data without redesigning and fully repeating the appropriate experiment.
