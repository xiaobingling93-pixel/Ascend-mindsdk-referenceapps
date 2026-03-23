# AgentSDK Precision & Performance Reference (Ascend NPU Edition)

## NPU Hardware & Software Stack

| Component | Description |
|-----------|-------------|
| **Hardware** | Ascend 910, 910B, 910C AI Accelerator |
| **Framework** | torch_npu (Ascend Extension for PyTorch) |
| **Compiler** | CANN (Compute Architecture for Neural Networks) |
| **Backend** | DaVinci Compiler |

---

## NPU API Quick Reference

### Device Management

| CUDA | Ascend NPU |
|------|------------|
| `torch.cuda` | `torch.npu` |
| `.cuda()` | `.npu()` |
| `torch.cuda.set_device(0)` | `torch.npu.set_device(0)` |
| `torch.cuda.device_count()` | `torch.npu.device_count()` |
| `torch.cuda.current_device()` | `torch.npu.current_device()` |
| `torch.cuda.get_device_name(0)` | `torch.npu.get_device_name(0)` |

### Memory Management

| CUDA | Ascend NPU |
|------|------------|
| `torch.cuda.memory_allocated()` | `torch.npu.memory_allocated()` |
| `torch.cuda.memory_reserved()` | `torch.npu.memory_reserved()` |
| `torch.cuda.empty_cache()` | `torch.npu.empty_cache()` |
| `torch.cuda.memory_summary()` | `torch.npu.memory_summary()` |

### Mixed Precision (AMP)

| CUDA | Ascend NPU |
|------|------------|
| `torch.cuda.amp.autocast` | `torch.npu.amp.autocast` |
| `torch.cuda.amp.GradScaler('cuda')` | `torch.npu.amp.GradScaler('npu')` |

---

## Precision Guide

### Data Types

| Type | Precision | Speed | Use Case |
|------|-----------|-------|----------|
| FP32 | 32-bit | Baseline | Default, stable |
| FP16 | 16-bit | 2x | Memory limited, fast |
| BF16 | Brain Float | 2x | **NPU recommended**, stable |

### BF16 vs FP16 on NPU

| Feature | BF16 | FP16 |
|---------|------|------|
| Range | Wider | Narrower |
| NPU Support | Native | Emulated |
| Stability | More stable | Can overflow |
| Recommendation | **Preferred** | Use with GradScaler |

### Common Precision Issues

#### 1. NaN in Loss
**Symptoms:** Training loss becomes NaN
**Solutions:**
```python
# Gradient clipping
torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

# Finite check
if torch.isfinite(loss).all():
    loss.backward()

# NPU GradScaler
scaler = torch.npu.amp.GradScaler('npu')
scaler.scale(loss).backward()
scaler.step(optimizer)
scaler.update()
```

#### 2. Overflow
**Symptoms:** Loss = inf or very large values
**Solutions:**
```python
# Clamp rewards
rewards = torch.clamp(rewards, min=-1e6, max=1e6)

# NPU AMP
with torch.npu.amp.autocast():
    accumulated_loss = loss.float()
```

---

## Performance Guide

### NPU Memory Optimization

#### 1. CPU-NPU Transfer
**Before:**
```python
cpu_params = [p.cpu() for p in model.parameters()]
```
**After:**
```python
with torch.no_grad():
    cpu_params = [p.cpu() for p in model.parameters()]
```
**Impact:** 10-15% memory reduction

#### 2. Memory Pooling
**Before:**
```python
for _ in range(num_batches):
    buffer = torch.empty(batch_size, hidden_size, device='npu')
```
**After:**
```python
buffer_pool = [torch.empty(batch_size, hidden_size, device='npu') 
              for _ in range(pool_size)]
```
**Impact:** 30-50% memory reduction

#### 3. NPU Cache Clearing
```python
# Clear NPU cache after large operations
torch.npu.empty_cache()
```

### NPU Inference Optimization

#### 1. NPU-Fused Optimizers
```python
# Use NPU fused optimizer (faster)
from torch_npu.optim import NPUFusedAdam
optimizer = NPUFusedAdam(model.parameters())
```

#### 2. CANN Optimization
```bash
# Use CANN profiling
msprof --export --output ./profile ...
```

### NPU Data Loading

#### 1. Batch Padding
**Before:**
```python
padded = []
for sample in batch:
    padded.append(pad_sequence(sample))
```
**After:**
```python
padded = torch.nn.utils.rnn.pad_sequence(
    batch, batch_first=True, padding_value=0
)
```

#### 2. Prefetch
```python
loader = DataLoader(
    dataset, 
    batch_size=32,
    num_workers=4,
    prefetch_factor=2
)
```

---

## Debugging Commands

### NPU Debugging
```bash
# Check NPU availability
python -c "import torch; print(torch.npu.is_available())"

# Check NPU device info
python -c "import torch; print(torch.npu.get_device_name(0))"

# Monitor NPU memory
python -c "import torch; print(torch.npu.memory_allocated())"

# Enable anomaly detection
torch.autograd.set_detect_anomaly(True)
```

### CANN Profiling
```bash
# NPU profiling
msprof --export --output ./profile ...

# Hardware monitoring
npu-smi info
npu-smi monitor
```

---

## Configuration Best Practices

### Training Config (NPU)
```yaml
training:
  dtype: bfloat16
  gradient_clip: 1.0
  amp:
    enabled: true
    device_type: npu
    init_scale: 65536
  
memory:
  offload_optimizer: false
  offload_grad: false
  gradient_checkpointing: true
```

### Inference Config (NPU)
```yaml
inference:
  dtype: bfloat16
  batch_size: 32
  max_num_seqs: 64
  
performance:
  kv_cache_dtype: bfloat16
  npu_memory_utilization: 0.9
```

---

## Common Pitfalls

1. **CUDA vs NPU**: Always use `torch.npu` instead of `torch.cuda`
2. **Mixed dtype**: Ensure tensors have matching dtypes
3. **Blocking in loops**: Batch operations outside loops
4. **Unnecessary gradient tracking**: Use torch.no_grad() for inference
5. **Inefficient padding**: Use vectorized operations
6. **No memory reuse**: Implement pooling for frequently created tensors
7. **Missing NPU AMP**: Enable torch.npu.amp.autocast for BF16 training

---

## Performance Checklist

- [ ] Use BF16 for NPU training (recommended)
- [ ] Enable torch.npu.amp.GradScaler
- [ ] Add gradient clipping (1.0 for BF16)
- [ ] Use torch.no_grad() for CPU/NPU transfers
- [ ] Replace torch.cuda with torch.npu APIs
- [ ] Enable DataLoader prefetch
- [ ] Use vectorized padding
- [ ] Implement memory pooling
- [ ] Use NPU fused optimizers (NPUFusedAdam)
- [ ] Profile with CANN msprof
