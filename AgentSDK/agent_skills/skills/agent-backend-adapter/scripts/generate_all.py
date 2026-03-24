#!/usr/bin/env python3
"""Code Generator for Agent Training Scripts"""
import os

TEMPLATES = {"train": "train_template.py", "vllm": "vllm_adapter_template.py"}
DEFAULTS = {
    "train": dict(framework="verl", n_gpus=8, n_samples=4, tp_size=2, lr=1e-6, epochs=15),
    "vllm": dict()
}
CONFIGS = {
    "train": ["framework", "n_gpus", "n_samples", "tp_size", "lr", "epochs"],
    "vllm": []
}
TRAINER = {"verl": "from verl.trainer.ppo.ray_trainer import RayPPOTrainer", "msrl": "from mindspeed_rl import RayGRPOTrainer"}

def generate(name: str, output: str, **kw) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "templates", TEMPLATES[name])
    with open(path) as f:
        t = f.read()
    d = DEFAULTS[name].copy()
    d.update(kw)
    r = {"output_basename": os.path.basename(output)}
    for k in CONFIGS[name]:
        v = d.get(k, "")
        r[k] = str(v) if not isinstance(v, str) else v
    for k, v in r.items():
        t = t.replace("{" + k + "}", v)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    with os.fdopen(fd, 'w') as f:
        f.write(t)
    return output

if __name__ == "__main__":
    generate("train", "agent_train_sample.py")
    generate("vllm", "vllm_adapter_sample.py")
