"""utility stuff."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/utils.ipynb.

# %% auto 0
__all__ = ['PACKAGE_NAME', 'test_grad_on', 'test_grad_off', 'seed_everything', 'adjust_config_with_derived_values', 'load_config',
           'pretty_print_ns', 'get_resnet_encoder', 'get_cifar_resnet18', 'resnet_arch_to_encoder', 'SimpleCNN',
           'BinocularEncoder', 'share_resnet_parameters', 'test_resnet_parameter_sharing_with_training',
           'generate_config_hash', 'create_experiment_directory', 'save_configuration', 'save_metadata_file',
           'update_experiment_index', 'get_latest_commit_hash', 'setup_experiment', 'InterruptCallback',
           'SaveLearnerCheckpoint', 'extract_number', 'find_largest_file', 'return_max_filename',
           'get_highest_num_path', 'save_dict_to_gdrive', 'load_dict_from_gdrive', 'download_weights']

# %% ../nbs/utils.ipynb 3
from fastcore.test import *
from fastai.vision.all import *
import torch
from torchvision.models import resnet18, resnet34, resnet50
from typing import Literal
import random 
import os 
import yaml
import numpy as np
import yaml
import configparser
from types import SimpleNamespace
import importlib
from nbdev import config
import json
import hashlib
import subprocess
import re
import sys
import os
import zipfile
import torch.nn as nn
import torch.optim as optim
import torch
import torch.nn as nn
from timm.models.swin_transformer import SwinTransformerBlock


# %% ../nbs/utils.ipynb 4
# cfg = config.get_config()
# PACKAGE_NAME = cfg.lib_name
PACKAGE_NAME = 'base_rbt' #hardcoded for now

# %% ../nbs/utils.ipynb 5
def test_grad_on(model):
    """
    Test that all grads are on for modules with parameters.
    """
    for name, module in model.named_modules():
        # Check each parameter in the module
        for param_name, param in module.named_parameters(recurse=False):
            assert param.requires_grad, f"Gradients are off for {name}.{param_name}"

def test_grad_off(model):
    """
    Test that all non-batch norm grads are off, but batch norm grads are on.
    """
    for name, module in model.named_modules():
        # Distinguish between BatchNorm and other layers
        if isinstance(module, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d, torch.nn.BatchNorm3d)):
            for param_name, param in module.named_parameters(recurse=False):
                assert param.requires_grad, f"BatchNorm parameter does not require grad in {name}.{param_name}"
        else:
            for param_name, param in module.named_parameters(recurse=False):
                assert not param.requires_grad, f"Gradients are on for non-BatchNorm layer {name}.{param_name}"

# %% ../nbs/utils.ipynb 6
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

# %% ../nbs/utils.ipynb 7
def adjust_config_with_derived_values(config):
    # Adjust n_in based on dataset


    #This is really just for backwards compatibility (old configs) and so
    # we easily have access to `encoder_dimension`; of course it's 
    #*determined* by the arch. This is a biy annoying, but we just leave it
    #as is for simplicity. 
    
    if config.arch in ['smallres','resnet18','cifar_resnet18',\
                       'cnn_lr_cifar_resnet18','res_lr_cifar_resnet18','cifar_resnet18_swin','resnet34']:
        config.encoder_dimension = 512

    elif config.arch in ['resnet50']:
        config.encoder_dimension = 2048

    else :
        raise ValueError(f"Architecture {config.arch} not supported")

    for key, value in list(config.__dict__.items()): 
        if value == 'none':
            config.__dict__[key] = None
        if value == 'True':
            config.__dict__[key] = True
        if value == 'False':
            config.__dict__[key] = False

    return config

def load_config(file_path):
    with open(file_path, 'r') as f:
        config = yaml.safe_load(f)
        config = SimpleNamespace(**config)
        config = adjust_config_with_derived_values(config)
        

    return config

# %% ../nbs/utils.ipynb 8
def pretty_print_ns(ns):
    """
    Pretty print a SimpleNamespace object
    """
    for key, value in ns.__dict__.items():
        print(f"{key}: {value}")

# %% ../nbs/utils.ipynb 10
class _SmallRes(nn.Module):
    def __init__(self, num_classes=1000):
        super().__init__()
        # First layer
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        # Minimal Intermediate layer
        self.intermediate_conv = nn.Conv2d(64, 512, kernel_size=1, stride=1, bias=False)
        self.intermediate_bn = nn.BatchNorm2d(512)
        self.intermediate_relu = nn.ReLU(inplace=True)

        # Last two layers
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512, num_classes)

    def forward(self, x):
        # First layer
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        # Minimal Intermediate layer
        x = self.intermediate_conv(x)
        x = self.intermediate_bn(x)
        x = self.intermediate_relu(x)

        # Last two layers
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)

        return x


# %% ../nbs/utils.ipynb 11
# import torch
# import torch.nn as nn
# from torchvision.models import resnet18, resnet34, resnet50
# from torchvision.models.resnet import ResNet18_Weights, ResNet34_Weights, ResNet50_Weights
# from typing import Literal

@torch.no_grad()
def get_resnet_encoder(model, n_in=3,flatten=True,remove_pool=False):

    if remove_pool:
        cut_point=2 
    else:
        cut_point=1
    model = create_body(model, n_in=n_in, pretrained=False, cut=len(list(model.children()))-cut_point)
    if flatten:
        model.add_module('flatten', torch.nn.Flatten())
    return model

# @torch.no_grad()
# def get_resnet_encoder(model, n_in=3, flatten=True, remove_pool=True):
#     # Remove the final FC layer
#     modules = list(model.children())[:-1]
    
#     # Optionally remove the final adaptive average pooling layer
#     if remove_pool:
#         modules = modules[:-1]
    
#     model = nn.Sequential(*modules)
    
#     if flatten:
#         model.add_module('flatten', nn.Flatten())
    
#     return model

#helper function
def get_cifar_resnet18(model,n_in=3):
    """Modifies a ResNet18 model for CIFAR-10."""
    model.conv1 = nn.Conv2d(n_in, 64, kernel_size=3, stride=1, padding=1, bias=False)
    model.maxpool = nn.Identity()
    return model

@torch.no_grad()
def resnet_arch_to_encoder(
    arch: Literal['smallres', 'resnet18', 'resnet34', 'resnet50', 'cifar_resnet18'],
    weight_type: Literal['random', 'imgnet_bt_pretrained', 'imgnet_sup_pretrained',
                         'dermnet_bt_pretrained', 'imgnet_bt_dermnet_bt_pretrained', 
                         'cifar10_pretrained,'] = 'random',
    remove_pool=False,
    flatten=True,
    n_in=3,
                            ):
    """
    Given a ResNet architecture, return the encoder configured for 3 input channels.
    The 'weight_type' argument specifies the weight initialization strategy.

    Args:
        arch: The architecture of the ResNet.
        weight_type: Specifies the weight initialization strategy. Defaults to 'random'.

    Returns:
        Encoder: An encoder configured for 3 input channels and specified architecture.
    """

    if weight_type == 'imgnet_bt_pretrained': 
        assert arch == 'resnet50', "ImageNet Barlow Twins pretrained weights are only available for ResNet50"
    
    if arch == 'resnet50':
        if weight_type == 'imgnet_bt_pretrained':
            _model = torch.hub.load('facebookresearch/barlowtwins:main', 'resnet50')
        elif weight_type == 'imgnet_sup_pretrained':
            _model = resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)
        else:
            _model = resnet50()
        
    elif arch == 'resnet34':
        if weight_type == 'imgnet_sup_pretrained':
            _model = resnet34(weights=ResNet34_Weights.IMAGENET1K_V1)
        else:
            _model = resnet34()

    elif arch == 'resnet18':
        if weight_type == 'imgnet_sup_pretrained':
            _model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        else:
            _model = resnet18()

    elif 'cifar_resnet18' in arch:
        assert weight_type in ['random', 'cifar10_pretrained'], "CIFAR ResNet18 only supports 'random' or 'cifar10_pretrained' weight types"
        _model = resnet18()
        _model = get_cifar_resnet18(_model,n_in=n_in)  # Adjust ResNet18 for CIFAR-10

    elif arch == 'smallres':
        _model = _SmallRes()
    
    else:
        raise ValueError('Architecture not recognized')

    return get_resnet_encoder(_model,remove_pool=remove_pool,flatten=flatten)

# %% ../nbs/utils.ipynb 13
class SimpleCNN(nn.Module):
    def __init__(self, in_channels=3, out_channels=3):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, out_channels, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
    
    def forward(self, x):
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        return x

class BinocularEncoder(nn.Module):
    def __init__(self, res):
        super().__init__()
        self.left_cnn = SimpleCNN(in_channels=3, out_channels=3)
        self.right_cnn = SimpleCNN(in_channels=3, out_channels=3)
        self.res = res
    
    def forward(self, x):
        # e.g. x = Bx3x32x32
        x_left = x[:, :, :, :x.shape[3]//2]  # left half of x
        x_right = x[:, :, :, x.shape[3]//2:]  # right half of x
        
        x_left = self.left_cnn(x_left)
        x_right = self.right_cnn(x_right)
        
        # Concatenate along the width dimension
        x_cat = torch.cat([x_left, x_right], dim=-1)
        
        x = self.res(x_cat+x)
        return x

# res = resnet_arch_to_encoder('cifar_resnet18')
# model = BinocularEncoder(res)
# _x = torch.rand(1,3,32,32)
# model(_x).shape


# %% ../nbs/utils.ipynb 15
def share_resnet_parameters(encoder_left, encoder_right):
    """Just tested for resnet18 or cifar_resnet18. Share params up to and inc stage 1."""
    for i in range(5):  # 0 to 4 inclusive
        encoder_right[i] = encoder_left[i]
    
    return encoder_left, encoder_right

def test_resnet_parameter_sharing_with_training(encoder_left, encoder_right):
    # Previous tests
    test_eq(encoder_left[0], encoder_right[0])
    test_eq(encoder_left[4], encoder_right[4])
    test_eq(encoder_left[4][0].conv1.weight.data, encoder_right[4][0].conv1.weight.data)
    test_eq(encoder_left[5] is encoder_right[5], False)
    
    # Set up a simple optimization step
    optimizer_left = optim.SGD(encoder_left.parameters(), lr=0.1)
    optimizer_right = optim.SGD(encoder_right.parameters(), lr=0.1)
    criterion = nn.MSELoss()

    # Simulate a forward pass and backward pass
    dummy_input = torch.randn(1, 3, 224, 224)
    output_left = encoder_left(dummy_input)
    output_right = encoder_right(dummy_input)
    
    target = torch.randn(output_left.shape)
    loss_left = criterion(output_left, target)
    loss_right = criterion(output_right, target)

    optimizer_left.zero_grad()
    optimizer_right.zero_grad()
    loss_left.backward()
    loss_right.backward()
    optimizer_left.step()
    optimizer_right.step()

    # Check if parameters are still the same after update
    test_eq(encoder_left[4][0].conv1.weight.data, encoder_right[4][0].conv1.weight.data)
    
    print("All tests passed, including parameter update check!")
   

# %% ../nbs/utils.ipynb 18
def generate_config_hash(config):
    """
    Generates a unique hash for a given experiment configuration.
    
    Args:
    config (dict or Namespace): Experiment configuration. Can be a dictionary or a namespace object.
    
    Returns:
    str: A unique hash representing the experiment configuration.
    """
    # Convert config to dict if it's a Namespace
    config_dict = vars(config) if not isinstance(config, dict) else config
    
    # Serialize configuration to a sorted JSON string to ensure consistency
    config_str = json.dumps(config_dict, sort_keys=True)
    
    # Generate SHA-256 hash from the serialized string
    hash_obj = hashlib.sha256(config_str.encode())  # Encode to convert string to bytes
    config_hash = hash_obj.hexdigest()
    
    # Optionally, return a truncated version of the hash for readability
    short_hash = config_hash[:8]  # Use the first 8 characters as an example
    return short_hash


# %% ../nbs/utils.ipynb 21
def create_experiment_directory(base_dir, config):
    # Generate a unique hash for the configuration
    unique_hash = generate_config_hash(config)
    
    # Construct the directory path for this experiment
    experiment_dir = os.path.join(base_dir, config.train_type, config.dataset, config.arch, unique_hash)
    
    # Create the directory if it doesn't exist
    os.makedirs(experiment_dir, exist_ok=True)
    
    return experiment_dir,unique_hash


def save_configuration(config, experiment_dir):
    """
    Saves the experiment configuration as a YAML file in the experiment directory.

    Args:
    config (dict, Namespace, or any serializable object): Experiment configuration.
    experiment_dir (str): Path to the directory where the config file will be saved.
    """
    config_file_path = os.path.join(experiment_dir, 'config.yaml')
    
    # Check if config is not a dictionary (e.g., a Namespace object) and convert if necessary
    config_dict = vars(config) if not isinstance(config, dict) else config
    
    with open(config_file_path, 'w') as file:
        yaml.dump(config_dict, file)
    
    print(f"Configuration saved to {config_file_path}")




def save_metadata_file(experiment_dir, git_commit_hash):
    """
    Saves a metadata file with the Git commit hash
    """
    metadata_file_path = os.path.join(experiment_dir, 'metadata.yaml')
    metadata_content = {
        "Git Commit Hash": git_commit_hash,
    }

    with open(metadata_file_path, 'w') as file:
        yaml.dump(metadata_content, file)

    print(f"Metadata saved to {metadata_file_path}")


def update_experiment_index(project_root, details):
    central_json_path = os.path.join(project_root, 'experiment_index.json')
    
    if os.path.exists(central_json_path):
        with open(central_json_path, 'r') as file:
            experiments_index = json.load(file)
    else:
        experiments_index = {}
    
    experiment_hash = details["experiment_hash"]
    experiments_index[experiment_hash] = details
    
    with open(central_json_path, 'w') as file:
        json.dump(experiments_index, file, indent=4)
    
    print(f"Updated experiment index for hash: {experiment_hash}")


def get_latest_commit_hash(repo_path):
    try:
        commit_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo_path).decode('ascii').strip()
        return commit_hash
    except subprocess.CalledProcessError as e:
        print(f"Error obtaining latest commit hash: {e}")
        return None

def setup_experiment(config,base_dir):

    # Create a unique directory for this experiment based on its configuration
    # This directory will contain all artifacts related to the experiment, such as model checkpoints and logs.
    experiment_dir, experiment_hash = create_experiment_directory(base_dir, config)

    print(f"The experiment_dir is: {experiment_dir} and the experiment hash is: {experiment_hash}")

    # Save the loaded configuration to the experiment directory as a YAML file
    # This ensures that we can reproduce or analyze the experiment later.
    save_configuration(config, experiment_dir)

    git_commit_hash = get_latest_commit_hash('.')
    print(f"The git hash is: {git_commit_hash}")

    return experiment_dir, experiment_hash,git_commit_hash


# %% ../nbs/utils.ipynb 22
class InterruptCallback(Callback):
    def __init__(self, interrupt_epoch):
        super().__init__()
        self.interrupt_epoch = interrupt_epoch

    def before_epoch(self):
        if self.epoch == self.interrupt_epoch:
            print(f"Interrupting training before starting epoch {self.interrupt_epoch}")
            raise CancelFitException

class SaveLearnerCheckpoint(Callback):
    def __init__(self, experiment_dir,start_epoch=0, save_interval=250, with_opt=True):
        self.experiment_dir = experiment_dir
        self.start_epoch = start_epoch
        self.save_interval = save_interval
        self.with_opt = with_opt  # Decide whether to save optimizer state as well.

    def after_epoch(self):
        if (self.epoch+1) % self.save_interval == 0 and self.epoch>=self.start_epoch:
            print(f"Saving model and learner state at epoch {self.epoch}")
   
            checkpoint_filename = f"learner_checkpoint_epoch_{self.epoch}"
            checkpoint_path = os.path.join(self.experiment_dir, checkpoint_filename)
            # Save the entire learner object, including the model's parameters and optimizer state.
            self.learn.save(checkpoint_path, with_opt=self.with_opt)
            print(f"Checkpoint saved to {checkpoint_path}")


# %% ../nbs/utils.ipynb 23
def extract_number(filename):
    """Extract the number from end of  filename. e.g. `epoch`"""
    #pattern = re.compile(r"_epoch_(\d+)\.pt[h]?")
    pattern = re.compile(r"_(\d+)\.pt[h]?")
    match = pattern.search(filename)
    return int(match.group(1)) if match else None

def find_largest_file(directory_path):
    """Find the file with the largest number (e.g. epoch) in a directory."""
    _max = -1
    largest_file = None

    for filename in os.listdir(directory_path):
        num = extract_number(filename)
        if num is not None and num > _max:
            _max = num
            largest_file = filename

    return largest_file

def return_max_filename(filename1, filename2):
    # Improved handling for initial cases
    if not filename1:
        return filename2
    if not filename2:
        return filename1

    # Extract epochs and compare
    num1 = extract_number(filename1)
    num2 = extract_number(filename2)

    # Return the filename with the larger epoch number
    return filename1 if num1 >= num2 else filename2

def get_highest_num_path(base_dir, config):
    """
    Check in the specific experiment directory derived from the config and return the path to the file
    with the highest number along with its experiment directory.
    """
    # Build the specific experiment directory from base_dir and config
    experiment_dir, _ = create_experiment_directory(base_dir, config)
    print(f"Looking in {experiment_dir} for highest num saved")

    _max_file_path = None
    _max_experiment_dir = experiment_dir

    # Find the largest file in the specific experiment directory
    _x = find_largest_file(experiment_dir)
    if _x:
        _max_file_path = os.path.join(experiment_dir, _x)
        print(f"Found max file path: {_max_file_path} and max experiment dir: {_max_experiment_dir}")
        _max_file_path = _max_file_path.split('.')[0]

    return _max_file_path, _max_experiment_dir  # Return both file path and directory


# def get_highest_num_path(base_dir, config):
#     """
#     Check in all experiment directories derived from the config and return the path
#     to the file with the highest number along with its experiment directory.
#     """

