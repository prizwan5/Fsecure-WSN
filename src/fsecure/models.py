"""Source classifier, target scorer, second-layer transfer and full MAML."""
from __future__ import annotations
import copy, torch
from torch import nn
from torch.func import functional_call

class SourceNet(nn.Module):
    def __init__(self,p):
        super().__init__()
        self.fc1=nn.Linear(p,64); self.fc2=nn.Linear(64,32); self.fc3=nn.Linear(32,1)
    def forward(self,x):
        return self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(x))))).squeeze(-1)

class RoutingNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1=nn.Linear(5,64); self.fc2=nn.Linear(64,32); self.fc3=nn.Linear(32,1)
    def forward(self,x):
        return torch.sigmoid(self.fc3(torch.relu(self.fc2(torch.relu(self.fc1(x)))))).squeeze(-1)

class SupervisedBaselineNet(nn.Module):
    def __init__(self,hidden=32):
        super().__init__()
        self.fc1=nn.Linear(5,hidden); self.fc2=nn.Linear(hidden,1)
    def forward(self,x):
        return torch.sigmoid(self.fc2(torch.relu(self.fc1(x)))).squeeze(-1)

def transfer_second_layer(source_checkpoint, target):
    """Exact, auditable tensors; source fc1/input and fc3/head never copied."""
    ckpt=torch.load(source_checkpoint,map_location='cpu',weights_only=True)
    sd=ckpt['model']
    assert tuple(sd['fc2.weight'].shape)==(32,64)
    assert tuple(sd['fc2.bias'].shape)==(32,)
    with torch.no_grad():
        target.fc2.weight.copy_(sd['fc2.weight'])
        target.fc2.bias.copy_(sd['fc2.bias'])
    return ('fc2.weight','fc2.bias')

def masked_mse(pred,y,mask=None):
    if mask is None: return (pred-y).square().mean()
    if mask.sum()<=0: raise ValueError('No supervised examples in batch')
    return ((pred-y).square()*mask).sum()/mask.sum()

def adapt(model, support_x, support_y, steps=5, lr=0.01, second_order=True):
    """Functional SGD, resets fast parameters per task and updates all layers."""
    params={name: p for name,p in model.named_parameters()}
    for _ in range(steps):
        pred=functional_call(model,params,(support_x,))
        loss=masked_mse(pred,support_y)
        gradients=torch.autograd.grad(loss,tuple(params.values()),create_graph=second_order)
        params={key: value-lr*grad for (key,value),grad in zip(params.items(),gradients)}
    return params

def maml_step(model, tasks, optimizer, steps, inner_lr, second_order=True):
    optimizer.zero_grad()
    losses=[]
    for sx,sy,qx,qy in tasks:
        fast=adapt(model,sx,sy,steps,inner_lr,second_order)
        losses.append(masked_mse(functional_call(model,fast,(qx,)),qy))
    meta=torch.stack(losses).mean()
    meta.backward(); optimizer.step()
    return meta.item()
