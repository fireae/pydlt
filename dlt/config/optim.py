import torch
from torch.optim.lr_scheduler import ReduceLROnPlateau, StepLR
from ..util import Checkpointer
from .opts import fetch_opts, parse

def optimizer(model, subset=None):
    """Returns the optimizer for the given model. Configurable using command line arguments.
    
    Args:
        model (nn.Module): The network for the optimizer.
        subset (string, optional): Specifies the subset of the relevant
            categories, if any of them was split (default, None).

    Relevant Command Line Arguments:

        - **optimizer**: `--optimizer`, `--lr`, `--momentum`,
            `--dampening`, `--beta1`, `--beta2`, `--weight_decay`.

    Note:
        Settings are automatically acquired from a call to :func:`dlt.config.parse`
        from the built-in ones. If :func:`dlt.config.parse` was not called in the 
        main script, this function will call it.
    """
    opts = fetch_opts(categories=['optimizer'], subset=subset)

    if opts.optimizer not in parse.optimizers:
        raise ValueError('Optimizer {0} not available.'.format(opts.optimizer))

    grad_params = filter(lambda p: p.requires_grad, model.parameters())
    if opts.optimizer == 'adam':
        ret_optimizer = torch.optim.Adam(grad_params, lr=opts.lr, 
            betas=(opts.beta1, opts.beta2), weight_decay=opts.weight_decay)
    elif opts.optimizer == 'sgd':
        ret_optimizer = torch.optim.SGD(grad_params, lr=opts.lr, momentum=opts.momentum, 
            dampening=opts.dampening, weight_decay=opts.weight_decay)
    elif opts.optimizer == 'adadelta':
        ret_optimizer = torch.optim.Adadelta(grad_params, lr=opts.lr, rho=opts.rho, 
            eps=opts.optim_eps, weight_decay=opts.weight_decay)
    elif opts.optimizer == 'adagrad':
        ret_optimizer = torch.optim.Adagrad(grad_params, lr=opts.lr, 
            lr_decay=opts.lr_decay, weight_decay=opts.weight_decay)
    elif opts.optimizer == 'sparseadam':
        ret_optimizer = torch.optim.SparseAdam(grad_params, lr=opts.lr, 
            betas=(opts.beta1, opts.beta2), eps=opts.optim_eps)
    elif opts.optimizer == 'adamax':
        ret_optimizer = torch.optim.Adamax(grad_params, lr=opts.lr, 
            betas=(opts.beta1, opts.beta2), eps=opts.optim_eps, weight_decay=opts.weight_decay)
    elif opts.optimizer == 'rmsprop':
        ret_optimizer = torch.optim.RMSprop(grad_params, lr=opts.lr,
            alpha=opts.alpha, eps=opts.optim_eps, weight_decay=opts.weight_decay,
            momentum=opts.momentum, centered=opts.centered)
    return ret_optimizer

def scheduler(optimizer, subset=None):
    """Returns a scheduler callable closure which accepts one argument.
    
    Configurable using command line arguments.
    
    Args:
        optimizer (torch.optim.Optimizer): The optimizer for the scheduler.
        subset (string, optional): Specifies the subset of the relevant
            categories, if any of them was split (default, None).

    Relevant Command Line Arguments:

        - **scheduler**: `--lr_schedule`, `--lr_step_size`, `--lr_patience`,
            `--lr_cooldown`, `--lr_ratio`, `--lr_min`.

    Note:
        Settings are automatically acquired from a call to :func:`dlt.config.parse`
        from the built-in ones. If :func:`dlt.config.parse` was not called in the 
        main script, this function will call it.
    """
    opts = fetch_opts(categories=['scheduler'], subset=subset)
    if opts.lr_schedule == 'plateau':
        ret_scheduler = ReduceLROnPlateau(optimizer, mode='min', factor=opts.lr_ratio, threshold=0.0001,
                                    patience=opts.lr_patience, verbose=True, threshold_mode='rel',
                                    cooldown=opts.lr_cooldown, min_lr=opts.lr_min, eps=1e-08)
        def schedule_fn(metric):
            ret_scheduler.step(metric)
    elif opts.lr_schedule == 'step':
        ret_scheduler = StepLR(optimizer, step_size=opts.lr_step_size, gamma=opts.lr_ratio)
        def schedule_fn(metric):
                ret_scheduler.step()
    elif opts.lr_schedule == 'none':
        def schedule_fn(metric):
            pass
    
    def schedule_step(metric):
        current_lr = optimizer.param_groups[0]['lr']
        schedule_fn(metric)
        new_lr = optimizer.param_groups[0]['lr']
        if new_lr != current_lr:
            name = subset['optimizer'] if isinstance(subset, dict) else subset
            name = ' ({0})'.format(name) if name else ''
            print('Learning rate{0} changed from {1:.2e} to {2:.2e}'.format(name, current_lr, new_lr))

    return schedule_step

def epoch_checkpointer(subset=None):
    """Returns epoch checkpointer and current epoch. Configurable using command line arguments.
    
    Args:
        subset (string, optional): Specifies the subset of the relevant
            categories, if any of them was split (default, None).

    Relevant Command Line Arguments:

        - **general**: `--experiment_name`, `--save_path`.

    Note:
        Settings are automatically acquired from a call to :func:`dlt.config.parse`
        from the built-in ones. If :func:`dlt.config.parse` was not called in the 
        main script, this function will call it.
    """
    opts = fetch_opts(categories=['general'], subset=subset)
    epoch_chkp = Checkpointer('epoch_' + opts.experiment_name, directory=opts.save_path, overwrite=True, timestamp=False, add_count=False)
    current_epoch = epoch_chkp.load() or 1
    return epoch_chkp, current_epoch

def lr_checkpointer(optimizer, subset=None):
    """Returns learning rate checkpointer. Configurable using command line arguments.

    Also sets the learning rate for the optimizer.
    
    Args:
        optimizer (torch.optim.Optimizer): The optimizer for which to set the learning rate.
        subset (string, optional): Specifies the subset of the relevant
            categories, if any of them was split (default, None).

    Relevant Command Line Arguments:

        - **general**: `--experiment_name`, `--save_path`.

    Note:
        Settings are automatically acquired from a call to :func:`dlt.config.parse`
        from the built-in ones. If :func:`dlt.config.parse` was not called in the 
        main script, this function will call it.
    """
    
    opts = fetch_opts(categories=['general', 'optimizer'], subset=subset)
    lr_chkp = Checkpointer('lr_' + opts.experiment_name, directory=opts.save_path, overwrite=True, timestamp=False, add_count=False)
    lr = lr_chkp.load() or opts.lr
    optimizer.param_groups[0]['lr'] = lr
    name = subset['optimizer'] if isinstance(subset, dict) else subset
    name = ' ({0})'.format(name) if name else ''
    print('Learning rate{0} initialized to {1:.2e}.'.format(name, lr))
    return lr_chkp