#     experiment_index_path = base_dir + '/experiment_index.json'

#     try: 
#         # Load the JSON data from the file
#         with open(experiment_index_path, 'r') as file:
#             experiment_index = json.load(file)

#     except FileNotFoundError:
#         return None,None


#     # Build the main part of the experiment directory from base_dir and config
#     _experiment_dir, _ = create_experiment_directory(base_dir, config)
#     base_experiment_dir = os.path.dirname(_experiment_dir)  # Strip the hash part

#     print(f"looking in {base_experiment_dir} for highest num saved")
#     _max_file_path = None
#     _max_experiment_dir = None  # To keep track of the directory of the max file

#     for k in list(experiment_index.keys()):
#         _experiment_dir = experiment_index[k]['experiment_dir']
#         if base_experiment_dir not in _experiment_dir:
#             continue
#         _x = find_largest_file(_experiment_dir)
#         if _x:
#             _x_path = os.path.join(_experiment_dir, _x)
#             # Update max_file_path and the corresponding experiment_dir if a new max is found
#             if not _max_file_path or return_max_filename(_x_path, _max_file_path) == _x_path:
#                 _max_file_path = _x_path
#                 _max_experiment_dir = _experiment_dir
    

#     print(f"Found max file path: {_max_file_path} and max experiment dir: {_max_experiment_dir}")
    
