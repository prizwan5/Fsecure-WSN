"""Independent packet-level *surrogate replay* using exported scenario geometry.

Not an implementation of over-the-air ns-3 LR-WPAN. Packet/frame attempts,
losses, energy and forwarding events are simulated in Python with an explicit
analytical model. Only verified reference-reconstruction outputs may be reported.
"""
from __future__ import annotations
import math, json
from pathlib import Path
import numpy as np,pandas as pd,torch
from torch.func import functional_call
from .core import mixed_seed,energy_per_hop,load_scenario,reachability
from .tasks import forward_success_probability,FEATS
from .models import RoutingNet,SupervisedBaselineNet,adapt
from .baselines import shortest_path,next_hop_candidates

METHODS=('eesm_proxy','opportunistic_proxy','supervised_mlp_proxy','fsecure')

def graph_from_frames(nodes,edges):
    graph={}; eidx={}
    for e in edges.to_dict('records'):
        u,v=int(e['src']),int(e['dst']);graph.setdefault(u,[]).append((v,e));eidx[u,v]=e
    coords={int(r.node_id):(float(r.x_m),float(r.y_m)) for r in nodes.itertuples()}
    return graph,eidx,coords

def scorer(model):
    model.eval()
    def fn(x):
        with torch.no_grad():return model(torch.tensor(x,dtype=torch.float32).unsqueeze(0)).item()
    return fn

def loaded_models(meta_path,baseline_path,records_path,task_id,cfg):
    meta=torch.load(meta_path,weights_only=False,map_location='cpu')
    baseline=torch.load(baseline_path,weights_only=False,map_location='cpu')
    m=RoutingNet();m.load_state_dict(meta['model'])
    b=SupervisedBaselineNet(cfg['baselines']['supervised_mlp_proxy']['hidden_neurons']);b.load_state_dict(baseline['model'])
    # Test-time support is labeled synthetic candidate-probe data from this realization.
    # Independent forwarding RNG streams are used during later replay; no query labels adapted.
    records=pd.read_csv(records_path)
    support=records[(records.task_id==task_id)&(records.split=='test')].head(cfg['task_support'])
    if len(support)==cfg['task_support']:
        sx=torch.tensor(support[FEATS].to_numpy('float32'))
        sy=torch.tensor(support.label.to_numpy('float32'))
        fast=adapt(m,sx,sy,cfg['inner_steps'],cfg['inner_lr'],second_order=False)
        params={k:v.detach() for k,v in fast.items()}
        def adapted(x):
            with torch.no_grad():return functional_call(m,params,(torch.tensor(x,dtype=torch.float32).unsqueeze(0),)).item()
        m_score=adapted
    else:m_score=scorer(m)
    return {'fsecure':m_score,'supervised_mlp_proxy':scorer(b)}

