"""Derive fresh CIs from generated per-run CSVs; never reuse prior manuscript values."""
import argparse
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import t
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--csv',default='outputs/replay_per_run.csv');p.add_argument('--out',default='outputs/replay_summary.csv')
a=p.parse_args();df=pd.read_csv(a.csv)
metrics=['pdr_percent','mean_delay_ms_delivered_only','energy_j_per_sensor_mean','attack_detection_accuracy_percent']
res=[]
for (n,attack,method),g in df.groupby(['node_count','attack','method']):
    for metric in metrics:
        x=g[metric].dropna().to_numpy(float)
        if len(x)==0:continue
        mean=float(x.mean());ci=float(t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x))) if len(x)>=2 else float('nan')
        res.append({'nodes':n,'attack':attack,'method':method,'metric':metric,'n_runs':len(x),'mean':mean,'ci95_halfwidth':ci})
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(res).to_csv(out,index=False)
for metric in ('pdr_percent','energy_j_per_sensor_mean'):
    subset=pd.DataFrame(res);subset=subset[subset.metric==metric]
    fig,ax=plt.subplots(figsize=(8,5))
    for (attack,method),z in subset.groupby(['attack','method']):
        z=z.sort_values('nodes'); ax.errorbar(z.nodes,z['mean'],yerr=z['ci95_halfwidth'].where(z.n_runs>=2,0),marker='o',label=f'{method} ({attack})')
    ax.set_xlabel('Sensor nodes');ax.set_ylabel(metric.replace('_',' '));ax.set_title('NEW reference reconstruction (not original results)')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out.parent/f'{metric}_reconstruction.png',dpi=160);plt.close(fig)
print('saved',out)
