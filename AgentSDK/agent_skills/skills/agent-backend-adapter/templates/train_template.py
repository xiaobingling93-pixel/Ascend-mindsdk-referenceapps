#!/usr/bin/env python3
"""Unified Agent Training Script Template

Usage:
    python agent_train_sample.py --model_path <model> [--framework verl|msrl]
"""
import os, argparse, logging
import ray
from omegaconf import OmegaConf

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def parse_args():
    p = argparse.ArgumentParser(description="Agent Training")
    p.add_argument("--model_path", type=str, required=True)
    p.add_argument("--framework", type=str, default="verl", choices=["verl", "msrl"])
    p.add_argument("--n_gpus", type=int, default=8)
    p.add_argument("--n_samples", type=int, default=4)
    p.add_argument("--tp_size", type=int, default=2)
    p.add_argument("--lr", type=float, default=1e-6)
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--output_dir", type=str, default="./checkpoints")
    p.add_argument("--copy_from", type=str, default="")
    p.add_argument("--copy_to", type=str, default="")
    return p.parse_args()

def copy_file(src, dst):
    import shutil
    if os.path.exists(src):
        shutil.copy2(src, dst)
        logger.info(f"Copied: {src} -> {dst}")
    else:
        logger.warning(f"Source not found: {src}")

from verl.trainer.ppo.ray_trainer import RayPPOTrainer
from mindspeed_rl import RayGRPOTrainer

def main():
    args = parse_args()
    if args.copy_from and args.copy_to:
        copy_file(args.copy_from, args.copy_to)
        return
    
    ray.init(num_cpus=args.n_gpus*8, num_gpus=args.n_gpus, runtime_env={{
        "env_vars": {{"TOKENIZERS_PARALLELISM": "false", "NCCL_DEBUG": "WARN"}}
    }})
    
    cfg = OmegaConf.create({{
        "model": args.model_path, "n_gpus": args.n_gpus, "n_samples": args.n_samples,
        "tp_size": args.tp_size, "lr": args.lr, "epochs": args.epochs, "framework": args.framework
    }})
    
    logger.info(f"Training: {{args.framework}} | Model: {{args.model_path}} | GPUs: {{args.n_gpus}}")

if __name__ == "__main__":
    main()
