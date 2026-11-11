import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.source import fit
p=argparse.ArgumentParser()
p.add_argument('--source-csv',nargs='+',required=True)
p.add_argument('--out',default='outputs/source.pt')
p.add_argument('--seed',type=int,default=20261111)
p.add_argument('--epochs',type=int,default=15)
p.add_argument('--limit',type=int)
a=p.parse_args();print(json.dumps(fit(a.source_csv,a.out,seed=a.seed,epochs=a.epochs,limit=a.limit),indent=2))
