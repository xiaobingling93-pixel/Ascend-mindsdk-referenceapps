---
name: agent-perf-analyzer
description: |
  Analyze AgentSDK/Agentic RL codebases for precision and performance issues on Ascend NPU.
  Use when users want to: diagnose training/inference precision problems (NaN, overflow, dtype mismatches) on NPU,
  identify performance bottlenecks (memory, latency, throughput), optimize model training speed on Ascend,
  debug memory issues, or get solutions for common AgentSDK performance/precision problems.
  This skill is specifically designed for Ascend NPU (Ascend 910/910B/910C) and CANN framework.
  This skill works standalone - no dependency on the main AgentSDK repository required.
---

# Agent Performance & Precision Analyzer (Ascend NPU Edition)

A standalone skill for analyzing AgentSDK and Agentic RL codebases to identify precision issues,
performance bottlenecks, and provide actionable solutions, specifically optimized for Ascend NPU.

## When to Use This Skill

Use this skill when the user mentions:
- "NPU", "Ascend", "CANN" - hardware platform
- "precision problem", "NaN", "overflow", "underflow", "dtype mismatch" on NPU
- "slow", "bottleneck", "performance issue", "memory leak" on Ascend
- "optimize training", "speed up inference", "reduce latency" on NPU
- "AgentSDK performance", "GRPO training slow" on Ascend NPU
- "torch.npu", "NPU backend" - NPU-specific APIs
- Any combination of precision + performance + Ascend NPU

---

## Ascend NPU Context

### Hardware & Software Stack

| Component | Description |
|-----------|-------------|
| **Hardware** | Ascend 910, 910B, 910C AI Accelerator |
| **Framework** | torch_npu (Ascend Extension for PyTorch) |
| **Compiler** | CANN (Compute Architecture for Neural Networks) |
| **Backend** | DaVinci Compiler |

### Key NPU Equivalents

| CUDA | Ascend NPU | Notes |
|------|------------|-------|
| `torch.cuda` | `torch.npu` | Device management |
| `.cuda()` | `.npu()` | Tensor device transfer |
| `torch.cuda.set_device()` | `torch.npu.set_device()` | Set NPU device |
| `torch.cuda.memory_allocated()` | `torch.npu.memory_allocated()` | Memory stats |
| `torch.cuda.empty_cache()` | `torch.npu.empty_cache()` | Clear cache |
| `torch.amp.autocast('cuda')` | `torch.amp.autocast('npu')` | Mixed precision |
| `torch.amp.GradScaler('cuda')` | `torch.amp.GradScaler('npu')` | Gradient scaling |
| `torch.cuda.amp.autocast` | `torch.npu.amp.autocast` | NPU AMP |

---

## Analysis Workflow

### Step 1: Scope Definition

Before analysis, determine with user:
1. **Target path**: Which code to analyze (local path or repo)
2. **Focus areas**: Precision, Performance, or Both
3. **Output format**: Console, JSON report, or Markdown
4. **Target audience**: Developer (detailed) or User (summary)

### Step 2: Precision Analysis (NPU Optimized)

Run precision diagnostics:
```bash
python -m scripts.analyze_precision <target_path> [--output report.json]
```

**What it checks (NPU-specific):**
| Check | Description | Impact |
|-------|-------------|--------|
| Dtype Consistency | BF16/FP16/FP32 NPU usage | High |
| NPU API Usage | torch.npu vs torch.cuda | High |
| Float64→Float32 Conversion | Explicit downcasting on NPU | High |
| Numerical Stability | Epsilon, NaN checks for NPU | High |
| Mixed Precision (NPU) | torch.amp.autocast('npu') | Medium |
| Gradient Clipping | NPU-appropriate thresholds | Medium |

**Common Precision Issues on NPU:**

| Issue | File Pattern | NPU Solution |
|-------|--------------|--------------|
| float64→float32 without guard | compute_utils.py | Use torch.amp.autocast('npu') |
| Hardcoded epsilon=1e-6 | Normalization ops | Make configurable |
| No NaN/Inf detection | Loss computation | Add torch.isfinite() checks |
| BF16 without AMP | Training loop | Use torch.npu.amp.autocast |
| Mismatched dtype | Various | Match model weight dtype to NPU |
| Using CUDA APIs | Legacy code | Replace with torch.npu equivalents |

### Step 3: Performance Profiling (NPU Optimized)

Run performance diagnostics:
```bash
python -m scripts.analyze_performance <target_path> [--output report.json]
```

**What it checks (NPU-specific):**

| Category | Checks | Impact |
|----------|--------|--------|
| Memory | NPU memory management, CPU copies, GC | High |
| NPU Inference | CANN optimization, batching | High |
| Data Loading | Padding efficiency, prefetch | Medium |
| Communication | HCCL (NPU collective), Ray | High |
| Training Loop | NPU-specific optimizations | Medium |

**NPU Performance Patterns:**

