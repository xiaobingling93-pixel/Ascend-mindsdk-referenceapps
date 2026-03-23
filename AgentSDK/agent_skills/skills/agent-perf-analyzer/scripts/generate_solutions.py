"""
Solution Generator Module for AgentSDK/Agentic RL Codebases.

This module generates actionable solutions for precision and performance issues
detected by the analyzer modules.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logging.basicConfig(
    level=logging.WARNING,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Solution:
    """Represents an actionable solution."""
    title: str
    category: str
    effort: str  # quick, medium, architectural
    impact: str
    description: str
    code_before: str = ""
    code_after: str = ""
    files_to_modify: List[str] = field(default_factory=list)
    priority: int = 0  # 1 = highest


@dataclass
class SolutionReport:
    """Complete solution report."""
    quick_wins: List[Solution] = field(default_factory=list)
    medium_effort: List[Solution] = field(default_factory=list)
    architectural: List[Solution] = field(default_factory=list)
    total_estimated_improvement: str = ""


class SolutionGenerator:
    """Generates solutions for detected issues."""
    
    # Solution templates
    SOLUTION_TEMPLATES = {
        # Precision solutions
        "dtype_conversion": {
            "title": "Fix float64 to float32 Conversion",
            "category": "precision",
            "effort": "medium",
            "description": "Replace float64 tensor creation with float32 or add overflow check",
            "code_before": '''# Before: Creates float64 then converts
scores = torch.tensor(rewards, dtype=torch.float64)
scores = scores.to(torch.float32)  # Precision loss here''',
            "code_after": '''# After Option 1: Use float32 from start
scores = torch.tensor(rewards, dtype=torch.float32)

# After Option 2: Add overflow guard
scores = torch.tensor(rewards, dtype=torch.float64)
if scores.abs().max() > 1e6:  # Overflow check
    warnings.warn("Potential overflow in reward values")
scores = scores.to(torch.float32)''',
        },
        "numerical_stability": {
            "title": "Add NaN/Inf Detection",
            "category": "precision",
            "effort": "quick",
            "description": "Add finite check before backward pass",
            "code_before": '''# Before: No validation
loss.backward()
optimizer.step()''',
            "code_after": '''# After: Add finite check
if torch.isfinite(loss).all():
    loss.backward()
    optimizer.step()
else:
    logger.warning("Non-finite loss detected, skipping update")''',
        },
        "dtype_consistency": {
            "title": "Ensure Dtype Consistency",
            "category": "precision",
            "effort": "quick",
            "description": "Match tensor dtype with model weight dtype",
            "code_before": '''# Before: Uses default dtype
score_batch = torch.zeros_like(response_batch)''',
            "code_after": '''# After: Explicit dtype from model
score_batch = torch.zeros_like(
    response_batch, 
    dtype=model.transformer.weight.dtype
)''',
        },
        
        # Performance solutions
        "memory": {
            "title": "Add torch.no_grad() Context",
            "category": "performance",
            "effort": "quick",
            "description": "Wrap CPU transfers in no_grad to save memory",
            "code_before": '''# Before: Tracks gradients unnecessarily
cpu_params = [p.cpu() for p in model.parameters()]''',
            "code_after": '''# After: No gradient tracking
with torch.no_grad():
    cpu_params = [p.cpu() for p in model.parameters()]''',
        },
        "inference": {
            "title": "Replace Cloudpickle Serialization",
            "category": "performance",
            "effort": "medium",
            "description": "Use faster serialization format",
            "code_before": '''# Before: Slow cloudpickle
import cloudpickle
data = cloudpickle.dumps(obj)''',
            "code_after": '''# After: Faster alternatives
import pickle  # Or use msgpack/orjson for specific cases
data = pickle.dumps(obj)  # Much faster for most objects''',
        },
        "communication": {
            "title": "Batch Ray RPC Calls",
            "category": "performance",
            "effort": "medium",
            "description": "Reduce number of round trips",
            "code_before": '''# Before: Sequential RPC calls
for worker in workers:
    ray.get(worker.process.remote(batch))''',
            "code_after": '''# After: Batched RPC
# Option 1: Submit all first
futures = [w.process.remote(batch) for w in workers]
results = ray.get(futures)  # Single call

# Option 2: Use ray.wait for streaming
pending = [w.process.remote(batch) for w in workers]
while pending:
    done, pending = ray.wait(pending, num_returns=1)''',
        },
        "data_loading": {
            "title": "Optimize Batch Padding",
            "category": "performance",
            "effort": "quick",
            "description": "Use vectorized padding instead of loops",
            "code_before": '''# Before: Per-sample padding in loop
padded = []
for sample in batch:
    padded.append(pad_sequence(sample, batch_first=True))''',
            "code_after": '''# After: Vectorized padding
padded = torch.nn.utils.rnn.pad_sequence(
    batch, 
    batch_first=True, 
    padding_value=tokenizer.pad_token_id
)''',
        },
        "training_loop": {
            "title": "Parallelize Worker Initialization",
            "category": "performance",
            "effort": "medium",
            "description": "Initialize workers in parallel",
            "code_before": '''# Before: Sequential init
for worker in workers:
    worker.init_worker.remote(config)''',
            "code_after": '''# After: Parallel init with concurrent.futures
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=len(workers)) as executor:
    futures = [executor.submit(lambda w: ray.get(w.init_worker.remote(config)), w) 
               for w in workers]
    ray.get([f.result() for f in futures])''',
        },
        
        # NPU-specific solutions (Ascend)
        "npu_api_usage": {
            "title": "Replace CUDA with NPU APIs",
            "category": "npu",
            "effort": "quick",
            "description": "Migrate CUDA code to NPU for Ascend compatibility",
            "code_before": '''# Before: CUDA API
tensor = torch.randn(2, 2).cuda()
torch.cuda.set_device(0)
mem = torch.cuda.memory_allocated()''',
            "code_after": '''# After: NPU API
tensor = torch.randn(2, 2).npu()
torch.npu.set_device(0)
mem = torch.npu.memory_allocated()''',
        },
        "npu_amp": {
            "title": "Enable NPU Mixed Precision (AMP)",
            "category": "npu",
            "effort": "quick",
            "description": "Use NPU AMP for BF16/FP16 training on Ascend",
            "code_before": '''# Before: CUDA AMP or no AMP
with torch.cuda.amp.autocast():
    output = model(input)
scaler = torch.cuda.amp.GradScaler('cuda')''',
            "code_after": '''# After: NPU AMP
with torch.npu.amp.autocast():
    output = model(input)
scaler = torch.npu.amp.GradScaler('npu')''',
        },
        "npu_memory": {
            "title": "Use NPU Memory Management",
            "category": "npu",
            "effort": "quick",
            "description": "Replace CUDA memory APIs with NPU equivalents",
            "code_before": '''# Before: CUDA memory
torch.cuda.empty_cache()
torch.cuda.memory_reserved()''',
            "code_after": '''# After: NPU memory
torch.npu.empty_cache()
torch.npu.memory_reserved()''',
        },
    }
    
    def __init__(self, precision_report: Optional[Dict] = None, 
                 performance_report: Optional[Dict] = None):
        """Initialize solution generator."""
        self.precision_report = precision_report
        self.performance_report = performance_report
        self.solutions: List[Solution] = []

    @staticmethod
    def _severity_to_priority(severity: str) -> int:
        """Convert severity to priority."""
        priority_map = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4
        }
        return priority_map.get(severity, 3)

    @staticmethod
    def _severity_to_impact(severity: str) -> str:
        """Convert severity to impact description."""
        impact_map = {
            "critical": "High",
            "high": "Medium-High",
            "medium": "Medium",
            "low": "Low"
        }
        return impact_map.get(severity, "Medium")

    def generate(self) -> SolutionReport:
        """Generate solutions from reports."""
        # Generate precision solutions
        if self.precision_report:
            self._generate_precision_solutions()
            
        # Generate performance solutions
        if self.performance_report:
            self._generate_performance_solutions()
            
        # Sort and categorize
        return self._organize_solutions()

    def to_markdown(self, report: Optional[SolutionReport] = None) -> str:
        """Convert solutions to Markdown."""
        if report is None:
            report = self.generate()

        md = ["# Solutions Report\n"]

        md.append(f"**Total Estimated Improvement:** {report.total_estimated_improvement}\n")

        # Quick wins
        if report.quick_wins:
            md.append("\n## Quick Wins (< 5 min)\n")
            for i, solution in enumerate(report.quick_wins, 1):
                md.append(f"### {i}. {solution.title}")
                md.append(f"**Category:** {solution.category}")
                md.append(f"**Impact:** {solution.impact}")
                md.append(f"**Files:** {', '.join(solution.files_to_modify)}")
                md.append(f"\n{solution.description}\n")

                if solution.code_before:
                    md.append("```python")
                    md.append(f"# Before\n{solution.code_before}")
                    md.append(f"# After\n{solution.code_after}")
                    md.append("```\n")

        # Medium effort
        if report.medium_effort:
            md.append("\n## Medium Effort (15-60 min)\n")
            for i, solution in enumerate(report.medium_effort, 1):
                md.append(f"### {i}. {solution.title}")
                md.append(f"**Category:** {solution.category}")
                md.append(f"**Impact:** {solution.impact}")
                md.append(f"**Files:** {', '.join(solution.files_to_modify)}")
                md.append(f"\n{solution.description}\n")

                if solution.code_before:
                    md.append("```python")
                    md.append(f"# Before\n{solution.code_before}")
                    md.append(f"# After\n{solution.code_after}")
                    md.append("```\n")

        # Architectural changes
        if report.architectural:
            md.append("\n## Architectural Changes (hours)\n")
            for i, solution in enumerate(report.architectural, 1):
                md.append(f"### {i}. {solution.title}")
                md.append(f"**Category:** {solution.category}")
                md.append(f"**Impact:** {solution.impact}")
                md.append(f"\n{solution.description}\n")

        return "\n".join(md)

    def to_json(self, report: Optional[SolutionReport] = None) -> str:
        """Convert solutions to JSON."""
        if report is None:
            report = self.generate()

        def solution_to_dict(s: Solution) -> Dict:
            return {
                "title": s.title,
                "category": s.category,
                "effort": s.effort,
                "impact": s.impact,
                "description": s.description,
                "code_before": s.code_before,
                "code_after": s.code_after,
                "files_to_modify": s.files_to_modify,
                "priority": s.priority
            }

        data = {
            "total_estimated_improvement": report.total_estimated_improvement,
            "quick_wins": [solution_to_dict(s) for s in report.quick_wins],
            "medium_effort": [solution_to_dict(s) for s in report.medium_effort],
            "architectural": [solution_to_dict(s) for s in report.architectural]
        }

        return json.dumps(data, indent=2)

    def _generate_precision_solutions(self):
        """Generate solutions for precision issues."""
        if not self.precision_report:
            return
            
        issues = self.precision_report.get("issues", [])
        
        for issue in issues:
            category = issue.get("category", "")
            severity = issue.get("severity", "medium")
            
            # Map issue to solution template
            template_key = None
            if "dtype" in category:
                template_key = "dtype_conversion"
            elif "numerical" in category:
                template_key = "numerical_stability"
            elif "dtype_consistency" in category:
                template_key = "dtype_consistency"
                
            if template_key and template_key in self.SOLUTION_TEMPLATES:
                template = self.SOLUTION_TEMPLATES[template_key]
                solution = Solution(
                    title=template["title"],
                    category="precision",
                    effort=template["effort"],
                    impact=self._severity_to_impact(severity),
                    description=template["description"],
                    code_before=template["code_before"],
                    code_after=template["code_after"],
                    files_to_modify=[issue.get("file", "")],
                    priority=self._severity_to_priority(severity)
                )
                self.solutions.append(solution)
    
    def _generate_performance_solutions(self):
        """Generate solutions for performance issues."""
        if not self.performance_report:
            return
            
        bottlenecks = self.performance_report.get("bottlenecks", [])
        
        for bottleneck in bottlenecks:
            category = bottleneck.get("category", "")
            severity = bottleneck.get("severity", "medium")
            
            # Map category to solution template
            template_key = None
            if category == "memory":
                template_key = "memory"
            elif category == "inference":
                template_key = "inference"
            elif category == "communication":
                template_key = "communication"
            elif category == "data_loading":
                template_key = "data_loading"
            elif category == "training_loop":
                template_key = "training_loop"
            elif category in ("npu_memory", "npu_precision", "npu_api_usage"):
                template_key = "npu_api_usage"
            elif "npu" in category:
                template_key = "npu_amp"
                
            if template_key and template_key in self.SOLUTION_TEMPLATES:
                template = self.SOLUTION_TEMPLATES[template_key]
                solution = Solution(
                    title=template["title"],
                    category="performance",
                    effort=template["effort"],
                    impact=bottleneck.get("estimated_impact", "variable"),
                    description=template["description"],
                    code_before=template["code_before"],
                    code_after=template["code_after"],
                    files_to_modify=[bottleneck.get("file", "")],
                    priority=self._severity_to_priority(severity)
                )
                self.solutions.append(solution)
    
    def _organize_solutions(self) -> SolutionReport:
        """Organize solutions by effort."""
        report = SolutionReport()
        
        # Sort by priority
        self.solutions.sort(key=lambda s: s.priority)
        
        for solution in self.solutions:
            if solution.effort == "quick":
                report.quick_wins.append(solution)
            elif solution.effort == "medium":
                report.medium_effort.append(solution)
            else:
                report.architectural.append(solution)
        
        # Estimate total improvement
        improvements = []
        for s in self.solutions:
            if s.impact and s.impact != "variable":
                improvements.append(s.impact)
        
        if len(improvements) > 3:
            report.total_estimated_improvement = "Significant (2-5x)"
        elif len(improvements) > 0:
            report.total_estimated_improvement = "Moderate (1.2-2x)"
        else:
            report.total_estimated_improvement = "To be determined"
        
        return report


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate solutions for detected issues")
    parser.add_argument("precision_report", help="Path to precision report JSON")
    parser.add_argument("performance_report", help="Path to performance report JSON")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", "-f", choices=["json", "markdown", "console"], 
                       default="console", help="Output format")
    
    args = parser.parse_args()
    
    # Load reports
    with open(args.precision_report) as f:
        precision_report = json.load(f)
        
    with open(args.performance_report) as f:
        performance_report = json.load(f)
    
    # Generate solutions
    generator = SolutionGenerator(precision_report, performance_report)
    report = generator.generate()
    
    if args.format == "json":
        output = generator.to_json(report)
    elif args.format == "markdown":
        output = generator.to_markdown(report)
    else:
        output = f"Solutions Report\n{'='*50}\n"
        output += f"Total Improvement: {report.total_estimated_improvement}\n"
        output += f"Quick Wins: {len(report.quick_wins)}\n"
        output += f"Medium Effort: {len(report.medium_effort)}\n"
        output += f"Architectural: {len(report.architectural)}\n"
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        logger.info(f"Report written to {args.output}")
    else:
        logger.warning(output)


if __name__ == "__main__":
    main()
