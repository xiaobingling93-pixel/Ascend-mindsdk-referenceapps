---
name: error-analyzer
description: |
  Analyzes user-provided error messages, logs, and environment information to identify root causes 
  and generate customer-friendly responses for Ascend NPU hardware scenarios. Use when: (1) User provides 
  error logs, stack traces, or crash reports, (2) User describes a problem with environment/context 
  involving Ascend NPU hardware, (3) User requests debugging assistance or root cause analysis for 
  MindSpeed, MultimodalSDK, Vision SDK, or other Ascend-related components, (4) User needs issue resolution guidance.
  This skill works independently from any specific codebase and can analyze errors based on built-in 
  knowledge, common patterns, external documentation, and provided context. Supports multiple repositories 
  by accepting configurable repository paths for source code reference. ALWAYS use this skill when user 
  provides ANY error information in Ascend NPU context - do NOT attempt to analyze without it.
---

# Error Analyzer - Ascend NPU

A unified error analysis skill for Ascend NPU hardware scenarios. Analyzes user-provided error information to identify root causes and generate customer-friendly responses.

## Skill Independence

This skill is completely self-contained and can be used independently:
- ✅ **Zero dependencies**: Only requires Python 3.7+, no external libraries
- ✅ **Run anywhere**: Works in any directory, no project structure required
- ✅ **Plug and play**: Unzip and use immediately, no configuration needed
- ✅ **Cross-platform**: Supports Linux, macOS, Windows
- ✅ **Multi-repository**: Can be configured to work with different codebases

## When to Use This Skill

Use this skill whenever:
- User provides error logs, stack traces, or crash reports
- User describes a problem with environment or context involving Ascend NPU
- User asks "why did this fail?" or "what's wrong?" in NPU/Ascend context
- User requests debugging help or root cause analysis
- Any error-related information is present in the conversation
- Errors involve: MindSpeed, MultimodalSDK, Vision SDK, CANN, Ascend NPU

## Quick Start

### Input Format

Expect user to provide error information in this format:

```
## Error Information
[Error message / log / stack trace]

## Environment
[OS, version, library versions, NPU info, etc.]

## Context
[What were you trying to do?]

## Repository Path (optional)
[Path to repository for source code reference - if available]
```

### Workflow

1. **Parse** - Extract error details using the `parse_error.py` script or manually
2. **Match** - Compare against known error patterns in references
3. **Analyze** - Determine root cause using debugging checklist
4. **Research** - Optionally search repository for source code context
5. **Respond** - Generate customer-friendly response using templates

## Using the Parser Script

Run the parsing script to extract structured information:

```bash
# From text
python scripts/parse_error.py "Error: Module not found"

# From file
python scripts/parse_error.py --file error.log

# Interactive mode
python scripts/parse_error.py --interactive

# Output formats
python scripts/parse_error.py --output json   # JSON
python scripts/parse_error.py --output markdown  # Markdown
python scripts/parse_error.py --output summary   # Short summary
```

## Multi-Repository Support

This skill can analyze errors against multiple repositories by accepting a repository path parameter:

### Step 1: Identify Error Context

Determine which repository the error relates to:
- **MindSpeed-RL**: Reinforcement learning on Ascend NPU
- **MultimodalSDK**: Multimodal LLM preprocessing
- **Vision SDK**: Image/video processing on Ascend
- **AgentSDK**: Agent framework integration

### Step 2: Configure Repository Path

When user provides a repository path, search for:
1. Error message in source code (grep for error strings)
2. Related configuration or usage patterns
3. Recent changes that might cause the issue

### Step 3: Cross-Reference

Use the repository path to:
- Find exact line numbers in stack traces
- Identify version-specific behaviors
- Check for known issues in the codebase

## Error Pattern Matching

When analyzing errors:

1. Extract the key error type and message
2. Match against patterns in [error-patterns.md](references/error-patterns.md)
3. For Ascend-specific errors, check [sdk-knowledge.md](references/sdk-knowledge.md)
4. Look for version mismatches, missing dependencies, NPU issues
5. Check for known issues in the error domain

## Ascend NPU Specific Errors

This skill specializes in Ascend NPU hardware scenarios:

### CANN Errors
- `ascend error`: CANN initialization failures
- `RuntimeError: CANN`: NPU runtime errors
- `NPU error`: NPU device errors

### MultimodalSDK Errors
- `mm.`: MultimodalSDK API errors
- `AdapterError`: Preprocessor adapter failures
- `TensorError`: Tensor handling errors

