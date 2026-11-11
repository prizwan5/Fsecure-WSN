# FSecure-WSN — independently written executable reconstruction

**Provenance:** These programs were newly authored to test and refine the mathematical specification in the author's manuscript. They are **not recovered 2026 experiment code**, not the original EESM, Opportunistic, or AI-CPS implementations, and they do **not** establish provenance for figures in the submitted article.

## Model and numerical settings in config/experiment.json

- FSecure WSN routing scorer: five features, hidden widths 64 and 32, ReLU, sigmoid scalar output; source transfer copies **fc2.weight (32×64)** and **fc2.bias (32)** only.
- Source pretraining: 41 original KDD/NSL-KDD attributes, three categorical variables, train-only vocabulary and standardization, BCE source head; newly specified 15 epochs, 128 batch, Adam 0.001. Real source CSVs must be separately downloaded.
- Routing-target costs: observed per-frame energy, 1−observed forwarding success, 1−observed link delivery, normalized successful-frame delay. The 0.30/0.30/0.25/0.15 weights are renormalized when components are genuinely unavailable. Reference scales E_ref and D_ref are fitted **only on training scenarios**.
- MAML: five inner functional-SGD updates, α=0.01; all trainable layers; full second-order meta-gradient; Adam outer η=0.001; four tasks per batch; eight support and sixteen query records; 1000 episodes by default.
- Source-data and WSN scenario splits are distinct. WSN training seeds: 101–106, validation 107–108, independent evaluation 1–10; 100/150/200 nodes; all 3 *surrogate* attack cases.
- Node positions: uniformly scattered in 500×500 m; sink at (250,525) m, static; radius 50 m; initial energy 2 J; 1000 rounds; 2 generated application packets/round; 512-byte application payload.
- No native 512-byte IEEE 802.15.4 frame exists. The **Python analytical replay** instead divides 512 bytes into six chunks of ≤96-byte payload plus assumed 15-byte framing, with up to 3 retries; this is *not* the ns-3 LR-WPAN MAC/reassembly stack.
- Link success is an explicitly specified logistic/log-distance analytical approximation, not measured IEEE802.15.4 PHY BER or LQI. Tx 0 dBm, path-loss reference 40 dB, path-loss exponent 3, receive threshold −91 dBm, logistic scale 3.5 dB; p is capped to [0.02,0.995] within 50 m, zero beyond. `lqi_proxy_0_255`=round(255p), **not observed LQI**.
- First-order transmit model: electronics 50 nJ/bit, amplifier 100 pJ/(bit·m²), exponent 2; reception electronics 50 nJ/bit. Delay and MAC costs are surrogate values. Receiver idle energy is not modeled.
- Attack injection: 15% adversarial sensor IDs, starts round 10; blackhole drop=1; selective forwarding drop=0.5; `sybil_proxy` drop=0.3. `sybil_proxy` **does not model forged identities or Sybil authentication** and cannot validate full Sybil resistance.
- EESM-style proxy: 2 shortest security-screened paths, backup first-edge exclusion; re-compute for each application packet, trust floor 0.6. Not the fully specified EESM literature algorithm.
- Opportunistic-style proxy: 3 candidate neighbors selected using link-success × geographic progress, 2 ms coordination penalty. No realistic overhearing or hidden-terminal control.
- AI proxy: single-hidden-layer supervised neural routing scorer 5–32–1, trained 50 epochs with Adam 0.001, batch 64. This is not the cited AI-CPS baseline.
- NS-3 C++ file installs `LrWpanHelper` devices for reproducible deployment geometry, exports nodes/links, and uses only **surrogate link probabilities**. It does **not** transmit the routing/application packets via LR-WPAN. Actual multi-hop on-air protocol validation would require an additional implementation.

## What can be claimed after running these files

The code can generate new scenario manifests, newly fitted checkpoints, matched simulated per-run outputs, and newly calculated CIs for the explicit analytical-replay protocol. None of these makes the historical manuscript means or their error bars independently reproducible. Results must be labeled `new reference reconstruction` until a genuine 802.15.4 packet-level NS-3 experiment and faithful comparator implementations are developed and run.

## Data/code availability

The public KDD99 and NSL-KDD datasets are not copied into this bundle. The original authors' code, checkpoints, and original raw output CSVs were not supplied. This folder is an **unpublished reconstruction source bundle** supplied for author testing; it has no registered DOI, stable URL, or deposited supplemental identifier. A public-availability statement should be updated **only after successful upload**.
