# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/base_model.ipynb.

# %% auto 0
__all__ = ['RandomGaussianBlur', 'get_batch_augs', 'get_multi_aug_pipelines', 'get_barlow_twins_aug_pipelines',
           'BarlowTwinsModel', 'create_barlow_twins_model', 'BarlowTwins', 'lf_bt']

# %% ../nbs/base_model.ipynb 3
import self_supervised
import torch
from fastai.vision.all import *
from self_supervised.augmentations import *
from self_supervised.layers import *
import kornia.augmentation as korniatfm
import torchvision.transforms as tvtfm

# %% ../nbs/base_model.ipynb 7
#My edited version of RandTransform
class RandomGaussianBlur(RandTransform):
    "Randomly apply gaussian blur with probability `p` with a value of s"
    order = 11
    def __init__(self, p=1.0,prob=0.5, s=(8,32),s1=None, same_on_batch=False, **kwargs): 
        store_attr()
        super().__init__(p=p, **kwargs)

    def encodes(self, x:TensorImage):

        if isinstance(self.s, int):   s = (self.s,self.s)
        elif isinstance(self.s, tuple) or isinstance(self.s, list): s=self.s
     
        #Default for ImageNet from BYOL / BT papers
        if self.s1 is None:
            self.s1 = np.random.uniform(0.1,2)

        tfm = korniatfm.RandomGaussianBlur(kernel_size=s,sigma=(self.s1,self.s1),same_on_batch=self.same_on_batch,p=self.prob)
        return tfm(x)

#Delete later: leaving for backward compatibility for now
# class RandomGaussianBlur(RandTransform):
#     "Randomly apply gaussian blur with probability `p` with a value of s"
#     order = 11
#     def __init__(self, p=0.5, s=(8,32), same_on_batch=False, **kwargs): 
#         store_attr()
#         super().__init__(p=p, **kwargs)
        
#     def encodes(self, x:TensorImage):
#         if isinstance(self.s, tuple): s = np.random.randint(*self.s)
#         if isinstance(self.s, list):  s = np.random.randint(*self.s)
#         if isinstance(self.s, int):   s = self.s
#         s2 = int(s/4)*2+1
#         tfm = korniatfm.RandomGaussianBlur((s2,s2),(s,s),same_on_batch=self.same_on_batch,p=1.) #p=1. is a bug
#                                             #kernel #sigma
        
#         return tfm(x)
    
def get_batch_augs(size,
                    rotate=True,jitter=True,bw=True,blur=True,solar=True, #Whether to use  given aug or not
                    resize_scale=(0.08, 1.0),resize_ratio=(3/4, 4/3), rotate_deg=30,jitter_s=.6,blur_s=(4,32),s1=None,sol_t=0.05,sol_a=0.05, #hps of diff augs
                    flip_p=0.5, rotate_p=0.3, jitter_p=0.3, bw_p=0.3, blur_p=0.3,sol_p=0.1, #prob of performing aug
                    same_on_batch=False,stats=imagenet_stats,cuda=default_device().type == 'cuda',xtra_tfms=[]):
    "Input batch augmentations implemented in tv+kornia+fastai"
    tfms = []

    korniatfm.RandomHorizontalFlip.order = RandomResizedCrop.order-1
    
    tfms += [tvtfm.RandomResizedCrop((size, size), scale=resize_scale, ratio=resize_ratio)]
    
    tfms += [korniatfm.RandomHorizontalFlip(p=flip_p)]

    if rotate: tfms += [Rotate(max_deg=rotate_deg, p=rotate_p, batch=same_on_batch)]

                                             #brightness,contrast,saturation,hue
    if jitter: tfms += [korniatfm.ColorJitter(0.4*jitter_s, 0.4*jitter_s, 0.2*jitter_s, 0.1*jitter_s, p=jitter_p, same_on_batch=same_on_batch)]
    
    if bw:     tfms += [korniatfm.RandomGrayscale(p=bw_p, same_on_batch=same_on_batch)]
        

    if blur:   tfms += [RandomGaussianBlur(p=blur_p, s=blur_s,s1=s1, same_on_batch=same_on_batch)]

    korniatfm.RandomSolarize.order = RandomGaussianBlur.order + 1 #we want to apply solarization after RandomGaussianBlur
    
    if solar: tfms += [korniatfm.RandomSolarize(p=sol_p,thresholds=sol_t, additions=sol_a,same_on_batch=same_on_batch)]

    if stats is not None: tfms += [Normalize.from_stats(*stats, cuda=cuda)]

    tfms += xtra_tfms

    pipe = Pipeline(tfms, split_idx = 0)
    return pipe

