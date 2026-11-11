"""Actual KDD Cup 99 / NSL-KDD parser, training-only encoders and source training.

User supplies original files. No dataset included in this supplement.
Outputs contain preprocessor metadata and transferred layer checksum.
"""
from __future__ import annotations
import json, numpy as np, pandas as pd, torch
from pathlib import Path
from torch.utils.data import TensorDataset,DataLoader
from .models import SourceNet
from .core import mixed_seed

COLS = ['duration','protocol_type','service','flag','src_bytes','dst_bytes','land','wrong_fragment',
'urgent','hot','num_failed_logins','logged_in','num_compromised','root_shell','su_attempted',
'num_root','num_file_creations','num_shells','num_access_files','num_outbound_cmds','is_host_login',
'is_guest_login','count','srv_count','serror_rate','srv_serror_rate','rerror_rate','srv_rerror_rate',
'same_srv_rate','diff_srv_rate','srv_diff_host_rate','dst_host_count','dst_host_srv_count',
'dst_host_same_srv_rate','dst_host_diff_srv_rate','dst_host_same_src_port_rate',
'dst_host_srv_diff_host_rate','dst_host_serror_rate','dst_host_srv_serror_rate',
'dst_host_rerror_rate','dst_host_srv_rerror_rate']
CATS=['protocol_type','service','flag']

def read_connections(paths,limit=None):
    frames=[]
    for path in paths:
        raw=pd.read_csv(path,header=None,nrows=limit)
        if raw.shape[1] not in (42,43):
            raise ValueError(f'{path}: expected 42 KDD or 43 NSL-KDD columns, found {raw.shape[1]}')
        raw=raw.iloc[:,:42].copy();raw.columns=COLS+['label']
        raw['dataset_file']=str(Path(path).name)
        raw['label']=(raw.label.astype(str).str.rstrip('.').str.lower()!='normal').astype('int64')
        frames.append(raw)
    if not frames: raise ValueError('Supply --source-csv paths to real downloaded KDD/NSL-KDD files')
    return pd.concat(frames,ignore_index=True).drop_duplicates(subset=COLS+['label']).reset_index(drop=True)

def preprocess_train_val(df,seed=1,frac=.2):
    rng=np.random.default_rng(seed);indices=rng.permutation(len(df)); split=max(1,round(len(df)*(1-frac)))
    train=df.iloc[indices[:split]].copy();val=df.iloc[indices[split:]].copy()
    if len(val)==0: raise ValueError('Need at least two source records')
    numeric=[c for c in COLS if c not in CATS]
    means={c:float(pd.to_numeric(train[c],errors='coerce').mean()) for c in numeric}
    scales={c:float(max(pd.to_numeric(train[c],errors='coerce').std(ddof=0),1e-8)) for c in numeric}
    vocab={c:sorted(str(x) for x in train[c].astype(str).unique()) for c in CATS}
    def transform(frame):
        xs=[]
        for c in numeric:
            arr=pd.to_numeric(frame[c],errors='coerce').fillna(means[c]).to_numpy(dtype='float32')
            xs.append(((arr-means[c])/scales[c])[:,None])
        for c in CATS:
            vals=frame[c].astype(str).to_numpy();v=vocab[c]
            xs.append(np.stack([vals==term for term in v],axis=-1).astype('float32'))
        return np.concatenate(xs,axis=1)
    artifact={'numeric_features':numeric,'means':means,'scales':scales,'vocabulary':vocab,
              'source_files':sorted(df.dataset_file.unique().tolist()),'source_train_rows':len(train),
              'source_validation_rows':len(val),'split_seed':seed,
              'source_split_warning':'Exact feature/label duplicates removed before random record split. Cross-source near-duplicates and test-set provenance require separate auditing before publication.'}
    return (transform(train),train.label.to_numpy(dtype='float32'),
            transform(val),val.label.to_numpy(dtype='float32'),artifact)

def fit(paths,out,seed=1,epochs=15,batch_size=128,lr=1e-3,limit=None):
    torch.manual_seed(seed)
    df=read_connections(paths,limit)
    x,y,xv,yv,p=preprocess_train_val(df,seed)
    model=SourceNet(x.shape[1]);opt=torch.optim.Adam(model.parameters(),lr=lr)
    data=TensorDataset(torch.from_numpy(x),torch.from_numpy(y))
    loader=DataLoader(data,batch_size=batch_size,shuffle=True,generator=torch.Generator().manual_seed(seed))
    for epoch in range(epochs):
        model.train()
        for xb,yb in loader:
            opt.zero_grad();loss=torch.nn.functional.binary_cross_entropy_with_logits(model(xb),yb)
            loss.backward();opt.step()
    model.eval()
    with torch.no_grad():
        vloss=torch.nn.functional.binary_cross_entropy_with_logits(model(torch.from_numpy(xv)),torch.from_numpy(yv)).item()
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    torch.save({'model':model.state_dict(),'source_input_dim':x.shape[1],
                'source_val_bce':vloss,'training_seed':seed,'epochs':epochs,'batch_size':batch_size,
                'lr':lr,'provenance':'newly_trained_source_classifier'},out)
    (out.parent/'source_preprocessing.json').write_text(json.dumps(p,indent=2))
    return {'checkpoint':str(out),'source_input_dim':x.shape[1],'source_validation_bce':vloss,'row_count':len(df)}
