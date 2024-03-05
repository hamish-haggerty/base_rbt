# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cifar10_dataloading.ipynb.

# %% auto 0
__all__ = ['seed', 'size', 'path', 'fnames_train', 'fnames_test', 'labels_train', 'labels_test', 'get_bt_cifar10_train_dls',
           'get_supervised_cifar10_train_dls', 'get_supervised_cifar10_test_dls', 'label_func']

# %% ../nbs/cifar10_dataloading.ipynb 3
import torch
from fastai.vision.all import *
# from self_supervised.augmentations import *
# from self_supervised.layers import *
from .utils import *

# %% ../nbs/cifar10_dataloading.ipynb 5
def get_bt_cifar10_train_dls(bs,size,device,pct_dataset=1.0,num_workers=12):
    
    n = int(len(fnames_train)*pct_dataset)-1

    return ImageDataLoaders.from_lists(path, fnames_train[0:n], labels_train[0:n],bs=bs, item_tfms=[Resize(size=size)], #batch_tfms=[ToTensor(), IntToFloatTensor()],
                                  valid_pct=0.0,num_workers=num_workers,device=device,seed=seed
                                      )


def get_supervised_cifar10_train_dls(bs,size,device,pct_dataset=1.0,num_workers=12):

    n = int(len(fnames_train)*pct_dataset)-1

    return ImageDataLoaders.from_lists(path, fnames_train, labels_train,bs=bs, item_tfms=[Resize(size=size)], #batch_tfms=[ToTensor(), IntToFloatTensor()],
                                  valid_pct=0.0,num_workers=num_workers,device=device,seed=seed
                                      )

def get_supervised_cifar10_test_dls(bs,size,device,pct_dataset=1.0,num_workers=12):
    
    n = int(len(fnames_train)*pct_dataset)-1
    
    return ImageDataLoaders.from_lists(path, fnames_test, labels_test,bs=bs, item_tfms=[Resize(size=size)], #batch_tfms=[ToTensor(), IntToFloatTensor()],
                                  valid_pct=0.0,num_workers=num_workers,device=device,seed=seed
                                      )
                                      

seed=42
size=32
path = untar_data(URLs.CIFAR)
fnames_train = get_image_files(path / "train") 
fnames_train.sort()
#shuffle data (in reproducible way)
seed_everything(seed=seed)
fnames_train = fnames_train.shuffle()

fnames_test = get_image_files(path / "test")

def label_func(fname):
    return fname.name.split('_')[1].strip('png').strip('.')

#labels for train,eval and test
labels_train = [label_func(fname) for fname in fnames_train]
labels_test = [label_func(fname) for fname in fnames_test]

test_eq(len(labels_train),len(fnames_train))
test_eq(len(labels_test),len(fnames_test))
test_eq(len(set(labels_train)),10)
test_eq(len(labels_train),50000)
test_eq(len(labels_test),10000)


