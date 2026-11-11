"""Run with python -m pytest tests -q. No paper results are fabricated."""
import json,sys
from pathlib import Path
import numpy as np,torch,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fsecure.core import config,make_nodes,make_edges,save_scenario,reachability,mixed_seed
from fsecure.tasks import generate,WEIGHTS,FEATS,tasks_from_csv
from fsecure.models import SourceNet,RoutingNet,transfer_second_layer,maml_step

def test_weights_and_declared_configuration():
    c=config(ROOT/'config/experiment.json')
    assert sum(WEIGHTS.values())==1.
    assert c['node_counts']==[100,150,200]
    assert set(c['training_seeds']).isdisjoint(c['evaluation_seeds'])
    assert c['packet_bytes_application']>127
    assert c['frame_payload_bytes_surrogate']+15<=127

def test_geometry_reproducibility_and_sink_reachability():
    c=config(ROOT/'config/experiment.json')
    a=make_nodes(c,100,1,'blackhole');b=make_nodes(c,100,1,'blackhole')
    pd.testing.assert_frame_equal(a,b)
    e=make_edges(c,a)
    reachable,n=reachability(a,e)
    assert n==100 and 0<=reachable<=100

def test_transfer_exact_tensors(tmp_path):
    torch.manual_seed(1);src=SourceNet(8);target=RoutingNet()
    before=target.fc1.weight.detach().clone()
    ckpt=tmp_path/'source.pt';torch.save({'model':src.state_dict()},ckpt)
    names=transfer_second_layer(ckpt,target)
    assert names==('fc2.weight','fc2.bias')
    assert torch.equal(src.fc2.weight,target.fc2.weight)
    assert torch.equal(src.fc2.bias,target.fc2.bias)
    assert torch.equal(before,target.fc1.weight)

def test_task_split_and_maml(tmp_path):
    c=config(ROOT/'config/experiment.json');m=generate(c,tmp_path,smoke=True)
    d=pd.read_csv(tmp_path/'candidate_probe_records.csv')
    assert set(d[d.split=='train'].task_id).isdisjoint(d[d.split=='test'].task_id)
    assert d.label.between(0,1).all()
    assert d[FEATS].notna().all().all()
    train=tasks_from_csv(tmp_path/'candidate_probe_records.csv','train')
    x,y=next(iter(train.values()));sx=torch.tensor(x[:8]);sy=torch.tensor(y[:8]);qx=torch.tensor(x[8:24]);qy=torch.tensor(y[8:24])
    model=RoutingNet();opt=torch.optim.Adam(model.parameters(),lr=.001)
    loss=maml_step(model,[(sx,sy,qx,qy)],opt,5,.01,True)
    assert np.isfinite(loss)
