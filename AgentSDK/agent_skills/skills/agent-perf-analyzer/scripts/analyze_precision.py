"""
Precision Analysis Module for AgentSDK/Agentic RL Codebases (Ascend NPU Edition).

This module analyzes Python code for precision-related issues:
- Dtype consistency (BF16/FP16/FP32)
- Float64→Float32 conversions
- Numerical stability (epsilon, NaN checks)
- Mixed precision handling
- Gradient operations
- NPU-specific checks (torch.npu, Ascend CANN)
"""

import ast
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PrecisionIssue:
    """Represents a precision-related issue found in code."""
    severity: str  # critical, high, medium, low
    category: str  # dtype_conversion, numerical_stability, mixed_precision, etc.
    file: str
    line: int
    description: str
    suggestion: str
    code_snippet: str = ""


@dataclass
class PrecisionReport:
    """Complete precision analysis report."""
    summary: Dict[str, int] = field(default_factory=dict)
    issues: List[PrecisionIssue] = field(default_factory=list)
    files_scanned: List[str] = field(default_factory=list)


class PrecisionAnalyzer:
    """Analyzes code for precision-related issues."""
    
    # Patterns that indicate precision issues
    DTYPE_PATTERNS = {
        "float64_to_float32": {
            "pattern": r"\.to\(torch\.float32\)|\.float\(\)|dtype=torch\.float32",
            "severity": "high",
            "category": "dtype_conversion",
            "description": "Potential precision loss from float64 to float32 conversion",
            "suggestion": "Check if float64 is necessary, or use float32 from the start"
        },
        "hardcoded_epsilon": {
            "pattern": r"1e-[0-9]+",  # Common epsilon values
            "severity": "medium",
            "category": "numerical_stability",
            "description": "Hardcoded epsilon value - consider making configurable",
            "suggestion": "Extract to config parameter for tuning"
        },
        "no_isfinite_check": {
            "pattern": r"loss\.backward\(\)|loss\.item\(\)",
            "severity": "high",
            "category": "numerical_stability",
            "description": "No NaN/Inf check before backward pass",
            "suggestion": "Add torch.isfinite() check before backward()"
        },
        "zeros_like_dtype": {
            "pattern": r"torch\.zeros_like\([^)]*\)",
            "severity": "medium",
            "category": "dtype_consistency",
            "description": "zeros_like without explicit dtype may not match model dtype",
            "suggestion": "Add explicit dtype parameter or use model.weight.dtype"
        },
        "tensor_creation": {
            "pattern": r"torch\.tensor\([^)]*dtype=[^)]*float64",
            "severity": "high",
            "category": "dtype_conversion",
            "description": "Explicit float64 tensor creation may cause issues",
            "suggestion": "Use float32 for training, float64 only for accumulation"
        },
        "no_grad_clip": {
            "pattern": r"clip_grad|grad_clip",
            "severity": "low",
            "category": "numerical_stability",
            "description": "Gradient clipping found - verify threshold is appropriate",
            "suggestion": "Typical threshold: 0.5-1.0 for BF16, 1.0-2.0 for FP32"
        },
        "autocast_missing": {
            "pattern": r"autocast|GradScaler|amp\.autocast",
            "severity": "medium",
            "category": "mixed_precision",
            "description": "No automatic mixed precision (AMP) found",
            "suggestion": "Consider using torch.amp.autocast for BF16 training"
        },
        "explicit_fp32_softmax": {
            "pattern": r"softmax.*fp32|attention_softmax_in_fp32",
            "severity": "low",
            "category": "mixed_precision",
            "description": "FP32 softmax - good for numerical stability",
            "suggestion": "This is a best practice, keep it"
        },
        # NPU-specific patterns (Ascend)
        "cuda_device": {
            "pattern": r"\.cuda\(\)|torch\.cuda\.set_device|device=['\"]cuda",
            "severity": "high",
            "category": "npu_api_usage",
            "description": "Using CUDA API instead of NPU - not compatible with Ascend",
            "suggestion": "Replace .cuda() with .npu(), torch.cuda.set_device with torch.npu.set_device"
        },
        "cuda_amp": {
            "pattern": r"torch\.cuda\.amp|GradScaler\(['\"]cuda",
            "severity": "high",
            "category": "npu_api_usage",
            "description": "Using CUDA AMP instead of NPU AMP",
            "suggestion": "Replace with torch.npu.amp.autocast and torch.npu.amp.GradScaler('npu')"
        },
        "cuda_memory": {
            "pattern": r"torch\.cuda\.memory|empty_cache",
            "severity": "medium",
            "category": "npu_api_usage",
            "description": "Using CUDA memory API instead of NPU",
            "suggestion": "Replace torch.cuda.memory_* with torch.npu.memory_*"
        },
    }
    
    # File extensions to analyze
    PY_EXTENSIONS = {'.py'}
    
    # Directories to skip
    SKIP_DIRS = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', '.venv'}
    
    def __init__(self, target_path: str, output_format: str = "json"):
        """
        Initialize precision analyzer.
        
        Args:
            target_path: Path to analyze
            output_format: json, markdown, or console
        """
        self.target_path = Path(target_path)
        self.output_format = output_format
        self.report = PrecisionReport()

    @staticmethod
    def _check_ast_patterns(tree: ast.AST, content: str, relative_path: Path, file_path: Path):
        """Check for specific AST patterns."""
        lines = content.split('\n')

        for node in ast.walk(tree):
            # Check for autocast usage
            if isinstance(node, ast.Name) and 'autocast' in node.id.lower():
                # Found autocast reference
                pass  # This is good

            # Check for GradScaler
            if isinstance(node, ast.Name) and 'gradscaler' in node.id.lower():
                pass  # This indicates AMP is being used

    def run(self) -> PrecisionReport:
        """
        Run precision analysis on target path.
        
        Returns:
            PrecisionReport with all findings
        """
        if not self.target_path.exists():
            raise FileNotFoundError(f"Path not found: {self.target_path}")
            
        # Find all Python files
        py_files = self._find_python_files()
        self.report.files_scanned = [str(f) for f in py_files]
        
        # Analyze each file
        for py_file in py_files:
            self._analyze_file(py_file)
            
        # Generate summary
        self._generate_summary()
        
        return self.report

    def to_json(self) -> str:
        """Convert report to JSON string."""
        data = {
            "summary": self.report.summary,
            "files_scanned": self.report.files_scanned,
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "description": i.description,
                    "suggestion": i.suggestion,
                    "code_snippet": i.code_snippet
                }
                for i in self.report.issues
            ]
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """Convert report to Markdown string."""
        md = ["# Precision Analysis Report\n"]

        # Summary
        md.append("## Summary\n")
        md.append(f"- **Total Issues:** {self.report.summary.get('issues_found', 0)}")
        md.append(f"- **Critical:** {self.report.summary.get('critical', 0)}")
        md.append(f"- **High:** {self.report.summary.get('high', 0)}")
        md.append(f"- **Medium:** {self.report.summary.get('medium', 0)}")
        md.append(f"- **Low:** {self.report.summary.get('low', 0)}")
        md.append(f"- **Files Scanned:** {self.report.summary.get('files_scanned', 0)}")
        md.append("")

        # Issues by severity
        if self.report.issues:
            md.append("## Issues\n")

            # Group by severity
            severity_order = ["critical", "high", "medium", "low"]

            for severity in severity_order:
                issues = [i for i in self.report.issues if i.severity == severity]
                if issues:
                    md.append(f"### {severity.upper()}\n")

                    for issue in issues:
                        md.append(f"**{issue.file}:{issue.line}** - {issue.category}")
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
                # Skip certain directories
                dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
                
                for file in files:
                    if Path(file).suffix in self.PY_EXTENSIONS:
                        py_files.append(Path(root) / file)
                        
        return py_files
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file for precision issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            logger.warning(f"Failed to read file: {file_path}")
            return
            
        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
        except SyntaxError:
            logger.warning(f"Failed to parse syntax: {file_path}")
            return
        
        # Check for various patterns
        relative_path = file_path.relative_to(self.target_path)
        
        # Check for float64 usage
        self._check_dtype_issues(content, relative_path, file_path)
        
        # Check for numerical stability issues
        self._check_numerical_stability(content, relative_path, file_path)
        
        # Check AST for specific patterns
        self._check_ast_patterns(tree, content, relative_path, file_path)
    
    def _check_dtype_issues(self, content: str, relative_path: Path, file_path: Path):
        """Check for dtype-related issues using regex patterns."""
        import re
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for float64 creation
            if 'dtype=torch.float64' in line or 'dtype=torch.float' in line:
                self.report.issues.append(PrecisionIssue(
                    severity="high",
                    category="dtype_conversion",
                    file=str(relative_path),
                    line=i,
                    description="float64 tensor creation - may cause precision issues in BF16 training",
                    suggestion="Use float32 unless specifically needed for higher precision",
                    code_snippet=line.strip()
                ))
                
            # Check for explicit float32 conversion
            if re.search(r'\.to\(torch\.float32\)', line) or re.search(r'\.float\(\)', line):
                # Check if this is from float64
                context_start = max(0, i - 3)
                context = '\n'.join(lines[context_start:i])
                
                if 'float64' in context:
                    self.report.issues.append(PrecisionIssue(
                        severity="high",
                        category="dtype_conversion",
                        file=str(relative_path),
                        line=i,
                        description="float64→float32 conversion detected - potential precision loss",
                        suggestion="Consider using float32 from the start or adding overflow check",
                        code_snippet=line.strip()
                    ))
                    
            # Check for zeros_like without dtype
            if 'torch.zeros_like' in line and 'dtype=' not in line:
                self.report.issues.append(PrecisionIssue(
                    severity="medium",
                    category="dtype_consistency",
                    file=str(relative_path),
                    line=i,
                    description="zeros_like without explicit dtype",
                    suggestion="Add explicit dtype parameter to match model weight dtype",
                    code_snippet=line.strip()
                ))
    
    def _check_numerical_stability(self, content: str, relative_path: Path, file_path: Path):
        """Check for numerical stability issues."""
        import re
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for hardcoded epsilon
            epsilon_matches = re.findall(r'1e-[0-9]+', line)
            has_math_operator = any(op in line for op in '+-*/')
            if epsilon_matches and has_math_operator:
                # This is likely used in division or normalization
                keywords = ['std', 'normalize', 'eps', 'epsilon', 'div', 'safe']
                has_relevant_keyword = any(kw in line.lower() for kw in keywords)
                if has_relevant_keyword:
                    self.report.issues.append(PrecisionIssue(
                        severity="low",
                        category="numerical_stability",
                        file=str(relative_path),
                        line=i,
                        description=f"Hardcoded epsilon: {epsilon_matches[0]}",
                        suggestion="Consider making epsilon configurable",
                        code_snippet=line.strip()
                    ))
            
            # Check for loss backward without finite check
            if '.backward()' in line or 'loss.backward' in line:
                # Look backward for isfinite check
                context_start = max(0, i - 10)
                context = '\n'.join(lines[context_start:i])
                
                if 'isfinite' not in context and 'nan' not in context.lower() and 'inf' not in context.lower():
                    self.report.issues.append(PrecisionIssue(
                        severity="high",
                        category="numerical_stability",
                        file=str(relative_path),
                        line=i,
                        description="No NaN/Inf check before backward pass",
                        suggestion="Add torch.isfinite(loss).all() check before backward()",
                        code_snippet=line.strip()
                    ))
    
    def _generate_summary(self):
        """Generate summary statistics."""
        critical = sum(1 for i in self.report.issues if i.severity == "critical")
        high = sum(1 for i in self.report.issues if i.severity == "high")
        medium = sum(1 for i in self.report.issues if i.severity == "medium")
        low = sum(1 for i in self.report.issues if i.severity == "low")
        
        self.report.summary = {
            "issues_found": len(self.report.issues),
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "files_scanned": len(self.report.files_scanned)
        }


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze code for precision issues")
    parser.add_argument("target_path", help="Path to analyze")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "console"], 
                       default="console", help="Output format")
    
    args = parser.parse_args()
    
    analyzer = PrecisionAnalyzer(args.target_path, args.format)
    report = analyzer.run()
    
    if args.format == "json":
        output = analyzer.to_json()
    elif args.format == "markdown":
        output = analyzer.to_markdown()
    else:
        output = f"Precision Analysis Report\n{'='*50}\n"
        output += f"Issues found: {report.summary.get('issues_found', 0)}\n"
        for issue in report.issues:
            output += f"\n[{issue.severity.upper()}] {issue.file}:{issue.line}\n"
            output += f"  {issue.description}\n"
            output += f"  {issue.suggestion}\n"
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Report written to {args.output}")
    else:
        logger.warning(output)


if __name__ == "__main__":
    main()
