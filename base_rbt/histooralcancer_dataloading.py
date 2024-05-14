# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/histooralcancer_dataloading.ipynb.

# %% auto 0
__all__ = ['label_func', 'get_supervised_histooralcancer_train_dls', 'get_supervised_histooralcancer_test_dls']

# %% ../nbs/histooralcancer_dataloading.ipynb 3
import torch
from fastai.vision.all import *
# from self_supervised.augmentations import *
# from self_supervised.layers import *
from .utils import *
import re
import os


# %% ../nbs/histooralcancer_dataloading.ipynb 7
def label_func(x):
    # Function to extract the label from the parent directory name
    return x.parent.name

def get_supervised_histooralcancer_train_dls(bs, dataset_dir, size=256, device='cpu', pct_dataset=1.0, num_workers=12):
    train_dir = os.path.join(dataset_dir, "train")  # Corrected path to the train directory
    
    # Get image files from the training directory
    fnames = get_image_files(train_dir)

    # Apply subset size
    n = int(len(fnames) * pct_dataset)
    fnames = fnames[:n]

    # Data transformations

    # Create the DataLoader
    dls = ImageDataLoaders.from_path_func(
        path=train_dir,
        fnames=fnames,
        label_func=label_func,
        bs=bs,
        valid_pct=0.0,  # No validation split, using all for training
        device=device,
        num_workers=num_workers * (device == 'cuda')
    )

    return dls

def get_supervised_histooralcancer_test_dls(bs, dataset_dir, size=256, device='cpu', pct_dataset=1.0, num_workers=12):
    test_dir = os.path.join(dataset_dir, "test")  # Corrected path to the test directory
    val_dir = os.path.join(dataset_dir, "val")    # Path to the validation directory
    
    # Get image files from the testing and validation directories
    fnames = get_image_files(test_dir) + get_image_files(val_dir)

    # Apply subset size
    n = int(len(fnames) * pct_dataset)
    fnames = fnames[:n]

    # Data transformations
    # Create the DataLoader
    dls = ImageDataLoaders.from_path_func(
        path=test_dir,  # Path used for DataLoader
        fnames=fnames,
        label_func=label_func,
        bs=bs,
        valid_pct=0,  # No validation split for the test set
        device=device,
        drop_last=False,
        num_workers=num_workers * (device == 'cuda')
    )

    return dls
