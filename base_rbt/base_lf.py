# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/base_lf.ipynb.

# %% auto 0
__all__ = ['seed_everything', 'random_sinusoid', 'C_z1z2', 'Cdiff_Rand', 'Max_Corr', 'Cdiff_Sup']

# %% ../nbs/base_lf.ipynb 3
from .base_model import *
from fastai.vision.all import *
import random
import os
import numpy as np

# %% ../nbs/base_lf.ipynb 5
def seed_everything(seed=42):
    """"
    Seed everything.
    """   
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True

# %% ../nbs/base_lf.ipynb 6
def random_sinusoid(x,std=0.1,seed=0,device='cuda'):
    
    #seed_everything(seed=seed)
    
    ps = x.shape[1]
    
    X = torch.randn(6,ps).to(device) #use this to get t,s,u,v,a,b i.e. random components of sinusoid
    
    t,s = std*X[0:2,:]
    u,v = X[2:4,:]
    a,b = 0.2*X[4:6,:]

    return a*torch.sin(t*x[:,]*math.pi+u) + b*torch.cos(s*x[:,]*math.pi+v)

# %% ../nbs/base_lf.ipynb 10
def C_z1z2(z1norm,z1norm_2,z2norm,z2norm_2,indep=True):
    
    bs = z1norm.shape[0]
    if indep == False:
        C1 =  (z1norm.T @ z2norm_2) / bs
        C2 = (z1norm_2.T @ z2norm) / bs
        cdiff = (0.5*C1.pow(2) + 0.5*C2.pow(2))
        
    elif indep == True:
        cdiff =  (z1norm_2.T @ z2norm_2) / bs
        
    return cdiff

# %% ../nbs/base_lf.ipynb 13
class Cdiff_Rand:
    
    def __init__(self,seed,std=0.1,K=2,indep=False):
        self.seed=seed
        self.std=std
        self.K=K
        self.indep=indep

    def __call__(self,z1norm,z2norm):
        
        K=self.K
        cdiff_rand=0
        for i in range(K):
            
            z1norm_2,z2norm_2 = random_sinusoid(x=z1norm,std=self.std,seed=self.seed+i), random_sinusoid(x=z2norm,std=self.std,seed=2*self.seed+i)
            cdiff_rand = C_z1z2(z1norm=z1norm,z1norm_2=z1norm_2,z2norm=z2norm,z2norm_2=z2norm_2,indep=self.indep)

        cdiff_rand=(1/K)*cdiff_rand
    
        return cdiff_rand

# %% ../nbs/base_lf.ipynb 14
class Max_Corr(nn.Module):
    def __init__(self,
                 qs #qs will tend to be =ps i.e. projection dimension, although this is not required. 
                ):
        super().__init__()
        self.m1 = nn.Sequential(nn.Linear(qs,qs),nn.Sigmoid(),nn.Linear(qs,qs)) #feedforward net one hidden layer
        self.m2 = nn.Sequential(nn.Linear(qs,qs),nn.ReLU(),nn.Linear(qs,qs)) #feedforward net one hidden layer
    
    def forward(self,x,y):
        return self.m1(x),self.m2(y)

# %% ../nbs/base_lf.ipynb 17
class Cdiff_Sup:
    
    def __init__(self,I,qs,inner_steps,indep=True):
        
        self.I=I
        self.qs=qs
        self.inner_steps=inner_steps
        self.indep=indep
        self.max_corr = Max_Corr(qs=qs)
        if default_device().type == 'cuda':
            self.max_corr.cuda()
        
    def inner_step(self,z1norm,z2norm):
    
        max_corr=self.max_corr
        inner_steps=self.inner_steps
        z1norm=z1norm.detach()
        z2norm=z2norm.detach()
        max_corr = Max_Corr(qs=self.qs)
        optimizer = torch.optim.Adam(list(max_corr.parameters()),lr=0.001)
        
        for i in range(inner_steps):
            z1norm_2,z2norm_2=max_corr(z1norm,z2norm)        
            cdiff_2 = C_z1z2(z1norm=z1norm,z1norm_2=z1norm_2,z2norm=z2norm,z2norm_2=z2norm_2,indep=self.indep)
            inner_loss=-1*(cdiff_2*(1-self.I)).mean()
            optimizer.zero_grad()
            inner_loss.backward()
            optimizer.step()
        
        for p in max_corr.parameters():
            p.requires_grad=False
            
        return max_corr
    
    def __call__(self,z1norm,z2norm):
        
            max_corr =  self.inner_step(z1norm,z2norm)
            z1norm_2,z2norm_2 = max_corr(z1norm,z2norm)
            cdiff_sup = C_z1z2(z1norm=z1norm,z1norm_2=z1norm_2,z2norm=z2norm,z2norm_2=z2norm_2,indep=self.indep)
    
            return cdiff_sup
