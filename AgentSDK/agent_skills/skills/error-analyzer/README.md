# Error Analyzer - Ascend NPU

A unified error analysis skill for Ascend NPU hardware scenarios. This skill analyzes user-provided error information to identify root causes and generate customer-friendly responses.

## Overview

**Error Analyzer - Ascend NPU** is a comprehensive skill that merges three specialized error analyzers:
- error-analyzer-Agent (AgentSDK)
- error-analyzer-multimodal (MultimodalSDK)
- error-analyzer-vision (Vision SDK)

This unified skill supports multiple Ascend NPU-related SDKs and frameworks, making it versatile for various error analysis scenarios.

## Features

- **Multi-SDK Support**: Works with MultimodalSDK, Vision SDK, MindSpeed, CANN, and more
- **NPU-Specific Analysis**: Specialized patterns for Ascend NPU hardware errors
- **Repository-Aware**: Can search provided repository paths for source code context
- **Self-Contained**: Works independently without project dependencies
- **Customer-Friendly**: Generates clear, actionable responses

## Independence

This skill is completely self-contained:
- **Zero dependencies**: Only requires Python 3.7+
- **Run anywhere**: Works in any directory
- **Cross-platform**: Linux, macOS, Windows

## Installation and Usage

### Quick Start

```bash
# Enter skill directory
cd /path/to/error-analyzer-ascend/

# Parse an error log
python scripts/parse_error.py --file error.log --output json

# Analyze with repository context
python scripts/analyze_error.py \
  --error-log error.log \
  --repo-path /path/to/repository \
  --output markdown
```

### Input Format

Provide error information in this format:

```
## Error Information
[Error message / log / stack trace]

## Environment
[OS, version, CANN version, library versions, NPU info]

## Context
[What were you trying to do?]

## Repository Path (optional)
[Path to repository for source code reference]
```

## Directory Structure

```
error-analyzer-ascend/
├── SKILL.md                    # Skill definition and usage guide
├── README.md                   # This file
├── scripts/                    # Executable scripts
│   ├── __init__.py
│   ├── parse_error.py          # Error log parser
│   └── analyze_error.py        # Advanced error analyzer
└── references/                 # Reference documents
    ├── error-patterns.md       # Known error patterns
    ├── sdk-knowledge.md        # Ascend NPU SDK knowledge
    ├── response-templates.md   # Response templates
    ├── debugging-checklist.md  # Debugging methodology
    ├── examples.md             # Analysis examples
    └── solutions.md            # Common solutions
```

## Supported Error Types

### NPU/Ascend Specific
- NPU out of memory
- CANN import errors
- ACL errors
- NPU initialization failures
- Device not found

### SDK-Specific
- MultimodalSDK errors (mm.*)
- Vision SDK errors (mxvision, mxstream)
- MindSpeed errors

### General
- Network/Distributed errors
- Memory errors
- Configuration errors
- Permission errors

## Example Usage

### Example 1: NPU Memory Error

```bash
python scripts/parse_error.py "NPU out of memory. Tried to allocate 2GB"
```

Output:
```json
{
  "error_type": "RuntimeError",
  "error_message": "NPU out of memory. Tried to allocate 2GB",
  "categories": ["npu", "memory"],
  "npu_specific": true
}
```

### Example 2: Full Analysis

```bash
python scripts/analyze_error.py \
  --error-log error.log \
  --repo-path /path/to/MultimodalSDK \
  --output markdown
```

## References

- `SKILL.md` - Complete skill definition and workflow
- `references/error-patterns.md` - Known error pattern library
- `references/sdk-knowledge.md` - Ascend NPU SDK documentation
- `references/solutions.md` - Common solutions and workarounds

## License

This skill follows the Mulan PSL v2 license.

## Version

- **Version**: 1.0.0
- **Created**: 2026-03-17
- **Python Support**: 3.7+