| Pattern | Location | Fix |
|---------|----------|-----|
| Blocking ray.get() in loop | trainer/*.py | Use async/await or batch |
| torch.empty_like for CPU copy | memory_manager.py | Use NPU memory pooling |
| Using CUDA APIs | Legacy code | Replace with torch.npu |
| No torch.npu.empty_cache() | NPU ops | Add cache clearing |
| Sequential worker init | vllm_async_server.py | Use HCCL for NPU init |
| No torch.no_grad() | CPU/NPU offload | Add context manager |

### Step 4: Solution Generation

Generate actionable fixes:
```bash
python -m scripts.generate_solutions <analysis_report.json> [--output fixes.md]
```

**Solution Categories:**

1. **Quick Wins** (< 5 min):
   - Add torch.no_grad() contexts
   - Replace torch.cuda with torch.npu
   - Enable gradient checkpointing
   - Configure proper batch sizes

2. **Medium Effort** (15-60 min):
   - Implement NPU memory pooling
   - Add HCCL collective communication
   - Optimize data loading pipeline
   - Configure proper dtype handling

3. **Architectural Changes** (hours):
   - Replace serialization format
   - Implement CANN optimization
   - Add profiling infrastructure
   - Redesign training loop

---

## Standalone Execution

This skill is fully self-contained:

### Installation
```bash
# NPU dependencies
pip install torch torch-npu

# Verify NPU availability
python -c "import torch; print(torch.npu.is_available())"
```

### Usage Without AgentSDK
```python
from scripts.analyze_precision import PrecisionAnalyzer
from scripts.analyze_performance import PerformanceAnalyzer

# Analyze local code
analyzer = PrecisionAnalyzer("/path/to/your/code")
report = analyzer.run()
print(report.summary)
```

### Integration Points

The skill provides these integration hooks:

1. **Pre-commit Hook** (for CI/CD):
   ```bash
   python -m scripts.quick_check /path/to/code --fail-on-error
   ```

2. **Build Verification**:
   ```bash
   python -m scripts.verify_perf /path/to/build --threshold 1.5x
   ```

3. **Report Generation**:
   ```bash
   python -m scripts.generate_report analysis.json --format html
   ```

---

## Output Format

### Precision Report (JSON)
```json
{
  "summary": {
    "issues_found": 5,
    "critical": 2,
    "warnings": 3
  },
  "issues": [
    {
      "severity": "critical",
      "category": "npu_api_usage",
      "file": "compute_utils.py",
      "line": 56,
      "description": "Using torch.cuda instead of torch.npu",
      "suggestion": "Replace .cuda() with .npu() for Ascend NPU"
    }
  ]
}
```

### Performance Report (JSON)
```json
{
  "summary": {
    "bottlenecks": 8,
    "high_impact": 3,
    "estimated_speedup": "2.3x"
  },
  "bottlenecks": [
    {
      "severity": "high",
      "category": "memory",
      "location": "memory_manager.py:150",
      "description": "Full NPU model copy without pooling",
      "fix": "Implement NPU buffer reuse pool"
    }
  ]
}
```

---

## NPU-Specific Solutions Reference

### Device Management

```python
# Before (CUDA)
device = torch.device('cuda:0')
tensor = tensor.cuda()

# After (NPU)
device = torch.device('npu:0')
tensor = tensor.npu()
```

### Mixed Precision (NPU)

```python
# Before (CUDA AMP)
with torch.cuda.amp.autocast():
    output = model(input)

scaler = torch.cuda.amp.GradScaler('cuda')
scaler.scale(loss).backward()

# After (NPU AMP)
with torch.npu.amp.autocast():
    output = model(input)

scaler = torch.npu.amp.GradScaler('npu')
scaler.scale(loss).backward()
```

### Memory Management (NPU)

```python
# Before (CUDA)
torch.cuda.empty_cache()
mem = torch.cuda.memory_allocated()

# After (NPU)
torch.npu.empty_cache()
mem = torch.npu.memory_allocated()
```

### NPU-Specific Optimizer

```python
# NPU fused optimizer (faster)
from torch_npu.optim import NPUFusedAdam
optimizer = NPUFusedAdam(model.parameters())
```

---

## Debugging Commands (NPU)

### NPU Debugging
```bash
# Check NPU availability
python -c "import torch; print(torch.npu.is_available())"

# Check NPU device info
python -c "import torch; print(torch.npu.get_device_name(0))"

# Monitor NPU memory
python -c "import torch; print(torch.npu.memory_allocated())"

# Enable NPU anomaly detection
torch.autograd.set_detect_anomaly(True)
```

### CANN Profiling
```bash
# Use msprof for NPU profiling
msprof --export --output ./profile ...

# NPU smi for hardware monitoring
npu-smi info
npu-smi monitor
```

---

## Integration with Development Workflow

### 1. Development Phase
- Use quick_check before commits
- Run full analysis weekly
- Verify NPU API compatibility

### 2. Testing Phase
- Include NPU perf benchmarks in CI
- Verify precision stability on NPU

### 3. Production Phase
- Monitor NPU metrics in production
- Use CANN optimization tools

---

## Exit Criteria

Analysis is complete when:
1. All target files scanned
2. NPU-specific precision issues identified and categorized
3. Performance bottlenecks ranked by impact (NPU context)
4. Solutions generated with NPU-specific recommendations
5. Report delivered in requested format

The skill should never modify user code without explicit permission - always generate reports and suggestions for human review.
