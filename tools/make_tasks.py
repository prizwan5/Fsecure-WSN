import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fsecure.core import config
from fsecure.tasks import generate
p=argparse.ArgumentParser();p.add_argument('--config',default='config/experiment.json')
p.add_argument('--out',default='outputs/reference');p.add_argument('--smoke',action='store_true')
p.add_argument('--ns3-scenarios',help='Use NS-3-exported node/edge folders instead of Python topology generation')
a=p.parse_args(); print(json.dumps(generate(config(a.config),a.out,smoke=a.smoke,ns3_scenarios=a.ns3_scenarios),indent=2))
