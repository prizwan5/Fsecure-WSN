"""Generate KDD-shaped SYNTHETIC rows for pipeline testing only.
Never cite or report these data or their pretrained checkpoint as KDD/NSL-KDD experiments.
"""
import argparse,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.source import COLS
p=argparse.ArgumentParser();p.add_argument('--out',default='outputs/SMOKE_SYNTHETIC_SOURCE_NOT_KDD.csv');p.add_argument('--rows',type=int,default=300)
a=p.parse_args();rng=np.random.default_rng(20261111);data=[]
for i in range(a.rows):
    label='normal.' if i%2==0 else 'neptune.'
    row=[]
    for c in COLS:
        if c=='protocol_type':val='tcp' if i%2==0 else 'udp'
        elif c=='service':val='http' if i%3 else 'ftp'
        elif c=='flag':val='SF' if i%2==0 else 'REJ'
        else:val=int(rng.integers(1,100)) if i%3 else float(rng.uniform(0,1))
        row.append(val)
    row.append(label);data.append(row)
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
pd.DataFrame(data).to_csv(out,index=False,header=False)
print('SYNTHETIC SMOKE ONLY, NOT A SCIENTIFIC DATASET:',out)
