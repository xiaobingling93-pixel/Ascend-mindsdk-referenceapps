---
name: multimodal-competitor-analysis
description: |
  Analyze competitor multimodal preprocessing capabilities, identify user pain points, 
  compare with current MultimodalSDK (Ascend) capabilities, provide NPU migration plans, 
  and perform tool quantity analysis. Use this skill when users want to:
  - Understand competitor preprocessing solutions (NVIDIA DALI, OpenCV CUDA, etc.)
  - Compare their current pipeline with Ascend MultimodalSDK capabilities
  - Plan migration from GPU/CPU preprocessing to NPU (Ascend)
  - Analyze tool/operator count differences between implementations
  - Identify gaps and provide migration recommendations
  This skill is independent and decoupled from the main repository - it uses external research
  and standalone analysis methods.
---

# Multimodal Preprocessing Competitor Analysis Skill

## Purpose

This skill provides comprehensive analysis of multimodal preprocessing capabilities, comparing competitor solutions with Ascend's MultimodalSDK. It helps users understand:
1. What competitors (NVIDIA DALI, OpenCV, etc.) offer
2. Current MultimodalSDK capabilities and gaps
3. User pain points in preprocessing pipelines
4. NPU migration strategies
5. Tool/operator quantity analysis for migration planning

## Research Methodology

### Step 1: Understand User's Current Setup

Ask the user to provide:
- **Current preprocessing pipeline**: What library/framework do they currently use? (e.g., NVIDIA DALI, torchvision, OpenCV, custom)
- **Target models**: Which multimodal models are they using? (e.g., Qwen2VL, InternVL2, LLaVA, etc.)
- **Hardware**: Current accelerator (GPU model, CPU, NPU type)
- **Pain points**: What issues are they facing? (performance, cost, compatibility, etc.)

### Step 2: Competitor Analysis (Use Librarian Agent)

For competitor research, invoke librarian agent with:
```
Research [competitor name] multimodal preprocessing capabilities:
- Image decoding, resizing, cropping operations
- Video decoding and frame extraction  
- Tensor conversion and normalization
- Model-specific preprocessing support
- Hardware acceleration support (GPU, NPU)
- Performance characteristics
```

**Key Competitors to Research:**
1. **NVIDIA DALI** - GPU-focused data pipeline
2. **OpenCV CUDA/GPU** - Traditional computer vision library
3. **torchvision** - PyTorch's native preprocessing
4. **Decord** - Video reading library
5. **TVM/Relay** - Compiler-based preprocessing
6. **Qualcomm QNN** - Mobile NPU preprocessing
7. **MediaTek NeuroPilot** - Mobile NPU preprocessing

### Step 3: Current MultimodalSDK Capabilities Analysis

Reference the following capability matrix (from Ascend MultimodalSDK documentation):

| Category | Capability | Status | Notes |
|----------|------------|--------|-------|
| **Image Loading** | Image.open(path, device) | ✅ Supported | CPU device only currently |
| | Image.from_numpy() | ✅ Supported | Convert from numpy |
| | Image.from_torch() | ✅ Supported | Convert from PyTorch |
| | Image.from_pillow() | ✅ Supported | Convert from PIL |
| **Image Processing** | resize(size, interpolation) | ✅ Supported | BICUBIC, etc. |
| | crop(top, left, height, width) | ✅ Supported | Spatial crop |
| | to_tensor(format, device) | ✅ Supported | NCHW, NHWC formats |
| **Video Processing** | video_decode(file_path) | ✅ Supported | Video to image frames |
| **Tensor Operations** | normalize(tensor, mean, std) | ✅ Supported | Channel-wise normalize |
| **Model Adapters** | MultimodalQwen2VLImageProcessor | ✅ Supported | Qwen2VL preprocessing |
| | InternVL2PreProcessor | ✅ Supported | InternVL2 preprocessing |
| **Framework Integration** | vllm patcher | ✅ Supported | Video/image patching for vllm |

### Step 4: Gap Analysis Framework

For each competitor, identify gaps compared to MultimodalSDK:

```
## Gap Analysis Template

### [Competitor Name] vs MultimodalSDK

| Operation | Competitor | MultimodalSDK | Gap Severity | Migration Effort |
|-----------|------------|---------------|--------------|------------------|
| Image Decode | [Yes/No/Limited] | [Yes/No/Limited] | [High/Med/Low] | [High/Med/Low] |
| Resize | ... | ... | ... | ... |
| Crop | ... | ... | ... | ... |
| Video Decode | ... | ... | ... | ... |
| Normalize | ... | ... | ... | ... |
| Model-specific prep | ... | ... | ... | ... |
```

### Step 5: User Pain Point Categories

Common pain points to identify:

1. **Performance Issues**
   - Slow preprocessing bottlenecking inference
   - GPU utilization low during preprocessing
   - CPU preprocessing slowing down GPU inference

2. **Compatibility Issues**
   - Framework version conflicts
   - Model-specific preprocessing not optimized
   - Data format conversion overhead

3. **Cost Issues**
   - GPU expensive for preprocessing only
   - License costs for commercial solutions
   - Infrastructure costs

4. **NPU Migration Pain Points**
   - Lack of NPU-optimized preprocessing
   - Porting difficulty from GPU/CPU code
   - Performance uncertainty on NPU

## NPU Migration Planning

### Migration Strategy Framework

For users planning NPU migration, provide:

