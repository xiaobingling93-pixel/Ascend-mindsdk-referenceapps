# Common Solutions Reference

Solutions and workarounds for common issues in Ascend NPU environments.

## Quick Fixes

### Environment Setup

**Problem**: Module not found after installation

```bash
# Solution 1: Verify installation location
pip show <package>
python -c "import sys; print(sys.path)"

# Solution 2: Reinstall in current environment
pip uninstall <package>
pip install <package>

# Solution 3: Use editable install for development
pip install -e .

# Solution 4: Check CANN environment (for NPU packages)
source /usr/local/Ascend/ascend-toolkit/set_env.sh
```

**Problem**: Wrong Python version

```bash
# Check Python version
python --version

# Switch to correct version
conda activate <env-name>
# or
pyenv local <version>
```

---

### CANN/NPU Issues

**Problem**: CANN not found / ACL import error

```bash
# Solution 1: Source CANN environment
source /usr/local/Ascend/ascend-toolkit/set_env.sh

# Solution 2: Verify CANN installation
npu-smi info

# Solution 3: Check CANN version
cat /usr/local/Ascend/ascend-toolkit/version.info

# Solution 4: Add to shell profile
echo "source /usr/local/Ascend/ascend-toolkit/set_env.sh" >> ~/.bashrc
```

**Problem**: NPU device not found

```bash
# Check NPU devices
npu-smi list

# Check NPU status
npu-smi info

# Check driver
npu-smi -v
```

---

### CUDA/NPU Memory Issues

**Problem**: NPU out of memory

```python
# Immediate fix - clear cache (requires NPU management tools)
# Or restart the process

# Long-term solutions
# 1. Reduce batch size
dataloader = DataLoader(dataset, batch_size=4)

# 2. Use gradient accumulation
accumulation_steps = 4
for i, batch in enumerate(dataloader):
    loss = model(batch) / accumulation_steps
    loss.backward()
    if (i + 1) % accumulation_steps == 0:
        optimizer.step()
        optimizer.zero_grad()

# 3. Enable mixed precision (if supported)
# Check SDK documentation for FP16/BF16 support

# 4. Enable gradient checkpointing
model.gradient_checkpointing_enable()
```

**Problem**: CUDA out of memory (when using GPU fallback)

```python
# Immediate fix
torch.cuda.empty_cache()

# Long-term solutions (same as NPU)
# See above
```

---

### Distributed Training

**Problem**: NCCL/NPU cluster errors

```bash
# Debug NCCL (for GPU)
export NCCL_DEBUG=INFO

# For Ascend NPU cluster
export HCCL_DEBUG=INFO
export HCCL_SOCKET_IFNAME=eth0

# Common fixes
export HCCL_IB_DISABLE=1
export HCCL_P2P_DISABLE=1

# Verify environment variables
echo "RANK: $RANK"
echo "WORLD_SIZE: $WORLD_SIZE"
echo "MASTER_ADDR: $MASTER_ADDR"
echo "MASTER_PORT: $MASTER_PORT"

# Set if missing
export MASTER_ADDR=localhost
export MASTER_PORT=29500
export WORLD_SIZE=2
export RANK=0
```

**Problem**: Process group initialization failed

```bash
# Verify environment variables
echo "RANK: $RANK"
echo "WORLD_SIZE: $WORLD_SIZE"
echo "MASTER_ADDR: $MASTER_ADDR"
echo "MASTER_PORT: $MASTER_PORT"

# Check network connectivity between nodes
ping <other-node>
nc -zv <other-node> <port>
```

---

### Configuration Issues

**Problem**: YAML parsing errors

```bash
# Validate YAML
yamllint config.yaml

# Check for tabs (YAML requires spaces)
cat -A config.yaml | grep $'\t'

# Convert tabs to spaces
expand -t 2 config.yaml > config_fixed.yaml
```

**Problem**: Missing configuration values

```python
# Use defaults
value = config.get('key', default_value)

# Or validate early
required_keys = ['learning_rate', 'batch_size', 'model_path']
for key in required_keys:
    if key not in config:
        raise ValueError(f"Missing required config: {key}")
```

