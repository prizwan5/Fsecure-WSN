"""Full second-order MAML for 5-64-32-1 network; all fast weights adapted."""
import argparse,sys,json,random
from pathlib import Path
import numpy as np,torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.models import RoutingNet,transfer_second_layer,maml_step,adapt
from fsecure.tasks import tasks_from_csv
from fsecure.core import config,fingerprint
p=argparse.ArgumentParser();p.add_argument('--config',default='config/experiment.json')
p.add_argument('--records',default='outputs/reference/candidate_probe_records.csv')
p.add_argument('--out',default='outputs/fsecure_meta.pt');p.add_argument('--source-checkpoint')
p.add_argument('--episodes',type=int);p.add_argument('--smoke',action='store_true')
a=p.parse_args();cfg=config(a.config)
seed=cfg['seed'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
train=tasks_from_csv(a.records,'train');val=tasks_from_csv(a.records,'val');
if not train:raise SystemExit('No training tasks')
model=RoutingNet(); transferred=[]
if a.source_checkpoint:transferred=list(transfer_second_layer(a.source_checkpoint,model))
optimizer=torch.optim.Adam(model.parameters(),lr=cfg['outer_lr'])
episodes=(3 if a.smoke else (a.episodes or cfg['meta_episodes']))
rng=np.random.default_rng(seed)

def batch_from(group,size):
    choices=rng.choice(list(group),size=size,replace=len(group)<size)
    result=[]
    for key in choices:
        x,y=group[key]
        idx=rng.choice(len(x),size=cfg['task_support']+cfg['task_query'],replace=False)
        s=cfg['task_support']
        result.append(tuple(torch.from_numpy(a) for a in (x[idx[:s]],y[idx[:s]],x[idx[s:]],y[idx[s:]])))
    return result
losses=[]
for ep in range(episodes):
    batch=batch_from(train,cfg['tasks_per_meta_batch'])
    loss=maml_step(model,batch,optimizer,cfg['inner_steps'],cfg['inner_lr'],cfg['maml_second_order'])
    losses.append(loss)
    if ep<3 or (ep+1)%100==0: print(f'episode={ep+1} query_mse={loss:.6f}')
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
torch.save({'model':model.state_dict(),'config':cfg,'transferred_parameter_names':transferred,
           'source_checkpoint_sha256':fingerprint(a.source_checkpoint) if a.source_checkpoint else None,
           'records_sha256':fingerprint(a.records),'meta_losses':losses,
           'type':'NEW_REFERENCE_RECONSTRUCTION_NOT_HISTORICAL'},out)
(out.parent/'meta_train_log.json').write_text(json.dumps({'episodes':episodes,'final_meta_mse':losses[-1],
                        'second_order':cfg['maml_second_order'],'adapted_parameters':'all',
                        'inner_optimizer':'functional_SGD','outer_optimizer':'Adam',
                        'source_checkpoint':a.source_checkpoint,'transferred_parameter_names':transferred},indent=2))
print('saved',out)