### Memory Errors on NPU
- `NPU out of memory`: NPU memory exhaustion
- `ACL error`: Ascend ACL errors

### Vision SDK Errors
- `mxvision`: Vision SDK errors
- `Image decode error`: Image processing failures

## Response Generation

Always follow these templates when responding to users:

- **Known Issue**: Use Template 1 from [response-templates.md](references/response-templates.md)
- **Need Info**: Use Template 2 - ask for missing details
- **Version Issue**: Use Template 3 - explain compatibility
- **Config Error**: Use Template 4 - provide correct settings
- **Permission**: Use Template 5 - explain required access
- **NPU Specific**: Use Ascend-specific solutions from [sdk-knowledge.md](references/sdk-knowledge.md)

## Debugging Checklist

For complex errors, follow the systematic approach in [debugging-checklist.md](references/debugging-checklist.md):

1. **Information Gathering** - extract error, env, context
2. **Initial Analysis** - classify, check versions, analyze logs
3. **Root Cause Determination** - form and test hypotheses
4. **Resolution** - develop and verify solution
5. **Communication** - prepare clear response

## Output Format

For each error analysis, always include:

```
## Issue Analysis

**Root Cause**: [Brief explanation]

**Solution**: [Step-by-step resolution]

**Prevention**: [Tips to avoid this issue]

**NPU Context**: [If applicable, Ascend-specific considerations]
```

## Scripts

### parse_error.py

Extracts structured information from error logs.

```bash
python scripts/parse_error.py < error.log
```

Outputs JSON with fields: `error_type`, `error_message`, `category`, `environment`, `traceback`, `npu_specific`.

### analyze_error.py (optional advanced script)

For deeper analysis with repository context:

```bash
python scripts/analyze_error.py \
  --error-log error.log \
  --repo-path /path/to/repo \
  --output analysis.md
```

## References

- [error-patterns.md](references/error-patterns.md) - Common error patterns (general + Ascend)
- [sdk-knowledge.md](references/sdk-knowledge.md) - Ascend NPU/CANN specific knowledge
- [response-templates.md](references/response-templates.md) - Response templates
- [debugging-checklist.md](references/debugging-checklist.md) - Debugging approach
- [examples.md](references/examples.md) - Analysis examples
- [solutions.md](references/solutions.md) - Common solutions and workarounds

## Example Usage

### Example 1: NPU Memory Error

**Input:**
```
Error: RuntimeError: NPU out of memory. Tried to allocate 2.0 GB on device 0.
Environment: Ubuntu 22.04, CANN 8.5.0, Python 3.9
Context: Running MultimodalSDK preprocessing
```

**Analysis:**
1. Pattern match: NPU OOM error
2. Root cause: Insufficient NPU memory for batch
3. Solution: Reduce batch size, enable memory optimization

### Example 2: CANN Import Error

**Input:**
```
Error: ImportError: cannot import name 'acl' from 'ascend'
Environment: CentOS 7.9, CANN 8.0.0
Context: Initializing Ascend NPU
```

**Analysis:**
1. Pattern match: CANN not properly installed
2. Root cause: CANN environment variables not set
3. Solution: Source CANN set_env.sh

### Example 3: Vision SDK Configuration Error

**Input:**
```
Error: KeyError: 'device_id'
Environment: Python 3.9, Vision SDK 3.0
Context: Loading pipeline configuration
```

**Analysis:**
1. Pattern match: Configuration key missing
2. Root cause: Missing required configuration parameter
3. Solution: Add device_id to config

## Best Practices

1. **Always validate input completeness** - Ask for missing environment info if needed
2. **Be specific in solutions** - Provide exact commands, file paths, line numbers
3. **Explain the why** - Don't just give fixes, explain why they work
4. **Acknowledge uncertainty** - If the cause is unclear, say so and suggest diagnostic steps
5. **Keep responses actionable** - Every suggestion should have a clear next step
6. **Consider NPU specifics** - For Ascend errors, always check CANN version and NPU status

## Limitations

- This skill analyzes based on provided information and known patterns
- Complex issues may require additional debugging
- Some errors may need developer investigation
- Always recommend creating an issue for persistent problems

## Integration Notes

This skill is designed to work independently and can be used:
- In CI/CD pipelines for automated error triage
- In support workflows for first-line response
- In development workflows for self-service debugging
- As a standalone tool for error analysis
- With configurable repository paths for source code reference