#     _max_file_path = _max_file_path.split('.')[0] if _max_file_path else None

#     return _max_file_path, _max_experiment_dir  # Return both file path and directory

    

# %% ../nbs/utils.ipynb 24
def save_dict_to_gdrive(d,directory, filename):
    #e.g. directory='/content/drive/My Drive/random_initial_weights'
    filepath = directory + '/' + filename + '.pkl'
    with open(filepath, "wb") as f:
        pickle.dump(d, f)

def load_dict_from_gdrive(directory,filename):
    #e.g. directory='/content/drive/My Drive/random_initial_weights'
    filepath = directory + '/' + filename + '.pkl'
    with open(filepath, "rb") as f:
        d = pickle.load(f)
    return d

# %% ../nbs/utils.ipynb 25
def download_weights():

    # Define paths
    zip_path = '/content/drive/MyDrive/model_weights.zip'
    extract_path = '/content/drive/MyDrive'
    
    # Check if weights are already unzipped
    example_path = '/content/drive/MyDrive/Experiments/barlow_twins/SSL/isicufes/resnet50/c34772a2/trained_encoder_epoch_99.pth'
    
    if os.path.exists(example_path):
        print("Model weights are already set up.")
    else:
        print("Model weights not found. Attempting to unzip...")
        
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print(f"Model weights unzipped to: {extract_path}/Experiments")
        else:
            print(f"Error: Zip file not found at: {zip_path}")
            print("Please ensure you've uploaded 'shared_model_weights.zip' to your Google Drive root")
# Usage:
# setup_and_verify_model_weights() (only have to call once)
