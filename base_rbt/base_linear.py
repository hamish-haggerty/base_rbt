# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/base_linear.ipynb.

# %% auto 0
__all__ = ['get_linear_batch_augs', 'LinearModel', 'LinearBt', 'show_linear_batch', 'Main_Linear_Eval']

# %% ../nbs/base_linear.ipynb 3
import self_supervised
import torch
from fastai.vision.all import *
from self_supervised.augmentations import *
from self_supervised.layers import *
import kornia.augmentation as korniatfm
import torchvision.transforms as tvtfm

from .helper import *

# %% ../nbs/base_linear.ipynb 5
#Batch level augmentations for linear classifier. At present time, just RandomResizedCrop and Normalization.
def get_linear_batch_augs(size,resize=True,
                    resize_scale=(0.08, 1.0),resize_ratio=(3/4, 4/3),
                    stats=None,cuda=default_device().type == 'cuda',xtra_tfms=[]):
    
    "Input batch augmentations implemented in tv+kornia+fastai"
    tfms = []
    if resize:tfms += [tvtfm.RandomResizedCrop((size, size), scale=resize_scale, ratio=resize_ratio)]
    if stats is not None: tfms += [Normalize.from_stats(*stats, cuda=cuda)]
    tfms += xtra_tfms
    pipe = Pipeline(tfms, split_idx = 0)
    return pipe

# %% ../nbs/base_linear.ipynb 7
#Linear model 
class LinearModel(Module):
    """Linear model
    """
    def __init__(self,encoder,
                 indim=1024,#dimension of encoder output
                 outdim=10, #number of classes
                ):
        self.encoder=encoder
        self.L = nn.Linear(indim,outdim) 
        
    def forward(self,x):return self.L(self.encoder(x))

# %% ../nbs/base_linear.ipynb 9
class LinearBt(Callback):
    order,run_valid = 9,True
    def __init__(self,aug_pipelines,n_in, show_batch=False, print_augs=False):
        assert_aug_pipelines(aug_pipelines)
        self.aug1= aug_pipelines[0]
        self.aug2=Pipeline( split_idx = 0) #empty pipeline
        if print_augs: print(self.aug1), print(self.aug2)
        self.n_in=n_in
        self._show_batch=show_batch
        self.criterion = nn.CrossEntropyLoss()
        
    def before_fit(self): 
        self.learn.loss_func = self.lf
            
    def before_batch(self):

        if self.n_in == 1:
            xi,xj = self.aug1(TensorImageBW(self.x)), self.aug2(TensorImageBW(self.x))                            
        elif self.n_in == 3:
            xi,xj = self.aug1(TensorImage(self.x)), self.aug2(TensorImage(self.x))
        self.learn.xb = (xi,)

        if self._show_batch:
            self.learn.aug_x = torch.cat([xi, xj])

    def lf(self, pred, *yb):        
        loss=self.criterion(pred,self.y)
        return loss

    @torch.no_grad()
    def show(self, n=1):
        if self._show_batch==False:
            print('Need to set show_batch=True')
            return
        bs = self.learn.aug_x.size(0)//2
        x1,x2  = self.learn.aug_x[:bs], self.learn.aug_x[bs:]
        idxs = np.random.choice(range(bs),n,False)
        x1 = self.aug1.decode(x1[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
        x2 = self.aug2.decode(x2[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
        images = []
        for i in range(n): images += [x1[i],x2[i]]
        return show_batch(x1[0], None, images, max_n=len(images), nrows=n)

# %% ../nbs/base_linear.ipynb 17
def show_linear_batch(dls,n_in,aug,n=2,print_augs=True):
    "Given a linear learner, show a batch"
    bt = LinearBt(aug,show_batch=True,n_in=n_in,print_augs=print_augs)
    learn = Learner(dls,model=None, cbs=[bt])
    b = dls.one_batch()
    learn._split(b)
    learn('before_batch')
    axes = learn.linear_bt.show(n=n)
    

# %% ../nbs/base_linear.ipynb 23
#Given validation set, test set, encoder, etc return accuracy via __call__
class Main_Linear_Eval:
    
    def __init__(self,size,n_in,indim,numfit, #size e.g. 32, n_in e.g. 1 or 3, indim  is encoder output dim, numfit number of epochs training 
                 dls_val,dls_test, #dls_val for training linear, dls_test for evaluation
                 stats, #e.g. cifar_stats
                 aug_pipelines_val, #generally simple (crop and normalizatiom)
                 encoder
                ):
    
        store_attr()
        self.encoder=encoder
        if self.encoder is not None:
            self.model = LinearModel(encoder=self.encoder,indim=indim)
     
    #Use this guy to put the model into evaluation mode
    def Eval_Mode(self,_model):

        aug_pipelines = get_linear_batch_augs(size=self.size,resize=False,stats=self.stats)

        @torch.no_grad()
        def call(x):
            return _model(aug_pipelines(x))

        return call
        
    #Evaluate linear model on dls_test
    def eval_linear(self):

        eval_model = self.Eval_Mode(self.model)
        N=len(self.dls_test.train)*self.dls_test.bs
        test_eq(N,len(self.dls_test.train_ds)) #check that batch size divides length of test set
        
        
        num_correct=0
        for x,y in self.dls_test.train:

            ypred=eval_model(x) 
            correct = (torch.argmax(ypred,dim=1) == y).type(torch.FloatTensor)
            num_correct += correct.sum()

        accuracy = num_correct/N
        return accuracy.item()
        
        
    def __call__(self):
        
        #train linear classifier on dls_eval. Requires inputs: encoder, aug_pipeline, dls, 
        bt = LinearBt(self.aug_pipelines_val,show_batch=True,n_in=self.n_in,print_augs=False)
        learn = Learner(self.dls_val,self.model, cbs=[bt])
        learn.fit(self.numfit)
        
        #eval linear classifier
        acc = self.eval_linear()
        
        return acc
    
