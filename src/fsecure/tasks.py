"""Candidate-probe task generation, leakage-controlled splits and future-outcome targets.

Synthetic candidate probes are newly generated simulator observations, not historical
run-level data. Missing components are excluded and the observed component weights
renormalized. No future label enters the five pre-decision input features.
"""
from __future__ import annotations
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
from .core import save_scenario,load_scenario,mixed_seed,energy_per_hop

WEIGHTS={'energy':.30,'trust':.30,'link':.25,'delay':.15}

def forward_success_probability(attack, cfg, round_num):
    if round_num < cfg['attack_activation_round']: return 1.0
    if attack=='blackhole':return 0.0
    if attack=='selective':return 1.0-cfg['selective_drop_probability']
    if attack=='sybil_proxy':return 1.0-cfg['sybil_proxy_drop_probability']
    return 1.0

def make_probe_rows(cfg,folder,n,seed,attack,probes):
    nodes,edges=load_scenario(folder)
    rng=np.random.default_rng(mixed_seed(cfg['seed'],n,seed,attack,'probes'))
    if len(edges)==0:return []
    dst_attack=nodes.set_index('node_id').attack_type.to_dict()
    out=[]
    for r in range(probes):
        e=edges.iloc[int(rng.integers(len(edges)))]; target=int(e.dst)
        round_num=int(rng.integers(1,cfg['rounds']+1))
        state_energy=float(rng.uniform(.3,.99)*cfg['initial_energy_j'])
        # Trust is a noisy, historical probe estimate, not a ground-truth attack label.
        prior_success=forward_success_probability(dst_attack[target],cfg,round_num)
        recent_obs=rng.binomial(12, prior_success*.85+.10)/12.
        historical_trust=float(np.clip(.8*.75+.2*recent_obs,0,1))
        predicted_pdr=float(np.clip(e.link_predicted_pdr+rng.normal(0,.03),0,1))
        p=float(e.link_success_probability_surrogate)
        received=bool(rng.random()<p)
        attempted_fwd=received and target!=n
        fwd=bool(rng.random()<prior_success) if attempted_fwd else None
        # Delay only observed when frame received and a forwarding event occurred.
        has_delay=received and (target==n or fwd is True)
        delay_ms=float(e.nominal_delay_ms_surrogate + max(0,rng.normal(0,.3))) if has_delay else np.nan
        tx,rx=energy_per_hop(cfg,float(e.distance_m),int(cfg['frame_payload_bytes_surrogate']))
        out.append({'task_id':f'n{n}_seed{seed}_{attack}','node_count':n,'seed':seed,'attack':attack,
                    'round':round_num,'src':int(e.src),'dst':target,'distance_m':float(e.distance_m),
                    'energy_input':state_energy/cfg['initial_energy_j'],
                    'trust_input':historical_trust,
                    'link_input':float(e.lqi_proxy_0_255)/255.,
                    'pdr_input':predicted_pdr,
                    'delay_input_ms':float(e.nominal_delay_ms_surrogate),
                    'observed_energy_j':float(tx+(rx if received else 0.)),
                    'received':int(received),
                    'forward_outcome':float(fwd) if fwd is not None else np.nan,
                    'observed_delay_ms':delay_ms,
                    'predecision_only':1,
                    'probe_phase':'independent_offline_calibration_not_replay_trace',
                    'backend':'python_reference_surrogate'})
    return out

