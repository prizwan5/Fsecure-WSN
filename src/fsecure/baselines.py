"""Explicit NEW comparison *proxies*, not faithful reproductions of cited protocols.

These algorithms intentionally have different policy logic and independently
stored numerical settings. Do not identify their outcomes as outcomes of the
original published EESM, Opportunistic, or AI-CPS implementations.
"""
from __future__ import annotations
import heapq,math

def shortest_path(graph,src,sink,state,trust_floor=0.,banned_edges=frozenset()):
    """Energy/trust-aware Dijkstra with loop-free parent recovery."""
    q=[(0.,int(src),(int(src),))];best={int(src):0.}
    while q:
        cost,u,path=heapq.heappop(q)
        if u==sink:return list(path)
        if cost>best.get(u,float('inf')):continue
        for v,e in graph.get(u,[]):
            if (u,v) in banned_edges or v in path:continue
            if v!=sink and state['trust'][v]<trust_floor:continue
            if v!=sink and state['energy'][v]<state['min_energy']:continue
            p=float(e['link_success_probability_surrogate'])
            new=cost+1./max(.05,p)+.2*e['distance_m']/50.
            if new<best.get(v,float('inf')):
                best[v]=new;heapq.heappush(q,(new,v,path+(v,)))
    return []

def next_hop_candidates(method,graph,node,sink,nodes,state,cfg,score=None):
    """Return local neighbor priority for opportunistic and learning policies."""
    choices=[]
    loc=nodes[node];dest=nodes[sink]
    distance_to_sink=lambda v: math.hypot(nodes[v][0]-dest[0],nodes[v][1]-dest[1])
    here=distance_to_sink(node)
    for v,e in graph.get(node,[]):
        if v!=sink and state['energy'][v]<state['min_energy']:continue
        if method=='fsecure' and v!=sink and state['trust'][v]<cfg['trust_threshold']:continue
        if distance_to_sink(v) >= here and v!=sink:continue
        p=float(e['link_success_probability_surrogate'])
        if method=='opportunistic_proxy':rank=p*(here-distance_to_sink(v))/max(1,here)
        elif method in ('fsecure','supervised_mlp_proxy'):
            if score is None: raise ValueError(f'{method} requires trained model')
            features=[state['energy'][v]/cfg['initial_energy_j'],state['trust'][v],
                      e['lqi_proxy_0_255']/255.,e['link_predicted_pdr'],
                      min(1.,e['nominal_delay_ms_surrogate']/state['delay_ref'])]
            rank=float(score(features))
        else: raise ValueError(method)
        choices.append((rank,v,e))
    return sorted(choices,key=lambda z:(-z[0],z[1]))
