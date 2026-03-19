# Debugging Checklist

A systematic approach to analyzing errors in Ascend NPU scenarios.

## Phase 1: Information Gathering

### 1.1 Error Identification
- [ ] Extract the exact error message
- [ ] Note error code (if applicable)
- [ ] Identify the component where error occurred
- [ ] Note timestamp of error

### 1.2 Environment Capture
- [ ] Operating system and version
- [ ] CANN version: `npu-smi -v`
- [ ] Python version
- [ ] SDK/library versions involved
- [ ] NPU device info: `npu-smi info`
- [ ] Hardware configuration

### 1.3 Context Collection
- [ ] What operation was being performed
- [ ] Steps to reproduce (if known)
- [ ] Recent changes (updates, config changes)
- [ ] Log files (relevant sections)

## Phase 2: Initial Analysis

### 2.1 Error Classification
- [ ] Is this a known error pattern?
- [ ] Is this NPU-specific? (check CANN, ACL, NPU keywords)
- [ ] Is this a new/unexpected error?
- [ ] Category: NPU, Memory, Network, Configuration, etc.

### 2.2 Version Check
- [ ] Check CANN version compatibility
- [ ] Check SDK version matches requirements
- [ ] Check dependency versions
- [ ] Check for known issues in version

### 2.3 Log Analysis
- [ ] Review application logs
- [ ] Review system logs: `dmesg | tail`
- [ ] Review NPU logs
- [ ] Look for warnings before the error
- [ ] Check for patterns in repeated errors

## Phase 3: Root Cause Determination

### 3.1 Hypothesis Formation
Based on analysis, form hypotheses:
- Hypothesis 1: [Most likely cause]
- Hypothesis 2: [Alternative cause]
- Hypothesis 3: [Less likely but possible]

### 3.2 Hypothesis Testing
- [ ] Test hypothesis 1
- [ ] Test hypothesis 2 if needed
- [ ] Document findings

### 3.3 Root Cause Confirmation
- [ ] Can the error be reproduced?
- [ ] Does fixing the root cause resolve the error?
- [ ] Are there any side effects?

## Phase 4: Resolution

### 4.1 Solution Development
- [ ] Permanent fix identified
- [ ] Workaround (if no permanent fix)
- [ ] Prevention measures

### 4.2 Verification
- [ ] Test the fix in similar environment
- [ ] Verify no regression
- [ ] Document the resolution

## Phase 5: Communication

### 5.1 Response Preparation
- [ ] Clear problem statement
- [ ] Root cause explanation (user-appropriate language)
- [ ] Step-by-step solution
- [ ] Prevention tips (if applicable)

### 5.2 Follow-up
- [ ] Confirm resolution with user
- [ ] Document for future reference
- [ ] Update knowledge base if applicable

## Quick Reference: NPU Diagnostic Commands

```bash
# Basic NPU info
npu-smi info

# Detailed NPU info
npu-smi info -q

# NPU memory
npu-smi info -q -d memory

# List devices
npu-smi list

# Monitor usage
npu-smi dmon -c 1

# Process info
npu-smi top

# Clear cache
npu-smi -r
```

## Quick Reference: Common Root Causes

| Error Type | Common Root Causes |
|------------|-------------------|
| NPU startup failures | Driver not loaded, CANN not installed, device busy |
| NPU runtime errors | Memory exhaustion, CANN version mismatch, device error |
| MultimodalSDK errors | Input format not supported, CANN not initialized |
| Vision SDK errors | Pipeline misconfiguration, missing dependencies |
| Startup failures | Missing deps, wrong permissions, config errors |
| Runtime crashes | Memory issues, null pointers, race conditions |
| Performance issues | Resource exhaustion, inefficient algorithms |
| Intermittent issues | Timing, race conditions, external dependencies |
| Data issues | Encoding, corruption, migration problems |

## Decision Tree

```
Error occurs
    │
    ├─► NPU-specific error?
    │       ├─► Yes → Check CANN status, npu-smi output
    │       └─► No → Continue
    │
    ├─► Known error pattern?
    │       ├─► Yes → Apply known solution
    │       └─► No → Continue
    │
    ├─► Version info available?
    │       ├─► Yes → Check compatibility matrix
    │       └─► No → Request version info
    │
    ├─► Can reproduce?
    │       ├─► Yes → Debug with logs/trace
    │       └─► No → Analyze logs for patterns
    │
    └─► Root cause found?
            ├─► Yes → Apply fix
            └─► No → Escalate with full context
```