def generate(cfg,base,smoke=False,ns3_scenarios=None):
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    counts=([20,30,40] if smoke else cfg['node_counts'])
    train_runs=([101,102] if smoke else cfg['training_seeds'])
    val_runs=([107] if smoke else cfg['validation_seeds'])
    test_runs=([1,2] if smoke else cfg['evaluation_seeds'])
    runs=train_runs+val_runs+test_runs
    if len(set(runs))!=len(runs):raise ValueError('Train, validation and evaluation seeds must be disjoint')
    # Smaller connected smoke geometry; does NOT alter the 500 x 500 m study defaults.
    generated_cfg=dict(cfg)
    if smoke: generated_cfg.update({'area_m':120.0,'sink_x_m':60.0,'sink_y_m':125.0})
    rows=[]
    for n in counts:
        for run in runs:
            for attack in ('blackhole','selective','sybil_proxy'):
                p=(Path(ns3_scenarios)/f'n{n}_seed{run}_{attack}' if ns3_scenarios else save_scenario(generated_cfg,n,run,attack,base/'scenarios'))
                if not (p/'nodes.csv').exists() or not (p/'edges.csv').exists():raise FileNotFoundError(p)
                rows+=make_probe_rows(cfg,p,n,run,attack,(45 if smoke else cfg['candidate_probes_per_scenario']))
    df=pd.DataFrame(rows)
    # Partition at FULL SCENARIO level by run, not randomly across probe rows.
    df['split']=np.where(df.seed.isin(train_runs),'train',
                         np.where(df.seed.isin(val_runs),'val','test'))
    if 'val' not in set(df.split) or 'test' not in set(df.split):raise ValueError('Need at least four distinct run IDs')
    train=df[df.split=='train']
    Eref=max(float(train.observed_energy_j.max()),1e-12)
    successful=train.observed_delay_ms.dropna()
    Dref=max(float(successful.max()),1e-12) if len(successful) else 1.0
    # Only TRAINING statistics fitted, then reused on val/test without leakage.
    df['delay_input']=np.minimum(1.,df.delay_input_ms/Dref)
    df['cost_energy']=np.minimum(1.,df.observed_energy_j/Eref)
    df['cost_link']=1-df.received
    df['cost_trust']=1-df.forward_outcome
    df['cost_delay']=np.minimum(1.,df.observed_delay_ms/Dref)
    denom=np.zeros(len(df));num=np.zeros(len(df))
    for key in WEIGHTS:
        c=df['cost_'+key].to_numpy(dtype=float)
        valid=np.isfinite(c)
        denom+=WEIGHTS[key]*valid
        num+=WEIGHTS[key]*np.where(valid,c,0.)
    df['label']=1-num/denom
    df['num_observed_components']=df[['cost_'+k for k in WEIGHTS]].notna().sum(axis=1)
    assert np.isfinite(df.label).all() and df.label.between(0,1).all()
    assert not set(df[df.split=='train'].task_id)&set(df[df.split=='test'].task_id)
    df.to_csv(base/'candidate_probe_records.csv',index=False)
    manifest=df.groupby(['task_id','split','attack','seed','node_count']).size().reset_index(name='examples')
    manifest.to_csv(base/'task_manifest.csv',index=False)
    meta={'provenance':'NEW surrogate probe outcomes, NOT historical paper measurements',
          'energy_reference_j_train_only':Eref,'delay_reference_ms_train_only':Dref,
          'feature_names':['energy_input','trust_input','link_input','pdr_input','delay_input'],
          'label_weights':WEIGHTS,'missing_component_policy':'renormalize weights across observed costs',
          'adaptation_support_provenance':'independent offline calibration probes, not packet events from the later scored replay',
          'splits':'disjoint scenario IDs and seed groups; no row-level mixing',
          'training_seed_ids':train_runs,'validation_seed_ids':val_runs,'test_seed_ids':test_runs,
          'simulator_backend':('ns3_geometry_with_surrogate_probes' if ns3_scenarios else 'python_reference_surrogate'),
          'smoke_geometry_override':({'area_m':120.0,'sink_x_m':60.0,'sink_y_m':125.0} if smoke else None),
          'records':len(df),'num_tasks':manifest.shape[0]}
    (base/'task_preprocessing.json').write_text(json.dumps(meta,indent=2))
    return meta

FEATS=['energy_input','trust_input','link_input','pdr_input','delay_input']
def tasks_from_csv(path,split):
    df=pd.read_csv(path); df=df[df.split==split]
    out={}
    for tid,g in df.groupby('task_id'):
        out[tid]=(g[FEATS].to_numpy('float32'),g.label.to_numpy('float32'))
    return out
