# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/helper.ipynb.

# %% auto 0
__all__ = ['test_grad_on', 'test_grad_off']

# %% ../nbs/helper.ipynb 4
from fastcore.test import *
import torch

# %% ../nbs/helper.ipynb 5
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