def replay(cfg,scenario,method,score_lookup,seed,rounds,packets_per_round,delay_ref):
    nodes,edges=load_scenario(scenario)
    graph,eidx,coords=graph_from_frames(nodes,edges)
    sink=int(nodes[nodes.is_sink==1].node_id.iloc[0]); n=sink
    attacks=nodes.set_index('node_id').attack_type.to_dict()
    state={'energy':np.full(n+1,cfg['initial_energy_j'],dtype=float),
           'trust':np.full(n+1,.75,dtype=float),
           'min_energy':cfg['energy_threshold_j'],'delay_ref':delay_ref}
    state['trust'][sink]=1.
    generated=received=0;latencies=[];packet_ctrl=0;first_death=None;routes=[]
    frames_per_app=math.ceil(cfg['packet_bytes_application']/cfg['frame_payload_bytes_surrogate'])
    tx_retries=cfg['mac_max_retries_surrogate']+1
    reachable,total=reachability(nodes,edges)
    for rnd in range(1,rounds+1):
        for index in range(packets_per_round):
            packet_id=(rnd-1)*packets_per_round+index
            src=int(np.random.default_rng(mixed_seed(cfg['seed'],seed,n,'source',packet_id)).integers(n))
            generated+=1
            # EESM path redundancy is a new, simplified two-path proxy.
            if method=='eesm_proxy':
                p1=shortest_path(graph,src,sink,state,trust_floor=cfg['baselines']['eesm_proxy']['trust_floor'])
                ban={(p1[0],p1[1])} if len(p1)>1 else set()
                p2=shortest_path(graph,src,sink,state,trust_floor=cfg['baselines']['eesm_proxy']['trust_floor'],banned_edges=ban)
                routes=[p for p in (p1,p2) if p][:cfg['baselines']['eesm_proxy']['max_disjoint_routes']]
            else: routes=[]
            choices=(routes if method=='eesm_proxy' else [None])
            delivered=False;packet_delay=0.
            for ridx,route in enumerate(choices):
                current=src;visited={src}; hops=0;failed=False;local_delay=0.
                while current!=sink and hops<cfg['max_hops']:
                    if method=='eesm_proxy':
                        if not route or hops+1>=len(route): failed=True;break
                        v=int(route[hops+1]);e=eidx.get((current,v));
                        if e is None:failed=True;break
                        candidate_list=[(1.,v,e)]
                    else:
                        candidate_list=next_hop_candidates(method,graph,current,sink,coords,state,cfg,score_lookup.get(method))
                        if method=='opportunistic_proxy': candidate_list=candidate_list[:cfg['baselines']['opportunistic_proxy']['candidate_set_size']]
                    if not candidate_list:failed=True;break
                    hop_success=False
                    for priority,v,e in candidate_list:
                        if v in visited:continue
                        packet_ctrl+=1
                        hop_energy=0.;hop_time=0.; all_fragments=True
                        for f in range(frames_per_app):
                            frag_bytes=min(cfg['frame_payload_bytes_surrogate'], cfg['packet_bytes_application']-f*cfg['frame_payload_bytes_surrogate'])
                            for attempt in range(tx_retries):
                                hop_time+=float(e['nominal_delay_ms_surrogate'])
                                etx,erx=energy_per_hop(cfg,float(e['distance_m']),frag_bytes+15)
                                state['energy'][current]-=etx
                                u=np.random.default_rng(mixed_seed(cfg['seed'],seed,n,packet_id,current,v,f,attempt,'radio')).random()
                                ok=u < float(e['link_success_probability_surrogate'])
                                if ok:state['energy'][v]-=erx
                                if ok:break
                            else: all_fragments=False;break
                        local_delay+=hop_time
                        if not all_fragments:
                            if method!='opportunistic_proxy':break
                            local_delay+=cfg['baselines']['opportunistic_proxy']['coordination_delay_ms']
                            continue
                        # Malicious forwarding action is separate from radio delivery.
                        pforward=forward_success_probability(attacks.get(v,'none'),cfg,rnd)
                        if v!=sink:
                            u=np.random.default_rng(mixed_seed(cfg['seed'],seed,n,packet_id,current,v,'forward')).random()
                            forwarded=u < pforward
                            state['trust'][v]=cfg['trust_forgetting_factor']*state['trust'][v]+(1-cfg['trust_forgetting_factor'])*float(forwarded)
                            if not forwarded:
                                if method!='opportunistic_proxy':break
                                continue
                        current=v;visited.add(v);hops+=1;hop_success=True
                        break
                    if not hop_success: failed=True;break
                if current==sink and not failed:
                    delivered=True;packet_delay+=local_delay;break
            if delivered:
                received+=1;latencies.append(packet_delay)
            if first_death is None and (state['energy'][:n]<=0).any():first_death=rnd
    true_mal=np.array([attacks.get(i,'none')!='none' for i in range(n)],dtype=bool)
    predicted_mal=state['trust'][:n]<cfg['trust_threshold']
    accuracy=float((true_mal==predicted_mal).mean()) if method=='fsecure' else float('nan')
    return {'method':method,'node_count':n,'seed':seed,'attack':('none' if not true_mal.any() else str(nodes[nodes.attack_type!='none'].attack_type.iloc[0])),
            'generated_packets':generated,'delivered_packets':received,'pdr_percent':100*received/max(1,generated),
            'mean_delay_ms_delivered_only':float(np.mean(latencies)) if latencies else float('nan'),
            'energy_j_per_sensor_mean':float(np.mean(cfg['initial_energy_j']-state['energy'][:n])),
            'first_node_death_round':first_death if first_death is not None else rounds+1,
            'attack_detection_accuracy_percent':accuracy*100 if not math.isnan(accuracy) else float('nan'),
            'control_decisions_proxy_count':packet_ctrl,'geometrically_sink_reachable_nodes':reachable,
            'total_sensor_nodes':total,'backend':'python_packet_replay_surrogate_NOT_ns3_MAC'}