#debugging:
# def get_batch_augs(size,
#                 rotate=True,jitter=True,bw=True,blur=True,solar=True, #Whether to use  given aug or not
#                 resize_scale=(0.08, 1.0),resize_ratio=(3/4, 4/3), rotate_deg=30,jitter_s=.6,blur_s=(4,32),s1=None,sol_t=0.05,sol_a=0.05, #hps of diff augs
#                 flip_p=0.5, rotate_p=0.3, jitter_p=0.3, bw_p=0.3, blur_p=0.3,sol_p=0.1, #prob of performing aug
#                 same_on_batch=False,stats=imagenet_stats,cuda=default_device().type == 'cuda',xtra_tfms=[]):


#     blur = RandomGaussianBlur(prob=blur_p, s=blur_s, same_on_batch=same_on_batch)
#     pipe = Pipeline([blur],split_idx = 0)
#     return pipe

@delegates(get_batch_augs)
def get_multi_aug_pipelines(size, **kwargs): return get_batch_augs(size, **kwargs)

@delegates(get_multi_aug_pipelines)
def get_barlow_twins_aug_pipelines(size,**kwargs): return get_multi_aug_pipelines(size=size,**kwargs)



# %% ../nbs/base_model.ipynb 9
#Base functions / classes we need to train a BT / RBT model.

#TODO: We can make these more abstract so can incrementally modify to build `bt/rbt` and also `new idea.` But for 
#sake of readability, might be easier to just modify the defintions elsewhere. Come back to this later...
class BarlowTwinsModel(Module):
    """An encoder followed by a projector
    """
    def __init__(self,encoder,projector):
        self.encoder = encoder
        self.projector = projector
        
    def forward(self,x): 
        
        return self.projector(self.encoder(x))

def create_barlow_twins_model(encoder, hidden_size=256, projection_size=128, bn=True, nlayers=3):
    "Create Barlow Twins model"
    n_in  = in_channels(encoder)
    with torch.no_grad(): representation = encoder(torch.randn((2,n_in,128,128)))
    projector = create_mlp_module(representation.size(1), hidden_size, projection_size, bn=bn, nlayers=nlayers) 
    apply_init(projector)
    return BarlowTwinsModel(encoder, projector)

class BarlowTwins(Callback):
    order,run_valid = 9,True
    def __init__(self, aug_pipelines,n_in, lmb=5e-3, print_augs=False):
        assert_aug_pipelines(aug_pipelines)
        self.aug1, self.aug2 = aug_pipelines
        if print_augs: print(self.aug1), print(self.aug2)
        store_attr('lmb')
        
        self.n_in=n_in
        
        self.index=-1 #Gets updated after each batch
        self.seed = np.random.randint(0,10000) #gets updated after each batch

        
    def before_fit(self): 
        self.learn.loss_func = self.lf
        nf = self.learn.model.projector[-1].out_features
        self.I = torch.eye(nf).to(self.dls.device)

    def update_seed(self):
        
        indexmod=2
        if self.index%indexmod == 0: 
            self.seed = np.random.randint(0,10000)

    def before_epoch(self):
        self.index=-1
            
    def before_batch(self):
        
        #TODO: Make this nicer (possibly can load in data as TensorImage(BW) or something?)
        #This is a bit of a hack. Can make this more elegant later. But in new version of FastAI
        #seems we need to compute TensorImage(BW) here, and depends on whether color or not, i.e. n_in.
        if self.n_in == 1:
            xi,xj = self.aug1(TensorImageBW(self.x)), self.aug2(TensorImageBW(self.x))
                                    
        elif self.n_in == 3:
            xi,xj = self.aug1(TensorImage(self.x)), self.aug2(TensorImage(self.x))

        self.learn.xb = (torch.cat([xi, xj]),)

        self.index=self.index+1
        self.update_seed()
        
    @torch.no_grad()
    def show(self, n=1): 
        bs = self.learn.x.size(0)//2
        x1,x2  = self.learn.x[:bs], self.learn.x[bs:]
        idxs = np.random.choice(range(bs),n,False)
        x1 = self.aug1.decode(x1[idxs].to('cpu').clone()).clamp(0,1)
        x2 = self.aug2.decode(x2[idxs].to('cpu').clone()).clamp(0,1)
        images = []
        for i in range(n): images += [x1[i],x2[i]]
        return show_batch(x1[0], None, images, max_n=len(images), nrows=n)

# %% ../nbs/base_model.ipynb 11
def lf_bt(pred,I,lmb):
    bs,nf = pred.size(0)//2,pred.size(1)
    
    z1, z2 = pred[:bs],pred[bs:] #so z1 is bs*projection_size, likewise for z2

    z1norm = (z1 - z1.mean(0)) / z1.std(0, unbiased=False)
    z2norm = (z2 - z2.mean(0)) / z2.std(0, unbiased=False)

    C = (z1norm.T @ z2norm) / bs 
    cdiff = (C - I)**2
    loss = (cdiff*I + cdiff*(1-I)*lmb).sum() 
    return loss

# %% ../nbs/base_model.ipynb 12
@patch
def lf(self:BarlowTwins, pred,*yb):
    return lf_bt(pred, self.I,self.lmb)