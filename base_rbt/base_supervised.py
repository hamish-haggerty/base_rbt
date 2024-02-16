# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/base_supervised.ipynb.

# %% auto 0
__all__ = ['supervised_aug_func_dict', 'get_linear_batch_augs', 'LM', 'LinearBt', 'show_linear_batch',
           'get_supervised_aug_pipelines', 'get_supervised_cifar10_augmentations', 'predict_model',
           'predict_whole_model', 'encoder_head_splitter', 'SaveModelCheckpoint', 'SupervisedLearning',
           'train_supervised']

# %% ../nbs/base_supervised.ipynb 3
import self_supervised
import torch
from fastai.vision.all import *
from self_supervised.augmentations import *
from self_supervised.layers import *
import kornia.augmentation as korniatfm
import torchvision.transforms as tvtfm
from .utils import *

# %% ../nbs/base_supervised.ipynb 5
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

# %% ../nbs/base_supervised.ipynb 7
class LM(nn.Module):
    "Basic linear model"
    def __init__(self,encoder,numout,encoder_dimension=2048):
        super().__init__()
        self.encoder=encoder
        self.head=nn.Linear(encoder_dimension,numout)

    def forward(self,x):
        return self.head(self.encoder(x))

# %% ../nbs/base_supervised.ipynb 10
# class LinearBt(Callback):
#     order,run_valid = 9,True
#     def __init__(self,aug_pipelines,n_in, show_batch=False, print_augs=False,data=None):
#         assert_aug_pipelines(aug_pipelines)
#         self.aug1= aug_pipelines[0]
#         self.aug2=Pipeline( split_idx = 0) #empty pipeline
#         if print_augs: print(self.aug1), print(self.aug2)
#         self.n_in=n_in
#         self._show_batch=show_batch
#         self.criterion = nn.CrossEntropyLoss()
        
#         self.data=data #if data is just e.g. 20 samples then don't bother re-loading each time
        
#     def before_fit(self): 
#         self.learn.loss_func = self.lf
            
#     def before_batch(self):

#         if self.n_in == 1:
#             xi,xj = self.aug1(TensorImageBW(self.x)), self.aug2(TensorImageBW(self.x))                            
#         elif self.n_in == 3:
#             xi,xj = self.aug1(TensorImage(self.x)), self.aug2(TensorImage(self.x))
#         self.learn.xb = (xi,)

#         if self._show_batch:
#             self.learn.aug_x = torch.cat([xi, xj])

#     def lf(self, pred, *yb):        
#         loss=self.criterion(pred,self.y)
#         return loss

#     @torch.no_grad()
#     def show(self, n=1):
#         if self._show_batch==False:
#             print('Need to set show_batch=True')
#             return
#         bs = self.learn.aug_x.size(0)//2
#         x1,x2  = self.learn.aug_x[:bs], self.learn.aug_x[bs:]
#         idxs = np.random.choice(range(bs),n,False)
#         x1 = self.aug1.decode(x1[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
#         x2 = self.aug2.decode(x2[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
#         images = []
#         for i in range(n): images += [x1[i],x2[i]]
#         return show_batch(x1[0], None, images, max_n=len(images), nrows=n)


#A more comprehensive callback, copy pasted from cancer-proj
class LinearBt(Callback):
    order,run_valid = 9,True
    def __init__(self,aug_pipelines,n_in, show_batch=False, print_augs=False,data=None,
                 tune_model_path=None,tune_save_after=None):
        self.aug1= aug_pipelines[0]
        self.aug2=Pipeline( split_idx = 0) #empty pipeline
        if print_augs: print(self.aug1), print(self.aug2)
        self.n_in=n_in
        self._show_batch=show_batch
        self.criterion = nn.CrossEntropyLoss()
        self.data=data #if data is just e.g. 20 samples then don't bother re-loading each time
        self.tune_model_path=tune_model_path
        self.tune_save_after = tune_save_after


    def after_create(self):
        self.learn.tune_model_path_dict = {}
        self.learn.tune_model_path=self.tune_model_path


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

