"""
title: Code Analysis Tool
version: 1.0.0
description: Code formatting, analysis, syntax checking, and documentation generation.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic

# SYSTEM PROMPT FOR AI
# ====================
# Analyze, format, and document code.
#
# CAPABILITIES:
#   - Syntax validation
#   - Code formatting (Python, JSON, XML)
#   - Complexity analysis
#   - Documentation generation
#   - Diff comparison
"""

import os
import re
import json
import ast
import tokenize
import io
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        max_line_length: int = Field(default=88, description="Max line length for formatting")
        indent_size: int = Field(default=4, description="Indentation size")
        show_line_numbers: bool = Field(default=True, description="Show line numbers in output")

    def __init__(self):
        self.citation = False
        self.valves = self.Valves()

    def validate_python(self, code: str) -> str:
        """
        Validate Python code syntax.

        Args:
            code: Python code to validate

        Returns:
            Validation result with any errors found.
        """
        try:
            ast.parse(code)
            return "✅ Python syntax is valid.\n\nNo errors found."
        except SyntaxError as e:
            error_line = e.lineno if e.lineno else "?"
            error_col = e.offset if e.offset else "?"
            error_msg = e.msg if e.msg else str(e)

            result = [
                "❌ Python syntax error found:",
                "",
                f"Line {error_line}, Column {error_col}:",
                f"  {error_msg}",
                "",
            ]

            # Show context if possible
            lines = code.split('\n')
            if e.lineno and 0 < e.lineno <= len(lines):
                result.append("Context:")
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                for i in range(start, end):
                    marker = ">>> " if i == e.lineno - 1 else "    "
                    result.append(f"{marker}{i+1:4}: {lines[i]}")
                    if i == e.lineno - 1 and e.offset:
                        result.append("    " + " " * (5 + e.offset) + "^")

            return "\n".join(result)

    def validate_json(self, json_str: str) -> str:
        """
        Validate JSON syntax and format.

        Args:
            json_str: JSON string to validate

        Returns:
            Validation result.
        """
        try:
            parsed = json.loads(json_str)

            # Format and show structure
            formatted = json.dumps(parsed, indent=2)
            lines = formatted.split('\n')

            result = [
                "✅ JSON is valid.",
                "",
                f"Type: {type(parsed).__name__}",
            ]

            if isinstance(parsed, dict):
                result.append(f"Keys: {len(parsed)}")
                if len(parsed) <= 10:
                    result.append(f"Keys: {', '.join(parsed.keys())}")
            elif isinstance(parsed, list):
                result.append(f"Items: {len(parsed)}")

            if len(lines) <= 20:
                result.extend(["", "Formatted:", "```json", formatted, "```"])
            else:
                result.extend(["", f"(Content: {len(lines)} lines, {len(json_str)} characters)"])

            return "\n".join(result)

        except json.JSONDecodeError as e:
            return f"❌ JSON syntax error:\n\nLine {e.lineno}, Column {e.colno}:\n  {e.msg}"

    def format_python(self, code: str) -> str:
        """
        Format Python code with consistent style.

        Args:
            code: Python code to format

        Returns:
            Formatted code.
        """
        # First validate
        try:
            ast.parse(code)
        except SyntaxError as e:
            return f"Cannot format invalid Python code.\n\n{self.validate_python(code)}"

        # Basic formatting
        lines = code.split('\n')
        formatted_lines = []
        indent_size = self.valves.indent_size

        for line in lines:
            # Preserve original indentation but normalize it
            stripped = line.lstrip()
            if stripped:
                # Count leading spaces/tabs
                leading = len(line) - len(stripped)
                # Normalize tabs to spaces
                normalized_line = line.replace('\t', ' ' * indent_size)
                leading_spaces = len(normalized_line) - len(normalized_line.lstrip())
                # Calculate indent level
                indent_level = leading_spaces // indent_size
                # Rebuild line with consistent indentation
                formatted_lines.append(' ' * (indent_level * indent_size) + stripped)
            else:
                formatted_lines.append('')

        formatted = '\n'.join(formatted_lines)

        # Remove trailing whitespace
        formatted = '\n'.join(line.rstrip() for line in formatted.split('\n'))

        # Ensure single newline at end
        formatted = formatted.rstrip() + '\n'

        result = [
            "✅ Code formatted.",
            "",
            "```python",
            formatted.rstrip(),
            "```"
        ]

        return "\n".join(result)

    def format_json(self, json_str: str, indent: int = 2) -> str:
        """
        Format JSON with consistent indentation.

        Args:
            json_str: JSON to format
            indent: Indentation level (default: 2)

        Returns:
            Formatted JSON.
        """
        try:
            parsed = json.loads(json_str)
            formatted = json.dumps(parsed, indent=indent, ensure_ascii=False, sort_keys=False)

            result = [
                "✅ JSON formatted.",
                "",
                "```json",
                formatted,
                "```"
            ]

            return "\n".join(result)

        except json.JSONDecodeError as e:
            return f"Cannot format invalid JSON.\n\n{self.validate_json(json_str)}"

    def analyze_python(self, code: str) -> str:
        """
        Analyze Python code complexity and structure.

        Args:
            code: Python code to analyze

        Returns:
            Analysis report with metrics.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Cannot analyze invalid Python.\n\n{self.validate_python(code)}"

        # Collect metrics
        metrics = {
            'lines': len(code.split('\n')),
            'lines_of_code': len([l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]),
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'complexity': 0,  # Simple cyclomatic complexity estimate
        }

        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                metrics['functions'] += 1
                func_complexity = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                         ast.With, ast.Assert, ast.comprehension)):
                        func_complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        func_complexity += len(child.values) - 1

                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': len(node.args.args),
                    'complexity': func_complexity,
                    'has_docstring': ast.get_docstring(node) is not None
                })
                metrics['complexity'] += func_complexity

            elif isinstance(node, ast.ClassDef):
                metrics['classes'] += 1
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes.append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': len(methods),
                    'has_docstring': ast.get_docstring(node) is not None
                })

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics['imports'] += 1
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                else:
                    module = node.module or ''
                    imports.append(module)

        # Build report
        result = [
            "**Code Analysis Report**",
            "=" * 50,
            "",
            "**Metrics:**",
            f"  Total lines:      {metrics['lines']}",
            f"  Lines of code:    {metrics['lines_of_code']}",
            f"  Functions:        {metrics['functions']}",
            f"  Classes:          {metrics['classes']}",
            f"  Imports:          {metrics['imports']}",
            f"  Total complexity: {metrics['complexity']}",
            "",
        ]

        if functions:
            result.append("**Functions:**")
            for f in functions:
                doc_mark = "📝" if f['has_docstring'] else "⚠️"
                result.append(f"  {doc_mark} {f['name']}() - Line {f['line']}, {f['args']} args, complexity {f['complexity']}")
            result.append("")

        if classes:
            result.append("**Classes:**")
            for c in classes:
                doc_mark = "📝" if c['has_docstring'] else "⚠️"
                result.append(f"  {doc_mark} {c['name']} - Line {c['line']}, {c['methods']} methods")
            result.append("")

        if imports:
            result.append("**Imports:**")
            for imp in sorted(set(imports)):
                result.append(f"  • {imp}")
            result.append("")

        # Recommendations
        recommendations = []
        if any(not f['has_docstring'] for f in functions):
            recommendations.append("Add docstrings to functions without documentation")
        if any(not c['has_docstring'] for c in classes):
            recommendations.append("Add docstrings to classes without documentation")
        if any(f['complexity'] > 10 for f in functions):
            recommendations.append("Consider refactoring complex functions (complexity > 10)")
        if metrics['lines_of_code'] > 500:
            recommendations.append("Consider splitting large file into modules")

        if recommendations:
            result.append("**Recommendations:**")
            for rec in recommendations:
                result.append(f"  • {rec}")

        return "\n".join(result)

    def generate_docstring(self, code: str, style: str = "google") -> str:
        """
        Generate docstrings for Python functions/classes.

        Args:
            code: Python function or class code
            style: Docstring style - "google", "numpy", or "sphinx"

        Returns:
            Code with generated docstrings.
        """
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return f"Cannot generate docstrings for invalid Python.\n\n{self.validate_python(code)}"

        result = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Get function info
                name = node.name
                args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                returns = None

                # Check for return annotation
                if node.returns:
                    if isinstance(node.returns, ast.Name):
                        returns = node.returns.id
                    elif isinstance(node.returns, ast.Constant):
                        returns = str(node.returns.value)

                # Generate docstring based on style
                if style == "google":
                    docstring = self._google_docstring(name, args, returns)
                elif style == "numpy":
                    docstring = self._numpy_docstring(name, args, returns)
                else:  # sphinx
                    docstring = self._sphinx_docstring(name, args, returns)

                result.append(f"```python\ndef {name}(...):\n{docstring}\n```\n")

            elif isinstance(node, ast.ClassDef):
                name = node.name
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

                if style == "google":
                    docstring = f'    """\n    Brief description of {name}.\n\n    Attributes:\n        attr1: Description.\n\n    Methods:\n'
                    for m in methods[:5]:
                        if not m.startswith('_'):
                            docstring += f'        {m}: Description.\n'
                    docstring += '    """'
                else:
                    docstring = f'    """Brief description of {name}."""'

                result.append(f"```python\nclass {name}:\n{docstring}\n```\n")

        if not result:
            return "No functions or classes found to document."

        return "**Generated Docstrings:**\n\n" + "\n".join(result)

    def _google_docstring(self, name: str, args: List[str], returns: Optional[str]) -> str:
        lines = ['    """Brief description.', '']
        if args:
            lines.append('    Args:')
            for arg in args:
                lines.append(f'        {arg}: Description.')
            lines.append('')
        if returns:
            lines.append('    Returns:')
            lines.append(f'        {returns}: Description.')
            lines.append('')
        lines.append('    """')
        return '\n'.join(lines)

    def _numpy_docstring(self, name: str, args: List[str], returns: Optional[str]) -> str:
        lines = ['    """Brief description.', '', '    Parameters', '    ----------']
        for arg in args:
            lines.append(f'    {arg} : type')
            lines.append('        Description.')
        if returns:
            lines.extend(['', '    Returns', '    -------', f'    {returns}', '        Description.'])
        lines.append('    """')
        return '\n'.join(lines)

    def _sphinx_docstring(self, name: str, args: List[str], returns: Optional[str]) -> str:
        lines = ['    """Brief description.', '']
        for arg in args:
            lines.append(f'    :param {arg}: Description.')
            lines.append(f'    :type {arg}: type')
        if returns:
            lines.append(f'    :returns: Description.')
            lines.append(f'    :rtype: {returns}')
        lines.append('    """')
        return '\n'.join(lines)

    def diff_code(self, code1: str, code2: str) -> str:
        """
        Show differences between two code snippets.

        Args:
            code1: Original code
            code2: Modified code

        Returns:
            Diff showing changes.
        """
        lines1 = code1.split('\n')
        lines2 = code2.split('\n')

        result = ["**Code Diff:**", "=" * 50, "", "```diff"]

        # Simple line-by-line diff
        max_lines = max(len(lines1), len(lines2))

        for i in range(max_lines):
            line1 = lines1[i] if i < len(lines1) else None
            line2 = lines2[i] if i < len(lines2) else None

            if line1 == line2:
                result.append(f"  {line1}")
            elif line1 is None:
                result.append(f"+ {line2}")
            elif line2 is None:
                result.append(f"- {line1}")
            else:
                result.append(f"- {line1}")
                result.append(f"+ {line2}")

        result.append("```")

        # Summary
        additions = len([l for l in result if l.startswith('+ ')])
        deletions = len([l for l in result if l.startswith('- ')])

        result.extend([
            "",
            f"**Summary:** {additions} addition(s), {deletions} deletion(s)"
        ])

        return "\n".join(result)

    def count_lines(self, code: str, language: str = "auto") -> str:
        """
        Count lines of code, comments, and blanks.

        Args:
            code: Code to analyze
            language: Programming language (auto, python, js, etc.)

        Returns:
            Line count statistics.
        """
        lines = code.split('\n')
        total = len(lines)
        blank = 0
        comment = 0
        code_lines = 0

        # Detect comment patterns based on language
        if language == "auto":
            if 'def ' in code or 'import ' in code:
                language = "python"
            elif 'function ' in code or 'const ' in code:
                language = "javascript"
            else:
                language = "generic"

        comment_patterns = {
            "python": (r'^\s*#', r'^\s*"""', r'^\s*\'\'\''),
            "javascript": (r'^\s*//', r'^\s*/\*'),
            "generic": (r'^\s*//', r'^\s*#', r'^\s*/\*'),
        }

        patterns = comment_patterns.get(language, comment_patterns["generic"])

        in_multiline = False
        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank += 1
            elif in_multiline:
                comment += 1
                if '"""' in stripped or "'''" in stripped or '*/' in stripped:
                    in_multiline = False
            elif any(re.match(p, line) for p in patterns):
                comment += 1
                if '"""' in stripped or "'''" in stripped or '/*' in stripped:
                    if not (stripped.count('"""') >= 2 or stripped.count("'''") >= 2 or '*/' in stripped):
                        in_multiline = True
            else:
                code_lines += 1

        result = [
            "**Line Count Analysis:**",
            "=" * 40,
            "",
            f"Language:      {language}",
            "",
            f"Total lines:   {total:>6}",
            f"Code lines:    {code_lines:>6}  ({100*code_lines/total:.1f}%)" if total > 0 else f"Code lines:    {code_lines:>6}",
            f"Comments:      {comment:>6}  ({100*comment/total:.1f}%)" if total > 0 else f"Comments:      {comment:>6}",
            f"Blank lines:   {blank:>6}  ({100*blank/total:.1f}%)" if total > 0 else f"Blank lines:   {blank:>6}",
        ]

        return "\n".join(result)

    def minify_json(self, json_str: str) -> str:
        """
        Minify JSON by removing whitespace.

        Args:
            json_str: JSON to minify

        Returns:
            Minified JSON.
        """
        try:
            parsed = json.loads(json_str)
            minified = json.dumps(parsed, separators=(',', ':'))

            original_size = len(json_str)
            minified_size = len(minified)
            savings = original_size - minified_size

            result = [
                "✅ JSON minified.",
                "",
                f"Original:  {original_size} bytes",
                f"Minified:  {minified_size} bytes",
                f"Saved:     {savings} bytes ({100*savings/original_size:.1f}%)" if original_size > 0 else "",
                "",
                "```json",
                minified[:500] + ("..." if len(minified) > 500 else ""),
                "```"
            ]

            return "\n".join(result)

        except json.JSONDecodeError as e:
            return f"Cannot minify invalid JSON: {e}"

    def check_availability(self) -> str:
        """Check tool capabilities."""
        return """**Code Analysis Tool - Available Functions:**

**Validation:**
  • validate_python(code) - Check Python syntax
  • validate_json(json_str) - Check JSON syntax

**Formatting:**
  • format_python(code) - Format Python code
  • format_json(json_str) - Format JSON
  • minify_json(json_str) - Minify JSON

**Analysis:**
  • analyze_python(code) - Complexity analysis
  • count_lines(code) - Line count statistics
  • diff_code(code1, code2) - Compare code

**Documentation:**
  • generate_docstring(code, style) - Generate docstrings
    Styles: google, numpy, sphinx"""
