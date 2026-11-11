from pathlib import Path
import pandas as pd
root=Path(__file__).resolve().parents[1]
src=(root/'manuscript'/'FSecure_Reconstruction_Aligned_Blue.tex').read_text()
summary=pd.read_csv(root/'executed_results'/'seed_level_summary_95CI.csv')
methods=['eesm_proxy','opportunistic_proxy','supervised_mlp_proxy','fsecure']
labels=['Two-path EESM-style proxy','Three-candidate opportunistic proxy','Supervised MLP proxy','FSecure-WSN reconstruction']
lines=[]
for n in (100,150,200):
 vals=[]
 for meth in methods:
  r=summary[(summary.nodes==n)&(summary.method==meth)&(summary.metric=='pdr_percent')].iloc[0]
  vals.append(f"{r['mean']:.2f} $\\pm$ {r['ci95_halfwidth']:.2f}")
 lines.append(f"{n} & "+' & '.join(vals)+r' \\')
result=r'''
\section{Executed Analytical-Replay Feasibility Experiment (New Results)}
\label{app:executed_60rounds}
\Revised{This section reports a newly executed and independently labeled reconstruction experiment. It is distinct from the original study and does not validate the numerical claims in the preceding Results section. The new reconstruction used a synthetic 300-record source-classification fixture rather than original KDD Cup 99 or NSL-KDD data, because genuine source files were not available in the provided material. The source classifier was trained for 15 epochs; the compatible second hidden layer (2,048 weights and 32 biases) was transferred to the five-input routing scorer. Full second-order MAML was trained for 1,000 meta-episodes with five support-set updates per task, and a supervised 5--32--1 baseline was trained for 50 epochs.}

\Revised{The subsequent evaluation replay used the same 500$\times$500~m$^2$ deployment, external sink coordinate $(250,525)$~m, 50~m geometric link threshold and node populations $\{100,150,200\}$ as the new reference configuration, but only \textbf{60 rounds} per scenario (two generated application packets per round). It comprised ten evaluation seeds (1--10), three attack labels (blackhole, selective forwarding and a Sybil-\emph{labeled packet-drop proxy}), and four routing policies. A total of 360 method--scenario results were generated. Training and validation seeds were disjoint from the evaluation seeds. The source-classification fixture and attack proxies must not be interpreted as real KDD/NSL-KDD observations or genuine Sybil identity-spoofing attacks.}

\begin{table*}[ht]
\centering\scriptsize
\caption{\Revised{New 60-round analytical-replay packet-delivery ratios (\%, mean $\pm$ Student-$t$ 95\% confidence-interval half-width, $n=10$ evaluation seeds). For each seed and node size, the three simulated attack-proxy results were averaged before computing the interval. These values are not those in the original Figures~4--10.}}
\label{tab:new_executed_pdr}
\begin{tabular}{ccccc}
\toprule
Nodes & EESM-style proxy & Opportunistic proxy & Supervised MLP proxy & FSecure reconstruction\\
\midrule
PLACEHOLDERROWS
\bottomrule
\end{tabular}
\end{table*}

\begin{figure*}[ht]
\centering
\includegraphics[width=.82\textwidth]{pdr_seed_ci.png}
\caption{\Revised{New analytical-replay PDR by network size across ten evaluation seeds, averaging the three attack proxy scenarios within each seed; error bars are 95\% Student-$t$ confidence-interval half-widths. This is not an ns-3 LR-WPAN measurement.}}
\label{fig:new_executed_pdr}
\end{figure*}

\begin{figure*}[ht]
\centering
\includegraphics[width=.82\textwidth]{energy_seed_ci.png}
\caption{\Revised{New analytical-replay average per-sensor energy expenditure during 60 routing rounds; intervals are calculated across ten seed-level summaries. The 60-round energy results cannot be compared directly with the previously reported 1,000-round study values.}}
\label{fig:new_executed_energy}
\end{figure*}

\Revised{The new model's packet-delivery ratio was lower than that of the EESM-style proxy at all three evaluated node sizes. This pilot therefore supplies no experimental basis for claiming that the reconstructed FSecure implementation outperforms the comparator proxies. It also highlights a fundamental topology issue: with a 500$\times$500~m$^2$ deployment and 50~m geometric link radius, many scenario realizations have few or no nodes connected by any route to the external sink. The mean numbers of sensor nodes with a geometrically valid path to the sink were 5.4, 43.8 and 113.6 for the 100-, 150- and 200-node cases, respectively, across the ten evaluation geometries. Twelve node-size/seed configurations had no sink-reachable sensor nodes. These failures must be incorporated in any interpretation of delivery performance, rather than silently excluded.}

\Revised{The reconstructed evaluator is an analytical Python packet replay with probabilistic link outcomes, approximate fragmentation and first-order radio-energy accounting, rather than a native ns-3 IEEE 802.15.4 MAC/PHY experiment. The published comparator algorithms have not been faithfully reconstructed, and the synthetic source checkpoint cannot establish the claimed benefit of KDD/NSL-KDD pre-training. The generated raw CSVs, preprocessing manifests, checkpoints, configuration file, test logs and plotting script accompany the new reconstruction package. Consequently, this executed experiment is a technical feasibility and sensitivity assessment only. It must not be substituted into the original manuscript as verification of the historical numerical results or as evidence that all reviewer reproducibility concerns have been conclusively resolved.}
'''.replace('PLACEHOLDERROWS','\n'.join(lines))
# insert after appendix reference implementation, before bibliography
src=src.replace('\\bibliography{sn-bibliography}', result+'\n\\bibliography{sn-bibliography}')
# Add an explicit provenance warning to the front matter as a LaTeX comment rather than incorrectly editing original study's abstract.
src=src.replace('\\begin{document}', '% EXECUTED PILOT APPENDIX: new 60-round analytical replay DOES NOT reproduce historical claims.\n\\begin{document}',1)
(root/'manuscript'/'FSecure_Executed_60Round_Manuscript_Blue.tex').write_text(src)
print('wrote appendix length',len(result))
