"""
Performance Analysis Module for AgentSDK/Agentic RL Codebases.

This module analyzes Python code for performance-related issues:
- Memory management (CPU copies, GC, caching)
- Inference optimization (serialization, async patterns)
- Data loading (padding, prefetch, tokenization)
- Communication overhead (Ray RPC patterns)
- Common anti-patterns
"""

import ast
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceIssue:
    """Represents a performance-related issue found in code."""
    severity: str  # high, medium, low
    category: str  # memory, inference, data_loading, communication, training_loop
    file: str
    line: int
    description: str
    suggestion: str
    estimated_impact: str = ""  # e.g., "20% memory reduction"
    code_snippet: str = ""


@dataclass
class PerformanceReport:
    """Complete performance analysis report."""
    summary: Dict[str, any] = field(default_factory=dict)
    bottlenecks: List[PerformanceIssue] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)
    patterns_found: Dict[str, int] = field(default_factory=dict)


class PerformanceAnalyzer:
    """Analyzes code for performance-related issues."""
    
    # Known anti-patterns
    ANTI_PATTERNS = {
        # Memory patterns
        "cpu_copy": {
            "pattern": r"torch\.empty_like\([^)]*device=[\"']cpu[\"']",
            "severity": "high",
            "category": "memory",
            "description": "Full CPU model copy without pooling - allocates duplicate memory",
            "suggestion": "Implement memory buffer pooling or use weight offloading with reuse",
            "estimated_impact": "30-50% memory reduction"
        },
        "gc_collect": {
            "pattern": r"gc\.collect\(\)",
            "severity": "medium",
            "category": "memory",
            "description": "Frequent garbage collection - may cause performance drops",
            "suggestion": "Use lazy GC or only when memory pressure detected",
            "estimated_impact": "5-10% performance improvement"
        },
        "no_no_grad": {
            "pattern": r"(cpu|to\([\"']cpu[\"']\))(?!\.(no_grad|eval))",
            "severity": "medium",
            "category": "memory",
            "description": "CPU transfer without torch.no_grad() - unnecessary gradient tracking",
            "suggestion": "Wrap in torch.no_grad() context",
            "estimated_impact": "10-15% memory reduction"
        },
        "tensor_recreation": {
            "pattern": r"torch\.(zeros|ones|empty)\((?!.*dtype)",
            "severity": "low",
            "category": "memory",
            "description": "Tensor recreated without explicit dtype - may not match model",
            "suggestion": "Use model.dtype or explicit dtype for consistency",
            "estimated_impact": "Minor"
        },
        
        # Inference patterns
        "cloudpickle": {
            "pattern": r"cloudpickle\.dump|cloudpickle\.loads",
            "severity": "high",
            "category": "inference",
            "description": "Cloudpickle serialization - slow for large objects",
            "suggestion": "Use msgpack or orjson for faster serialization",
            "estimated_impact": "2-3x faster serialization"
        },
        "blocking_ray_get": {
            "pattern": r"ray\.get\(",
            "severity": "high",
            "category": "inference",
            "description": "Blocking ray.get() - serializes worker communication",
            "suggestion": "Use async patterns or ray.get_async()",
            "estimated_impact": "20-40% latency reduction"
        },
        "serial_worker_init": {
            "pattern": r"for.*in.*workers:.*init",
            "severity": "medium",
            "category": "inference",
            "description": "Sequential worker initialization",
            "suggestion": "Use concurrent.futures for parallel initialization",
            "estimated_impact": "50% faster startup"
        },
        "no_connection_pool": {
            "pattern": r"ray\.get_actor\(",
            "severity": "low",
            "category": "inference",
            "description": "Repeated actor lookups without caching",
            "suggestion": "Cache actor handles to avoid repeated lookups",
            "estimated_impact": "Minor"
        },
        
        # Data loading patterns
        "inefficient_padding": {
            "pattern": r"for.*in.*batch:.*pad",
            "severity": "high",
            "category": "data_loading",
            "description": "Per-sample padding in loop - O(n²) complexity",
            "suggestion": "Use torch.nn.utils.rnn.pad_sequence for batch padding",
            "estimated_impact": "30-50% faster collation"
        },
        "np_tile": {
            "pattern": r"np\.tile\(",
            "severity": "medium",
            "category": "data_loading",
            "description": "np.tile for repetition - creates full copy",
            "suggestion": "Use generator-based sampling or torch.repeat",
            "estimated_impact": "Memory efficient, 20% faster"
        },
        "no_prefetch": {
            "pattern": r"DataLoader\([^)]*\)",
            "severity": "medium",
            "category": "data_loading",
            "description": "DataLoader without prefetch - blocks on I/O",
            "suggestion": "Set num_workers > 0 and prefetch_factor",
            "estimated_impact": "2-3x throughput"
        },
        "sequential_tokenization": {
            "pattern": r"for.*tokenizer\.",
            "severity": "medium",
            "category": "data_loading",
            "description": "Sequential tokenization in loop",
            "suggestion": "Batch tokenization with tokenizer.batch_encode_plus",
            "estimated_impact": "5-10x faster"
        },
        
        # Communication patterns
        "excessive_rpc": {
            "pattern": r"ray\.get\([^)]*\.remote\(\)",
            "severity": "high",
            "category": "communication",
            "description": "Multiple sequential Ray RPC calls",
            "suggestion": "Batch multiple operations into single RPC",
            "estimated_impact": "30-60% faster"
        },
        "no_batched_transfer": {
            "pattern": r"for.*ray\.get\(",
            "severity": "high",
            "category": "communication",
            "description": "Data transferred one batch at a time",
            "suggestion": "Collect all futures and batch ray.get()",
            "estimated_impact": "20-40% bandwidth improvement"
        },
        "ray_wait": {
            "pattern": r"ray\.wait\(",
            "severity": "low",
            "category": "communication",
            "description": "Using ray.wait() - good for fire-and-forget",
            "suggestion": "This is a best practice pattern, keep it",
            "estimated_impact": "N/A"
        },
        
        # Training loop patterns
        "sync_validation": {
            "pattern": r"ray\.get\(.*validation.*remote",
            "severity": "medium",
            "category": "training_loop",
            "description": "Synchronous validation blocking training",
            "suggestion": "Run validation asynchronously or less frequently",
            "estimated_impact": "10-20% training speedup"
        },
        "blocking_metrics": {
            "pattern": r"ray\.get\(.*metrics.*\)",
            "severity": "low",
            "category": "training_loop",
            "description": "Metrics collected synchronously",
            "suggestion": "Batch metric collection or use async callbacks",
            "estimated_impact": "Minor"
        },
        "sequential_processing": {
            "pattern": r"for.*in.*:.*process",
            "severity": "medium",
            "category": "training_loop",
            "description": "Sequential processing in loop that could be parallelized",
            "suggestion": "Use vectorized operations or parallel processing",
            "estimated_impact": "Variable"
        },
        
        # NPU-specific patterns (Ascend)
        "npu_cuda_memory": {
            "pattern": r"torch\.cuda\.(memory|empty_cache)",
            "severity": "high",
            "category": "npu_memory",
            "description": "Using CUDA memory API on NPU - not effective",
            "suggestion": "Replace with torch.npu.memory_allocated, torch.npu.empty_cache",
            "estimated_impact": "Proper NPU memory management"
        },
        "npu_missing_cache": {
            "pattern": r"\.npu\(\)(?!\.empty_cache)",
            "severity": "low",
            "category": "npu_memory",
            "description": "NPU tensor created without cache clearing",
            "suggestion": "Consider adding torch.npu.empty_cache() after large operations",
            "estimated_impact": "Memory optimization"
        },
        "npu_no_fp16_bf16": {
            "pattern": r"dtype=['\"]float32['\"](?!.*autocast)",
            "severity": "medium",
            "category": "npu_precision",
            "description": "Using FP32 without NPU mixed precision",
            "suggestion": "Enable torch.npu.amp.autocast for BF16/FP16 on NPU",
            "estimated_impact": "2x speedup on NPU"
        },
    }
    
    PY_EXTENSIONS = {'.py'}
    SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}
    
    def __init__(self, target_path: str, output_format: str = "json"):
        """Initialize performance analyzer."""
        self.target_path = Path(target_path)
        self.output_format = output_format
        self.report = PerformanceReport()

    @staticmethod
    def _is_ray_get(node: ast.Call) -> bool:
        """Check if AST node is a ray.get call."""
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == 'get':
                if isinstance(node.func.value, ast.Name):
                    return node.func.value.id == 'ray'
        return False

    def run(self) -> PerformanceReport:
        """Run performance analysis on target path."""
        if not self.target_path.exists():
            raise FileNotFoundError(f"Path not found: {self.target_path}")
            
        py_files = self._find_python_files()
        self.report.files_scanned = [str(f) for f in py_files]
        
        for py_file in py_files:
            self._analyze_file(py_file)
            
        self._generate_summary()
        
        return self.report

    def to_json(self) -> str:
        """Convert report to JSON string."""
        data = {
            "summary": self.report.summary,
            "files_scanned": self.report.files_scanned,
            "bottlenecks": [
                {
                    "severity": b.severity,
                    "category": b.category,
                    "file": b.file,
                    "line": b.line,
                    "description": b.description,
                    "suggestion": b.suggestion,
                    "estimated_impact": b.estimated_impact,
                    "code_snippet": b.code_snippet
                }
                for b in self.report.bottlenecks
            ]
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """Convert report to Markdown string."""
        md = ["# Performance Analysis Report\n"]

        md.append("## Summary\n")
        md.append(f"- **Total Bottlenecks:** {self.report.summary.get('bottlenecks', 0)}")
        md.append(f"- **High Impact:** {self.report.summary.get('high_impact', 0)}")
        md.append(f"- **Medium Impact:** {self.report.summary.get('medium_impact', 0)}")
        md.append(f"- **Low Impact:** {self.report.summary.get('low_impact', 0)}")
        md.append(f"- **Estimated Speedup:** {self.report.summary.get('estimated_speedup', 'N/A')}")
        md.append(f"- **Files Scanned:** {self.report.summary.get('files_scanned', 0)}")
        md.append("")

        # Patterns found
        if self.report.patterns_found:
            md.append("## Patterns Detected\n")
            for pattern, count in sorted(self.report.patterns_found.items(), key=lambda x: -x[1]):
                md.append(f"- `{pattern}`: {count} occurrences")
            md.append("")

        # Issues by category
        if self.report.bottlenecks:
            md.append("## Bottlenecks\n")

            categories = ["memory", "inference", "data_loading", "communication", "training_loop"]

            for category in categories:
                issues = [i for i in self.report.bottlenecks if i.category == category]
                if issues:
                    md.append(f"### {category.replace('_', ' ').title()}\n")

                    for issue in issues:
                        md.append(f"**[{issue.severity.upper()}]** {issue.file}:{issue.line}")
                        if issue.estimated_impact:
                            md.append(f"> Impact: {issue.estimated_impact}")
                        md.append(f"```python")
                        md.append(f"{issue.code_snippet}")
                        md.append(f"```")
                        md.append(f"{issue.description}")
                        md.append(f"**Suggestion:** {issue.suggestion}")
                        md.append("")

        return "\n".join(md)

    def _find_python_files(self) -> List[Path]:
        """Find all Python files in target path."""
        py_files = []
        
        if self.target_path.is_file():
            if self.target_path.suffix == '.py':
                py_files.append(self.target_path)
        else:
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
                for file in files:
                    if Path(file).suffix in self.PY_EXTENSIONS:
                        py_files.append(Path(root) / file)
                        
        return py_files
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for performance issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            logger.warning(f"Failed to read file: {file_path}")
            return
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            logger.warning(f"Failed to parse syntax: {file_path}")
            return
        
        relative_path = file_path.relative_to(self.target_path)
        
        # Check for anti-patterns
        self._check_anti_patterns(content, relative_path)
        
        # Check AST patterns
        self._check_ast_patterns(tree, content, relative_path, file_path)
    
    def _check_anti_patterns(self, content: str, relative_path: Path):
        """Check for known anti-patterns using regex."""
        lines = content.split('\n')
        
        for pattern_name, pattern_info in self.ANTI_PATTERNS.items():
            try:
                matches = re.finditer(pattern_info["pattern"], content, re.IGNORECASE | re.MULTILINE)
            except re.error:
                continue
                
            for match in matches:
                # Find line number
                line_num = content[:match.start()].count('\n') + 1
                
                # Get line content
                line_start = content.rfind('\n', 0, match.start()) + 1
                line_end = content.find('\n', match.end())
                if line_end == -1:
                    line_end = len(content)
                line_content = content[line_start:line_end].strip()
                
                # Record pattern found
                self.report.patterns_found[pattern_name] = self.report.patterns_found.get(pattern_name, 0) + 1
                
                # Skip if it's a comment
                if line_content.strip().startswith('#'):
                    continue
                    
                self.report.bottlenecks.append(PerformanceIssue(
                    severity=pattern_info["severity"],
                    category=pattern_info["category"],
                    file=str(relative_path),
                    line=line_num,
                    description=pattern_info["description"],
                    suggestion=pattern_info["suggestion"],
                    estimated_impact=pattern_info["estimated_impact"],
                    code_snippet=line_content[:100]  # Truncate long lines
                ))
    
    def _check_ast_patterns(self, tree: ast.AST, content: str, relative_path: Path, file_path: Path):
        """Check for specific AST patterns."""
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            # Check for for loops with blocking operations
            if isinstance(node, ast.For):
                # Check if loop contains ray.get
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute):
                            if child.func.attr == 'get' and self._is_ray_get(child):
                                line_num = node.lineno or 0
                                self.report.bottlenecks.append(PerformanceIssue(
                                    severity="high",
                                    category="communication",
                                    file=str(relative_path),
                                    line=line_num,
                                    description="Ray get in loop - potential serialization point",
                                    suggestion="Batch operations outside loop or use async",
                                    estimated_impact="20-40% speedup"
                                ))
    
    def _generate_summary(self):
        """Generate summary statistics."""
        high = sum(1 for i in self.report.bottlenecks if i.severity == "high")
        medium = sum(1 for i in self.report.bottlenecks if i.severity == "medium")
        low = sum(1 for i in self.report.bottlenecks if i.severity == "low")
        
        # Calculate estimated speedup
        estimated_speedup = self._estimate_speedup()
        
        self.report.summary = {
            "bottlenecks": len(self.report.bottlenecks),
            "high_impact": high,
            "medium_impact": medium,
            "low_impact": low,
            "estimated_speedup": estimated_speedup,
            "files_scanned": len(self.report.files_scanned),
            "patterns_found": self.report.patterns_found
        }
    
    def _estimate_speedup(self) -> str:
        """Estimate potential speedup based on issues found."""
        total_impact = 0.0
        
        for bottleneck in self.report.bottlenecks:
            impact_str = bottleneck.estimated_impact
            if not impact_str or impact_str == "N/A" or impact_str == "Minor":
                continue
                
            # Parse impact
            try:
                if 'x' in impact_str:
                    # e.g., "2-3x faster"
                    num = float(impact_str.split('x')[0].split('-')[-1].strip())
                    total_impact += num
                elif '%' in impact_str:
                    # e.g., "30% memory reduction"
                    num = float(impact_str.split('%')[0].split('-')[-1].strip())
                    total_impact += num / 100
            except (ValueError, IndexError):
                continue
        
        if total_impact == 0:
            return "Minimal"
        elif total_impact < 0.5:
            return "~1.2x"
        elif total_impact < 1.0:
            return "~1.5x"
        elif total_impact < 2.0:
            return "~2x"
        else:
            return f"~{total_impact:.1f}x"


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze code for performance issues")
    parser.add_argument("target_path", help="Path to analyze")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "console"], 
                       default="console", help="Output format")
    
    args = parser.parse_args()
    
    analyzer = PerformanceAnalyzer(args.target_path, args.format)
    report = analyzer.run()
    
    if args.format == "json":
        output = analyzer.to_json()
    elif args.format == "markdown":
        output = analyzer.to_markdown()
    else:
        output = f"Performance Analysis Report\n{'='*50}\n"
        output += f"Bottlenecks found: {report.summary.get('bottlenecks', 0)}\n"
        output += f"Estimated speedup: {report.summary.get('estimated_speedup', 'N/A')}\n"
        for issue in report.bottlenecks:
            output += f"\n[{issue.severity.upper()}] {issue.file}:{issue.line} ({issue.category})"
            output += f"\n  {issue.description}\n"
            output += f"  {issue.suggestion}\n"
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Report written to {args.output}")
    else:
        logger.warning(output)


if __name__ == "__main__":
    main()
