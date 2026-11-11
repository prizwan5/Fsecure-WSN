"""Produce a new-analysis report only from executed, labelled surrogate CSVs."""
import json, hashlib
from pathlib import Path
import pandas as pd, numpy as np
from scipy.stats import t
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'; ART=ROOT/'executed_results'; ART.mkdir(exist_ok=True)
run=pd.concat([pd.read_csv(OUT/f'EXECUTED_n{n}_60rounds.csv') for n in [100,150,200]],ignore_index=True)
assert len(run)==360 and run.groupby(['node_count','attack','method']).size().eq(10).all()
run.to_csv(ART/'per_run_360_rows.csv',index=False)
# Average attack proxies WITHIN evaluation seed, so each uncertainty estimate has 10 independent seed units
seedagg=run.groupby(['node_count','seed','method'],as_index=False).agg(pdr_percent=('pdr_percent','mean'), energy_j_per_sensor_mean=('energy_j_per_sensor_mean','mean'), reachable_nodes=('geometrically_sink_reachable_nodes','mean'))
seedagg.to_csv(ART/'per_seed_120_rows.csv',index=False)
rows=[]
for (n,m),g in seedagg.groupby(['node_count','method']):
 for metric in ['pdr_percent','energy_j_per_sensor_mean','reachable_nodes']:
  x=g[metric].values; rows.append({'nodes':n,'method':m,'metric':metric,'n_independent_seeds':len(x),'mean':x.mean(),'sample_sd':x.std(ddof=1),'ci95_halfwidth':t.ppf(.975,9)*x.std(ddof=1)/np.sqrt(10)})
sm=pd.DataFrame(rows);sm.to_csv(ART/'seed_level_summary_95CI.csv',index=False)
cols={'eesm_proxy':'EESM-style proxy','opportunistic_proxy':'Opportunistic proxy','supervised_mlp_proxy':'Supervised MLP proxy','fsecure':'FSecure reconstruction'}
for metric,ylabel,fname in [('pdr_percent','Packet delivery ratio (%)','pdr_seed_ci.png'),('energy_j_per_sensor_mean','Average per-sensor energy expenditure (J)','energy_seed_ci.png')]:
 fig,ax=plt.subplots(figsize=(8,4.8))
 for method,name in cols.items():
  s=sm[(sm.method==method)&(sm.metric==metric)].sort_values('nodes'); ax.errorbar(s.nodes,s['mean'],yerr=s.ci95_halfwidth,marker='o',capsize=4,label=name)
 ax.set_xlabel('Sensor nodes'); ax.set_ylabel(ylabel);ax.set_xticks([100,150,200]);ax.set_ylim(bottom=0);ax.grid(alpha=.2);ax.legend(fontsize=8)
 ax.set_title('60-round analytical replay — 10 seeds; 3 attack proxies averaged')
 fig.tight_layout();fig.savefig(ART/fname,dpi=180);plt.close(fig)
# Provenance, all hashes
hashfiles=['config/experiment.json','outputs/EXECUTED_SYNTHETIC_SOURCE.pt','outputs/EXECUTED_FSECURE.pt','outputs/EXECUTED_SUPERVISED.pt','outputs/executed_full/candidate_probe_records.csv']
prov={'result_category':'NEW 60-round analytical packet replay, not native NS-3, not original study', 'source_dataset':'300-row SYNTHETIC KDD-shaped fixture, not real KDD Cup 99 or NSL-KDD','node_counts':[100,150,200],'attacks':['blackhole','selective','sybil_proxy'],'evaluation_seeds':list(range(1,11)),'rounds_per_scenario':60,'packets_per_round':2,'rows':len(run),'checkpoint_transfer':'source fc2.weight (32x64) and fc2.bias (32) copied; test checkpoint synthetic source','model_training':'1000 second-order MAML episodes; five adaptation steps; outer Adam; meta batch 4','baseline_validity':'three independently developed proxies, not published baseline implementations','radio_backend':'Python analytical probability and energy replay, not native NS-3 MAC or PHY','files_sha256':{}}
for name in hashfiles:
 f=ROOT/name;prov['files_sha256'][name]=hashlib.sha256(f.read_bytes()).hexdigest()
(ART/'provenance.json').write_text(json.dumps(prov,indent=2))
# reports
print(sm[(sm.metric=='pdr_percent')].pivot(index='nodes',columns='method',values='mean').round(2).to_string())
print('saved',ART)