```
## NPU Migration Plan

### Phase 1: Assessment
- [ ] Inventory current preprocessing operators
- [ ] Identify NPU-supported operations
- [ ] Quantify performance requirements

### Phase 2: Mapping
| Original Operator | MultimodalSDK Equivalent | NPU Support | Effort |
|-------------------|-------------------------|-------------|--------|
| torch.nn.functional.resize | Image.resize() | ✅ | Low |
| torchvision.transforms.CenterCrop | Image.crop() | ✅ | Low |
| cv2.resize | Image.resize() | ✅ | Low |
| decord.VideoReader | video_decode() | ✅ | Low |
| ... | ... | ... | ... |

### Phase 3: Implementation
- Replace operators one-by-one
- Validate output correctness
- Benchmark performance

### Phase 4: Optimization
- Batch processing optimization
- Memory layout optimization
- NPU-specific tuning
```

### Common Migration Paths

| From | To | Complexity | Notes |
|------|-----|-----------|-------|
| torchvision transforms | MultimodalSDK Image class | Low | Direct API mapping |
| OpenCV CPU | MultimodalSDK Image class | Low | Similar API |
| NVIDIA DALI | MultimodalSDK + custom | Medium | Different paradigm |
| Custom PyTorch | MultimodalSDK Tensor | Medium | Need data conversion |

## Tool/Operator Quantity Analysis

### Analysis Framework

Help users understand the scope of migration by analyzing:

```
## Tool Quantity Analysis

### Current Pipeline Analysis
Count operators in user's current pipeline:
- Image decoding: ___ occurrences
- Resize operations: ___ occurrences
- Crop operations: ___ occurrences
- Normalize operations: ___ occurrences
- Format conversions: ___ occurrences
- Model-specific ops: ___ occurrences

### Total: ___ operators to migrate

### Migration Complexity Assessment
- Direct 1:1 mappings: ___ operators
- Requires refactoring: ___ operators
- No direct equivalent: ___ operators (need workarounds)
```

### Quantification Template

Provide a table showing operator-level analysis:

| Operator Type | Count in Pipeline | NPU Ready | Effort Estimate |
|---------------|------------------|-----------|-----------------|
| Decode | X | Yes/No | X person-days |
| Resize | X | Yes/No | X person-days |
| Crop | X | Yes/No | X person-days |
| ... | ... | ... | ... |
| **Total** | **X** | - | **X person-days** |

## Output Formats

### Competitor Analysis Report

Generate structured report:

```markdown
# Multimodal Preprocessing Competitor Analysis

## 1. Executive Summary
[High-level comparison and recommendations]

## 2. Competitor Capabilities
### 2.1 [Competitor 1]
- Capabilities: [...]
- Strengths: [...]
- Limitations: [...]
### 2.2 [Competitor 2]
- [...]

## 3. MultimodalSDK Position
### 3.1 Current Capabilities
[Capability matrix]
### 3.2 Gaps Identified
[Gaps vs competitors]

## 4. User Pain Point Analysis
### 4.1 Pain Points Identified
[Based on user's input]
### 4.2 Root Causes
[Analysis of why these pain points exist]

## 5. NPU Migration Plan
### 5.1 Assessment Results
### 5.2 Migration Path
### 5.3 Timeline Estimate
### 5.4 Risk Analysis

## 6. Tool Quantity Analysis
### 6.1 Operator Count
### 6.2 Complexity Breakdown
### 6.3 Resource Estimates
```

### Migration Roadmap

Provide actionable roadmap:

```markdown
## Recommended Migration Roadmap

### Immediate (Week 1-2)
- [ ] Replace image loading operations
- [ ] Replace basic transforms

### Short-term (Week 3-4)
- [ ] Replace video processing
- [ ] Implement model-specific preprocessing

### Medium-term (Month 2-3)
- [ ] Optimize for NPU
- [ ] Benchmark and tune

### Long-term (Month 4+)
- [ ] Full pipeline optimization
- [ ] Production deployment
```

## Key Considerations

### When to Recommend NPU Migration

Recommend NPU migration when:
1. User is already using Ascend NPU for inference
2. Cost optimization is critical (NPU vs GPU)
3. User needs offline deployment on Ascend devices
4. Power efficiency is important (edge deployment)

### When NOT to Recommend NPU Migration

Don't recommend when:
1. Current GPU solution meets performance needs
2. User needs features not yet supported on NPU
3. Migration cost exceeds expected benefits
4. Framework dependencies prevent easy migration

### Gap Severity Guidelines

| Severity | Definition | Action Required |
|----------|------------|-----------------|
| High | Core functionality missing | Prioritize development or use alternative |
| Medium | Feature incomplete | Workaround available, plan fix |
| Low | Minor difference | Accept or adapt |

## Quality Checks

Before delivering analysis, verify:
- [ ] All competitor capabilities researched
- [ ] MultimodalSDK capabilities accurately represented
- [ ] Pain points specifically tied to user's context
- [ ] Migration plan considers user's constraints
- [ ] Tool quantity analysis is actionable

## Skill Dependencies

This skill can operate independently but benefits from:
- **librarian agent**: For competitor research
- **web search**: For latest competitor updates
- **Documentation access**: For MultimodalSDK API details

This skill is designed to be **decoupled from any specific repository** - all analysis is based on:
1. External research (librarian)
2. General knowledge of MultimodalSDK capabilities
3. Framework-specific documentation
