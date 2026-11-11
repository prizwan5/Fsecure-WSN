"""Scenario construction and reproducible analytical-link *surrogate*.

This is not an IEEE 802.15.4 PHY/MAC implementation. To run topology
construction inside ns-3, use ns3/scenario_export.cc to export node positions.
All radio outcomes in the Python replay are drawn from the explicitly defined
log-distance/probabilistic surrogate in this module.
"""
from __future__ import annotations
import json, math, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

ATTACKS = ('none', 'blackhole', 'selective', 'sybil_proxy')

def config(path):
    return json.loads(Path(path).read_text())

def mixed_seed(*pieces):
    digest = hashlib.sha256('|'.join(map(str, pieces)).encode()).digest()
    return int.from_bytes(digest[:8], 'little') % (2**32 - 1)

def make_nodes(cfg, n, run, attack='none'):
    """Create explicit, reproducible geometry with a static external sink (id=n)."""
    rng = np.random.default_rng(mixed_seed(cfg['seed'], n, run, 'placement'))
    xy = rng.uniform(0., cfg['area_m'], (n, 2))
    nodes = pd.DataFrame({'node_id':range(n), 'x_m':xy[:,0], 'y_m':xy[:,1]})
    nodes['is_sink'] = 0
    nodes['attack_type'] = 'none'
    nbad = round(n*cfg['attack_fraction']) if attack!='none' else 0
    if nbad:
        bad_ids = rng.choice(n, size=nbad, replace=False)
        nodes.loc[nodes.node_id.isin(bad_ids), 'attack_type'] = attack
    nodes.loc[len(nodes)] = [n, cfg['sink_x_m'], cfg['sink_y_m'], 1, 'none']
    return nodes

def link_probability(cfg, d):
    if d > cfg['radio_range_m']: return 0.0
    # Explicit new surrogate calibration; not ns-3 LR-WPAN bit-error measurements.
    if d < 1.0: d = 1.0
    rx = cfg['tx_power_dbm'] - cfg['log_distance_reference_loss_db'] - 10.0*cfg['log_distance_exponent']*math.log10(d)
    z = (rx - cfg['rx_threshold_dbm'])/cfg['link_success_scale_db']
    p = 1.0/(1.0+math.exp(-max(-60,min(60,z))))
    return max(0.02,min(0.995,p))

def make_edges(cfg, nodes):
    rec=[]
    rows=nodes.to_dict('records')
    for a in rows:
        for b in rows:
            if a['node_id']==b['node_id'] or int(a['is_sink'])==1: continue
            d=math.hypot(a['x_m']-b['x_m'],a['y_m']-b['y_m'])
            p=link_probability(cfg,d)
            if p==0.: continue
            rec.append({'src':int(a['node_id']),'dst':int(b['node_id']), 'distance_m':d,
                        'link_success_probability_surrogate':p,
                        'lqi_proxy_0_255':int(round(p*255)),
                        'nominal_delay_ms_surrogate':2.5+d/200., 'link_predicted_pdr':p})
    return pd.DataFrame(rec,columns=['src','dst','distance_m','link_success_probability_surrogate','lqi_proxy_0_255','nominal_delay_ms_surrogate','link_predicted_pdr'])

def save_scenario(cfg,n,run,attack,base):
    folder=Path(base)/f'n{n}_seed{run}_{attack}'
    folder.mkdir(parents=True,exist_ok=True)
    nodes=make_nodes(cfg,n,run,attack); edges=make_edges(cfg,nodes)
    nodes.to_csv(folder/'nodes.csv',index=False); edges.to_csv(folder/'edges.csv',index=False)
    meta={'backend':'python_reference_surrogate','not_real_ns3_phy':True,'seed':run,'nodes':n,'attack':attack,
          'config_sha256':hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest()}
    (folder/'metadata.json').write_text(json.dumps(meta,indent=2))
    return folder

def load_scenario(folder):
    folder=Path(folder)
    return pd.read_csv(folder/'nodes.csv'),pd.read_csv(folder/'edges.csv')

def reachability(nodes,edges):
    sink=int(nodes[nodes.is_sink==1].node_id.iloc[0])
    reverse={}
    for e in edges.itertuples(): reverse.setdefault(int(e.dst),set()).add(int(e.src))
    seen={sink}; tovisit=[sink]
    while tovisit:
        for v in reverse.get(tovisit.pop(),set()):
            if v not in seen: seen.add(v); tovisit.append(v)
    return sum(i in seen for i in nodes[nodes.is_sink==0].node_id),len(nodes)-1

def energy_per_hop(cfg,d, payload_bytes):
    bits=8*payload_bytes
    tx = bits*(cfg['radio_e_elec_j_per_bit']+cfg['radio_epsilon_j_per_bit_m2']*d**cfg['radio_path_loss_exponent'])
    rx = bits*cfg['radio_e_elec_j_per_bit']
    return tx,rx

def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
