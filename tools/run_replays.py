"""Replay the three proxy baselines and FSecure on matched scenario seeds."""
import argparse,sys,json
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.evaluate import replay,METHODS,loaded_models
from fsecure.core import config,fingerprint
p=argparse.ArgumentParser();p.add_argument('--config',default='config/experiment.json')
p.add_argument('--records',default='outputs/reference/candidate_probe_records.csv')
p.add_argument('--scenarios',default='outputs/reference/scenarios')
p.add_argument('--meta',default='outputs/fsecure_meta.pt')
p.add_argument('--baseline',default='outputs/ai_proxy.pt')
p.add_argument('--out',default='outputs/replay_per_run.csv')
p.add_argument('--rounds',type=int);p.add_argument('--smoke',action='store_true')
a=p.parse_args();cfg=config(a.config);root=Path(a.scenarios)
ref=json.loads((Path(a.records).parent/'task_preprocessing.json').read_text())
folders=sorted(p for p in root.iterdir() if p.is_dir())
eval_seeds=([1,2] if a.smoke else cfg['evaluation_seeds'])
folders=[p for p in folders if any(f'_seed{k}_' in p.name for k in eval_seeds)]
records=[]
for f in folders:
    n=int(f.name.split('_')[0][1:]);seed=int(f.name.split('_')[1][4:]); attack='_'.join(f.name.split('_')[2:]);
    scores=loaded_models(a.meta,a.baseline,a.records,f.name,cfg)
    for method in METHODS:
        z=replay(cfg,f,method,scores,seed,rounds=(8 if a.smoke else (a.rounds or cfg['rounds'])),
                 packets_per_round=cfg['packets_per_round'],delay_ref=ref['delay_reference_ms_train_only'])
        records.append(z)
        print(f'{f.name} {method} PDR={z["pdr_percent"]:.1f}% reach={z["geometrically_sink_reachable_nodes"]}/{z["node_count"]}')
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(records).to_csv(out,index=False)
(out.parent/'replay_provenance.json').write_text(json.dumps({'backend':'python_packet_replay_surrogate_NOT_real_ns3_MAC',
          'scenario_count':len(folders),'method_names':list(METHODS), 'meta_sha256':fingerprint(a.meta),
          'baseline_sha256':fingerprint(a.baseline),'config_sha256':fingerprint(a.config),
          'no_original_outcomes_recovered':True},indent=2))
print('saved',out)