---

### Network Issues

**Problem**: DNS resolution failures

```bash
# Quick fix for socket.gaierror
echo "127.0.0.1 $(hostname)" | sudo tee -a /etc/hosts

# Check DNS
cat /etc/resolv.conf
nslookup $(hostname)
```

**Problem**: Connection timeouts

```bash
# Check connectivity
ping <host>
traceroute <host>

# Check ports
nc -zv <host> <port>
telnet <host> <port>

# Check firewall
iptables -L | grep <port>
```

---

## Performance Optimization

### Memory Optimization

```python
# 1. Use data streaming instead of loading everything
def data_generator(file_path):
    with open(file_path) as f:
        for line in f:
            yield process(line)

# 2. Delete unused variables
del large_tensor
torch.cuda.empty_cache()

# 3. Use CPU/NPU offload for large models
from accelerate import init_empty_weights, load_checkpoint_and_dispatch

with init_empty_weights():
    model = Model()

model = load_checkpoint_and_dispatch(
    model, checkpoint, device_map="auto", offload_folder="offload"
)
```

### I/O Optimization

```python
# 1. Use async data loading
dataloader = DataLoader(
    dataset,
    batch_size=32,
    num_workers=4,
    pin_memory=True,
    prefetch_factor=2
)

# 2. Cache frequently accessed data
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_operation(key):
    return load_data(key)
```

---

## Debugging Techniques

### Enable Verbose Logging

```python
# Set logging level
import logging
logging.basicConfig(level=logging.DEBUG)

# For specific modules
logging.getLogger('mm').setLevel(logging.DEBUG)
logging.getLogger('mxstream').setLevel(logging.DEBUG)
```

### Trace Execution

```python
# Add trace to function
import traceback

def debugged_function():
    try:
        # code
        pass
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        raise
```

### Profile Performance

```python
# Simple timing
import time

start = time.time()
# code
print(f"Time: {time.time() - start:.2f}s")

# Detailed profiling
import cProfile
cProfile.run('function()', 'profile.stats')

import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
```

---

## Common Workarounds

### NPU Issues

```bash
# Kill stuck processes
pkill -f python
pkill -f mm_
pkill -f mxstream

# Clear NPU memory
npu-smi -r

# Restart NPU services
systemctl restart ascend-npu-driver
```

### Port Conflicts

```bash
# Find process using port
lsof -i :<port>
# or
netstat -tlnp | grep <port>

# Kill process
kill -9 <pid>

# Use different port
export MASTER_PORT=29501
```

---

## Health Checks

### System Health

```bash
#!/bin/bash
echo "=== System Health Check ==="

# Disk space
df -h | grep -E 'Filesystem|/dev/'

# Memory
free -h

# NPU
npu-smi info

# Network
ping -c 1 google.com &>/dev/null && echo "Internet: OK" || echo "Internet: FAIL"

# Python
python --version
pip list | wc -l
```

### NPU Health

```bash
#!/bin/bash
echo "=== NPU Health Check ==="

# NPU devices
npu-smi list

# NPU memory
npu-smi info -q -d memory

# CANN version
npu-smi -v

# Check ACL
python -c "import acl; print('ACL OK')"
```

---

## Emergency Procedures

### Complete Reset

```bash
# 1. Kill all related processes
pkill -f python
pkill -f mm_
pkill -f mxstream
pkill -f ray

# 2. Clear caches
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
npu-smi -r

# 3. Clear temp files
rm -rf /tmp/ray/
rm -rf ~/.cache/torch/

# 4. Restart NPU services
systemctl restart ascend-npu-driver

# 5. Reinstall if needed
pip uninstall multimodalsdk -y
pip install multimodalsdk
```

### Data Recovery

```bash
# Find latest checkpoint
ls -lt checkpoints/ | head -5

# Backup current state
cp -r current_run/ backup_$(date +%Y%m%d_%H%M%S)/

# Resume from checkpoint
python train.py --resume checkpoints/latest/
```