# %% ../nbs/base_supervised.ipynb 15
def show_linear_batch(dls,n_in,aug,n=2,print_augs=True):
    "Given a linear learner, show a batch"
    bt = LinearBt(aug,show_batch=True,n_in=n_in,print_augs=print_augs)
    learn = Learner(dls,model=None, cbs=[bt])
    b = dls.one_batch()
    learn._split(b)
    learn('before_batch')
    axes = learn.linear_bt.show(n=n)
    

# %% ../nbs/base_supervised.ipynb 17
def get_supervised_aug_pipelines(augs,size):

    return supervised_aug_func_dict[augs](size)

def get_supervised_cifar10_augmentations(size):

    return get_linear_batch_augs(size=size,resize=True,resize_scale=(0.3,1.0),stats=cifar_stats)

supervised_aug_func_dict = {'supervised_cifar10_augmentations':get_supervised_cifar10_augmentations}

# %% ../nbs/base_supervised.ipynb 21
@torch.no_grad()
def predict_model(xval,yval,model,aug_pipelines_test,numavg=3,criterion = CrossEntropyLossFlat(),deterministic=False):
    "Note that this assumes xval is entire validation set. If it doesn't fit in memory, can't use this guy"
    
    model.eval()

    N=xval.shape[0]
    
    if not deterministic:

        probs=0
        for _ in range(numavg):

            probs += torch.softmax(model(aug_pipelines_test[0](xval)),dim=1) #test time augmentation. This also gets around issue of randomness in the dataloader in each session...

        probs *= 1/numavg
        
    else:
        probs = torch.softmax(model(xval),dim=1)

    
    ypred = cast(torch.argmax(probs, dim=1),TensorCategory)

    correct = (ypred == yval)#.type(torch.FloatTensor)

    #correct = (torch.argmax(ypred,dim=1) == yval).type(torch.FloatTensor)
    num_correct = correct.sum()
    accuracy = num_correct/N

    #val_loss = criterion(scores,yval)
    
    return probs,ypred,accuracy.item()#,val_loss.item()

@torch.no_grad()
def predict_whole_model(dls_test, model, aug_pipelines_test, numavg=3, criterion=CrossEntropyLossFlat(), deterministic=False):
    """
    Predicts the labels and probabilities for the entire test set using the specified model and data augmentation
    pipelines. Returns a dictionary containing the labels, probabilities, predicted labels, and accuracy.

    Args:
        dls_test: The test dataloader.
        model: The trained model.
        aug_pipelines_test: The test data augmentation pipelines.
        numavg: The number of times to perform test-time augmentation.
        criterion: The loss function to use for computing the accuracy.
        deterministic: Whether to use deterministic computation.

    Returns:
        A dictionary containing the labels, probabilities, predicted labels, and accuracy.
    """
    model.eval()
    total_len = len(dls_test.dataset)
    y = torch.zeros(total_len, dtype=torch.long)
    probs = torch.zeros(total_len, model.head.out_features)
    ypred = torch.zeros(total_len, dtype=torch.long)

    start_idx = 0
    for xval, yval in dls_test.train:
        end_idx = start_idx + len(xval)
        _probs, _ypred, acc = predict_model(xval, yval, model, aug_pipelines_test, numavg, criterion, deterministic)
        y[start_idx:end_idx] = yval
        probs[start_idx:end_idx] = _probs
        ypred[start_idx:end_idx] = _ypred
        start_idx = end_idx

    # Calculate the overall accuracy
    acc = (ypred == y).float().mean().item()

    # Return the predictions and labels in a dictionary
    #return {'y': y, 'probs': probs, 'ypred': ypred, 'acc': acc}
    return y,probs,ypred,acc


# %% ../nbs/base_supervised.ipynb 23
def encoder_head_splitter(m):
    return L(sequential(*m.encoder),m.head).map(params)

