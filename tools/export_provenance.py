"""Write fully explicit NEW configuration log/checkpoint file hashes."""
import argparse,sys,json,hashlib,csv
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--config',default='config/experiment.json')
p.add_argument('--outputs',default='outputs');a=p.parse_args()
cfg=json.loads(Path(a.config).read_text());out=Path(a.outputs);out.mkdir(parents=True,exist_ok=True)
rows=[]
for file in out.rglob('*.pt'):
    rows.append({'path':str(file),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                 'note':'new smoke or reference checkpoint, NEVER the original authors checkpoint'})
with (out/'checkpoint_manifest.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['path','sha256','note']);w.writeheader();w.writerows(rows)
(out/'baseline_parameter_log.json').write_text(json.dumps({'common_new_config':{k:cfg[k] for k in
    ('area_m','sink_x_m','sink_y_m','radio_range_m','packet_bytes_application','frame_payload_bytes_surrogate',
     'attack_fraction','attack_activation_round','rounds','training_seeds','validation_seeds','evaluation_seeds')},
     'reference_comparator_proxies':cfg['baselines'],
     'WARNING':'Not executed historical EESM, Opportunistic, or AI-CPS settings'},indent=2))
print('wrote',out/'baseline_parameter_log.json',out/'checkpoint_manifest.csv')
