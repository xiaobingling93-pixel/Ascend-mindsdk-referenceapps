# Response Templates

Templates for generating customer-friendly error responses.

## Template 1: Known Issue with Solution

```
## Issue Analysis

I've identified the problem you're experiencing.

**Root Cause**: [Brief explanation of why the error occurred]

**Solution**: [Step-by-step resolution]

[If applicable: **Workaround**: Temporary solution if fix not available]

**Prevention**: [Tips to avoid this issue in the future]
```

## Template 2: Need More Information

```
## Issue Analysis

I need additional information to pinpoint the exact cause:

- [ ] Exact error message (full text)
- [ ] Environment details (OS version, CANN version, library versions)
- [ ] Steps to reproduce
- [ ] Recent changes (updates, configuration changes)
- [ ] NPU device info (if applicable): output of `npu-smi info`

Please provide these details so I can assist you better.
```

## Template 3: Version Compatibility Issue

```
## Issue Analysis

This error is likely caused by a version mismatch.

**Root Cause**: [Component A] version [X] is incompatible with [Component B] version [Y]

**Solution Options**:

1. **Upgrade**: Update [Component A] to version [Z+]
2. **Downgrade**: Roll back [Component B] to version [Z-]
3. **Use compatible combination**: See version compatibility matrix

**Recommended**: [Option based on best practice]

**Version Check Commands**:
- CANN: `npu-smi -v`
- Python: `python --version`
- SDK: `pip show [package]`
```

## Template 4: Configuration Error

```
## Issue Analysis

The error indicates a configuration issue.

**Root Cause**: [Configuration item] is set incorrectly

**Solution**:

1. Check configuration file: [path]
2. Verify the following settings:
   - [Setting 1]: [Correct value]
   - [Setting 2]: [Correct value]
3. Restart the service

**Note**: Run [command] to validate your configuration.
```

## Template 5: Permission/Access Error

```
## Issue Analysis

The error indicates a permission or access issue.

**Root Cause**: [User/process] lacks necessary [permission/type] for [resource]

**Solution**:

1. Check current permissions: [command]
2. Fix permissions:
   - For file: `chmod [mode] [path]`
   - For directory: `chown [user]:[group] [path]`
3. Verify the fix

**Security Note**: Always follow least-privilege principle.
```

## Template 6: NPU-Specific Error

```
## Issue Analysis

This is an Ascend NPU-specific error.

**Root Cause**: [Explanation of NPU-related cause]

**NPU Diagnostic Steps**:

1. Check NPU status: `npu-smi info`
2. Check NPU memory: `npu-smi info -q -d memory`
3. Verify CANN installation: `source /usr/local/Ascend/ascend-toolkit/set_env.sh`

**Solution**: [Step-by-step resolution]

**Prevention**: [Tips to avoid this issue]
```

## Response Guidelines

1. **Be empathetic**: Acknowledge the user's frustration
2. **Be clear**: Use simple language, avoid jargon
3. **Be actionable**: Provide concrete steps, not just explanations
4. **Be complete**: Include all necessary information
5. **Be preventive**: Suggest how to avoid similar issues

## Tone

- Professional but friendly
- Confident when solution is certain
- Helpful when more information needed
- Clear about limitations or unknown factors
- Include NPU-specific diagnostics when relevant