# %% ../nbs/base_supervised.ipynb 25
class SaveModelCheckpoint(Callback):
    def __init__(self, experiment_dir, save_interval=250):
        self.experiment_dir = experiment_dir
        self.save_interval = save_interval

    def after_epoch(self):
        if (self.epoch+1) % self.save_interval == 0:
            print(f"Saving model checkpoint at epoch {self.epoch}")
            checkpoint_filename = f"model_checkpoint_epoch_{self.epoch}.pt"
            checkpoint_path = os.path.join(self.experiment_dir, checkpoint_filename)
            torch.save(self.learn.model.state_dict(), checkpoint_path)

# %% ../nbs/base_supervised.ipynb 26
class SupervisedLearning:
    "Train model using supervised learning. Either linear evaluation or semi-supervised."

    def __init__(self,
                 model,
                 dls_train,
                 aug_pipelines_supervised,
                 n_in,
                 model_type,
                 wd,
                 device,
                 experiment_dir=None,
                 save_interval=None
                 ):

       
        store_attr()
        self.learn = self.setup_learn()

    
    def setup_learn(self):
        """
        Sets up the learner with the model, callbacks, and metrics.

        Returns:
        - learn: The Learner object.
        """
        # Setup the model: encoder + head
        #model = LM(encoder=self.encoder, enc_dim=self.enc_dim, numout=len(self.dls_train.vocab))
        self.model.to(self.device)

        cbs = [LinearBt(aug_pipelines=self.aug_pipelines_supervised, show_batch=True, n_in=self.n_in, print_augs=True)]

        if self.experiment_dir is not None:
            cbs.append(SaveModelCheckpoint(self.experiment_dir,self.save_interval))

        # Setup the learner with callbacks and metrics
        learn = Learner(self.dls_train, self.model, splitter=encoder_head_splitter,cbs=cbs,wd=self.wd, metrics=accuracy)

        return learn
    
    def supervised_learning(self,epochs:int=1):

        test_grad_on(self.learn.model.encoder)
        test_grad_on(self.learn.model.head)
        lrs = self.learn.lr_find()
        self.learn.fit_one_cycle(epochs, lrs.valley)
        return self.learn.model
    
    def linear_evaluation(self,epochs:int=1):

        self.learn.freeze() #freeze encoder
        test_grad_off(self.learn.model.encoder)
        lrs = self.learn.lr_find() #find learning rate
        self.learn.fit_one_cycle(epochs, lrs.valley) #fit head
        return self.learn.model

    def semi_supervised(self,freeze_epochs:int=1,epochs:int=1):

        self.learn.freeze() #freeze encoder
        test_grad_off(self.learn.model.encoder)
        self.learn.fit(freeze_epochs) #fit head for (typically one) epoch
        self.learn.unfreeze() #unfreeze encoder
        test_grad_on(self.learn.model)
        lrs = self.learn.lr_find() #find learning rate
        self.learn.fit_one_cycle(epochs, lrs.valley) #fit all
        return self.learn.model


def train_supervised(model,
                    dls_train,
                    aug_pipelines_supervised,
                    n_in,
                    model_type,
                    wd,
                    epochs,
                    freeze_epochs,
                    weight_type, #random, supervised_pretrained, bt_pretrained, etc
                    device,
                    experiment_dir=None,
                    save_interval=None
                    ):


    supervised = SupervisedLearning(model=model,
                                    dls_train=dls_train,
                                    aug_pipelines_supervised=aug_pipelines_supervised,
                                    n_in=n_in,
                                    model_type=model_type,
                                    wd=wd,
                                    device=device,
                                    experiment_dir=experiment_dir,
                                    save_interval=save_interval
                                    )
    if weight_type!='random':
        #means we freeze the encoder for `freeze_epochs` first
        if model_type=='linear_evaluation':
            model = supervised.linear_evaluation(epochs=epochs)
        elif model_type=='semi_supervised':
            model = supervised.semi_supervised(freeze_epochs=freeze_epochs,epochs=epochs)

        else:
            raise ValueError('model_type must be linear_evaluation or semi_supervised')

    else:
        model = supervised.supervised_learning(epochs=epochs)

    return model

