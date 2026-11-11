"""New supervised-MLP proxy baseline, not a reproduction of the cited AI-CPS algorithm."""
import argparse,sys,json
from pathlib import Path
import pandas as pd,numpy as np,torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.models import SupervisedBaselineNet
from fsecure.tasks import FEATS
from fsecure.core import config,fingerprint
p=argparse.ArgumentParser();p.add_argument('--config',default='config/experiment.json')
p.add_argument('--records',default='outputs/reference/candidate_probe_records.csv')
p.add_argument('--out',default='outputs/ai_proxy.pt');p.add_argument('--epochs',type=int)
a=p.parse_args();c=config(a.config);torch.manual_seed(c['seed'])
df=pd.read_csv(a.records);df=df[df.split=='train'];x=torch.tensor(df[FEATS].to_numpy('float32'));y=torch.tensor(df.label.to_numpy('float32'))
m=SupervisedBaselineNet(c['baselines']['supervised_mlp_proxy']['hidden_neurons'])
opt=torch.optim.Adam(m.parameters(),lr=c['supervised_lr']);epochs=a.epochs or c['supervised_epochs']
for e in range(epochs):
    for idx in torch.randperm(len(x)).split(c['supervised_batch_size']):
        opt.zero_grad(); loss=(m(x[idx])-y[idx]).square().mean();loss.backward();opt.step()
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
torch.save({'model':m.state_dict(),'training_samples':len(df),'epochs':epochs,'lr':c['supervised_lr'],
            'records_sha256':fingerprint(a.records),'type':'new_supervised_proxy_NOT_original_AI_CPS'},out)
print('saved',out)
