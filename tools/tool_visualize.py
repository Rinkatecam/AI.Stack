"""
title: Data Visualization Tool
version: 2.0.0
description: Generate charts, graphs, and molecular structures. Displays inline in chat with download option.
author: AI.STACK
author_url: https://github.com/Rinkatecam/aistack
requirements: pydantic, matplotlib, numpy, pillow

# SYSTEM PROMPT FOR AI
# ====================
# Generate visualizations from data.
# Charts display INLINE in chat AND are saved for download.
#
# CHART TYPES:
#   bar_chart, line_chart, pie_chart
#   histogram, scatter_plot, box_plot
#   comparison_chart, heatmap
#   draw_molecule (requires rdkit)
"""

import os
import json
import base64
import io
import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from rdkit import Chem
    from rdkit.Chem import Draw, AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from PIL import Image


STYLE_CONFIG = {
    "primary_color": "#2563EB",
    "secondary_color": "#3B82F6",
    "success_color": "#10B981",
    "warning_color": "#F59E0B",
    "error_color": "#EF4444",
    "palette": ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"],
    "title_fontsize": 14,
    "label_fontsize": 11,
    "tick_fontsize": 10,
    "legend_fontsize": 10,
    "figure_width": 10,
    "figure_height": 6,
    "dpi": 150,
    "background_color": "#FFFFFF",
    "grid_color": "#E5E7EB",
    "text_color": "#1F2937",
    "border_color": "#D1D5DB",
}


def _setup_style():
    if not MATPLOTLIB_AVAILABLE:
        return
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update({
        'figure.facecolor': STYLE_CONFIG["background_color"],
        'axes.facecolor': STYLE_CONFIG["background_color"],
        'axes.edgecolor': STYLE_CONFIG["border_color"],
        'axes.labelcolor': STYLE_CONFIG["text_color"],
        'text.color': STYLE_CONFIG["text_color"],
        'xtick.color': STYLE_CONFIG["text_color"],
        'ytick.color': STYLE_CONFIG["text_color"],
        'grid.color': STYLE_CONFIG["grid_color"],
        'grid.linestyle': '--',
        'grid.alpha': 0.7,
        'font.family': 'sans-serif',
        'font.size': STYLE_CONFIG["tick_fontsize"],
    })


def _get_output_dir() -> str:
    if os.path.exists("/data/user-files"):
        output_dir = "/data/user-files/charts"
    else:
        output_dir = os.path.expanduser("~/ai-stack/charts")
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _generate_filename(chart_type: str, title: str = "") -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
    if safe_title:
        return f"{chart_type}_{safe_title}_{timestamp}.png"
    return f"{chart_type}_{timestamp}.png"


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=STYLE_CONFIG["dpi"],
                bbox_inches='tight', facecolor=STYLE_CONFIG["background_color"])
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    return img_base64


def _save_figure(fig, chart_type: str, title: str = "") -> str:
    output_dir = _get_output_dir()
    filename = _generate_filename(chart_type, title)
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, format='png', dpi=STYLE_CONFIG["dpi"],
                bbox_inches='tight', facecolor=STYLE_CONFIG["background_color"])
    return filepath


def _create_response(fig, chart_type: str, title: str = "") -> str:
    img_base64 = _fig_to_base64(fig)
    filepath = _save_figure(fig, chart_type, title)
    plt.close(fig)
    response = f"![{title or chart_type}](data:image/png;base64,{img_base64})\n\n"
    response += f"**Download:** `{filepath}`"
    return response


def _parse_data(data: str) -> Union[Dict, List]:
    if isinstance(data, (dict, list)):
        return data
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON data: {e}")


def _add_watermark(fig, ax):
    fig.text(0.99, 0.01, 'AI Stack', fontsize=8, color='#9CA3AF',
             ha='right', va='bottom', alpha=0.5)


class Tools:
    class Valves(BaseModel):
        default_width: int = Field(default=10, description="Chart width in inches")
        default_height: int = Field(default=6, description="Chart height in inches")
        show_grid: bool = Field(default=True, description="Show grid lines")
        color_scheme: str = Field(default="blue", description="Color scheme: blue, green, rainbow")

    def __init__(self):
        self.citation = False
        self.valves = self.Valves()
        _setup_style()

    def _get_colors(self, count: int) -> List[str]:
        scheme = self.valves.color_scheme
        if scheme == "green":
            base_colors = ["#10B981", "#059669", "#047857", "#065F46", "#064E3B"]
        elif scheme == "rainbow":
            base_colors = STYLE_CONFIG["palette"]
        else:
            base_colors = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"]
        return [base_colors[i % len(base_colors)] for i in range(count)]

    def bar_chart(self, data: str, title: str = "Bar Chart",
                  xlabel: str = "", ylabel: str = "Value", horizontal: bool = False) -> str:
        """
        Create a bar chart.

        Args:
            data: JSON object with labels and values: '{"A": 10, "B": 20}'
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            horizontal: If True, horizontal bars

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            parsed = _parse_data(data)
            if not isinstance(parsed, dict):
                return "Error: Data must be a JSON object"

            labels = list(parsed.keys())
            values = list(parsed.values())
            colors = self._get_colors(len(labels))

            fig, ax = plt.subplots(figsize=(self.valves.default_width, self.valves.default_height))

            if horizontal:
                bars = ax.barh(labels, values, color=colors, edgecolor='white', linewidth=1)
                ax.set_xlabel(ylabel)
                ax.set_ylabel(xlabel)
            else:
                bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=1)
                ax.set_xlabel(xlabel)
                ax.set_ylabel(ylabel)

            ax.set_title(title, fontweight='bold', pad=15)
            ax.grid(self.valves.show_grid, axis='y' if not horizontal else 'x', alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "bar_chart", title)

        except Exception as e:
            return f"Error creating bar chart: {str(e)}"

    def line_chart(self, data: str, title: str = "Line Chart",
                   xlabel: str = "", ylabel: str = "Value",
                   show_points: bool = True, fill: bool = False) -> str:
        """
        Create a line chart.

        Args:
            data: JSON object or array
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            show_points: Show data points
            fill: Fill area under line

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            parsed = _parse_data(data)
            fig, ax = plt.subplots(figsize=(self.valves.default_width, self.valves.default_height))
            colors = self._get_colors(10)

            if isinstance(parsed, dict):
                first_val = list(parsed.values())[0]
                if isinstance(first_val, list):
                    for i, (series_name, values) in enumerate(parsed.items()):
                        x = range(len(values))
                        ax.plot(x, values, color=colors[i], linewidth=2,
                               marker='o' if show_points else None, markersize=6, label=series_name)
                        if fill:
                            ax.fill_between(x, values, alpha=0.2, color=colors[i])
                    ax.legend()
                else:
                    labels = list(parsed.keys())
                    values = list(parsed.values())
                    ax.plot(labels, values, color=colors[0], linewidth=2,
                           marker='o' if show_points else None, markersize=8)
                    if fill:
                        ax.fill_between(range(len(values)), values, alpha=0.2, color=colors[0])
            elif isinstance(parsed, list):
                ax.plot(parsed, color=colors[0], linewidth=2,
                       marker='o' if show_points else None, markersize=8)
                if fill:
                    ax.fill_between(range(len(parsed)), parsed, alpha=0.2, color=colors[0])

            ax.set_title(title, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(self.valves.show_grid, alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "line_chart", title)

        except Exception as e:
            return f"Error creating line chart: {str(e)}"

    def pie_chart(self, data: str, title: str = "Pie Chart",
                  show_percentages: bool = True, explode_largest: bool = False) -> str:
        """
        Create a pie chart.

        Args:
            data: JSON object: '{"A": 30, "B": 70}'
            title: Chart title
            show_percentages: Show percentage labels
            explode_largest: Highlight largest slice

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            parsed = _parse_data(data)
            if not isinstance(parsed, dict):
                return "Error: Data must be a JSON object"

            labels = list(parsed.keys())
            values = list(parsed.values())
            colors = self._get_colors(len(labels))

            explode = [0] * len(values)
            if explode_largest:
                max_idx = values.index(max(values))
                explode[max_idx] = 0.05

            fig, ax = plt.subplots(figsize=(self.valves.default_height, self.valves.default_height))

            wedges, texts, autotexts = ax.pie(
                values, labels=labels, colors=colors,
                autopct='%1.1f%%' if show_percentages else None,
                explode=explode, startangle=90,
                wedgeprops={'edgecolor': 'white', 'linewidth': 2},
                textprops={'fontsize': STYLE_CONFIG["label_fontsize"]}
            )

            if show_percentages:
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')

            ax.set_title(title, fontweight='bold', pad=15)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "pie_chart", title)

        except Exception as e:
            return f"Error creating pie chart: {str(e)}"

    def histogram(self, data: str, title: str = "Histogram",
                  xlabel: str = "Value", ylabel: str = "Frequency",
                  bins: int = 10, show_stats: bool = True) -> str:
        """
        Create a histogram.

        Args:
            data: JSON array of numbers: '[1.2, 1.3, 1.1]'
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            bins: Number of bins
            show_stats: Show mean and std dev

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            parsed = _parse_data(data)
            if not isinstance(parsed, list):
                return "Error: Data must be a JSON array"

            values = [float(v) for v in parsed]
            colors = self._get_colors(1)

            fig, ax = plt.subplots(figsize=(self.valves.default_width, self.valves.default_height))
            ax.hist(values, bins=bins, color=colors[0], edgecolor='white', linewidth=1, alpha=0.8)

            ax.set_title(title, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(self.valves.show_grid, axis='y', alpha=0.3)

            if show_stats:
                mean = sum(values) / len(values)
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std = variance ** 0.5
                ax.axvline(mean, color=STYLE_CONFIG["error_color"], linestyle='--',
                          linewidth=2, label=f'Mean: {mean:.2f}')
                ax.legend(loc='upper right')

            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "histogram", title)

        except Exception as e:
            return f"Error creating histogram: {str(e)}"

    def scatter_plot(self, x_data: str, y_data: str, title: str = "Scatter Plot",
                     xlabel: str = "X", ylabel: str = "Y", show_trendline: bool = False) -> str:
        """
        Create a scatter plot.

        Args:
            x_data: JSON array of x values
            y_data: JSON array of y values
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            show_trendline: Show linear trendline

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            x = _parse_data(x_data)
            y = _parse_data(y_data)

            if not isinstance(x, list) or not isinstance(y, list):
                return "Error: Both x_data and y_data must be JSON arrays"

            if len(x) != len(y):
                return f"Error: x_data ({len(x)}) and y_data ({len(y)}) must have same length"

            x = [float(v) for v in x]
            y = [float(v) for v in y]
            colors = self._get_colors(1)

            fig, ax = plt.subplots(figsize=(self.valves.default_width, self.valves.default_height))
            ax.scatter(x, y, c=colors[0], s=80, alpha=0.7, edgecolors='white', linewidth=1)

            if show_trendline and NUMPY_AVAILABLE:
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                x_line = np.linspace(min(x), max(x), 100)
                ax.plot(x_line, p(x_line), color=STYLE_CONFIG["error_color"],
                       linestyle='--', linewidth=2, label=f'y = {z[0]:.2f}x + {z[1]:.2f}')
                ax.legend()

            ax.set_title(title, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(self.valves.show_grid, alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "scatter_plot", title)

        except Exception as e:
            return f"Error creating scatter plot: {str(e)}"

    def box_plot(self, data: str, title: str = "Box Plot",
                 xlabel: str = "", ylabel: str = "Value") -> str:
        """
        Create a box plot.

        Args:
            data: JSON object with arrays: '{"Group A": [1,2,3], "Group B": [2,3,4]}'
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label

        Returns:
            Inline image + download path.
        """
        if not MATPLOTLIB_AVAILABLE:
            return "Error: matplotlib not installed"

        try:
            parsed = _parse_data(data)
            if not isinstance(parsed, dict):
                return "Error: Data must be a JSON object with arrays"

            labels = list(parsed.keys())
            data_arrays = [parsed[label] for label in labels]
            colors = self._get_colors(len(labels))

            fig, ax = plt.subplots(figsize=(self.valves.default_width, self.valves.default_height))
            bp = ax.boxplot(data_arrays, labels=labels, patch_artist=True)

            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            ax.set_title(title, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.grid(self.valves.show_grid, axis='y', alpha=0.3)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "box_plot", title)

        except Exception as e:
            return f"Error creating box plot: {str(e)}"

    def draw_molecule(self, smiles: str, title: str = "") -> str:
        """
        Draw molecular structure from SMILES notation (requires RDKit).

        Args:
            smiles: SMILES string (e.g., "CCO" for ethanol)
            title: Optional title

        Returns:
            Inline molecular structure + download path.
        """
        if not RDKIT_AVAILABLE:
            return "Error: RDKit not installed. Install with: pip install rdkit"

        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return f"Error: Invalid SMILES string: '{smiles}'"

            AllChem.Compute2DCoords(mol)
            img = Draw.MolToImage(mol, size=(400, 400), kekulize=True, wedgeBonds=True)

            fig, ax = plt.subplots(figsize=(6, 6))
            ax.imshow(img)
            ax.axis('off')

            if title:
                ax.set_title(title, fontweight='bold', pad=10)

            fig.text(0.5, 0.02, f'SMILES: {smiles}', ha='center', fontsize=10, color='#6B7280')
            _add_watermark(fig, ax)
            plt.tight_layout()

            return _create_response(fig, "molecule", title or smiles[:20])

        except Exception as e:
            return f"Error drawing molecule: {str(e)}"

    def check_availability(self) -> str:
        """Check which visualization features are available."""
        status = ["Visualization Tool - Library Status", "=" * 40, ""]
        status.append(f"{'✅' if MATPLOTLIB_AVAILABLE else '❌'} matplotlib: {'Available' if MATPLOTLIB_AVAILABLE else 'Not installed'}")
        status.append(f"{'✅' if NUMPY_AVAILABLE else '⚠️'} numpy: {'Available' if NUMPY_AVAILABLE else 'Not installed'}")
        status.append(f"{'✅' if RDKIT_AVAILABLE else '⚠️'} rdkit: {'Available' if RDKIT_AVAILABLE else 'Not installed'}")

        status.extend([
            "", "Available chart types:",
            "  • bar_chart, line_chart, pie_chart",
            "  • histogram, scatter_plot, box_plot",
            "  • comparison_chart, heatmap",
        ])

        if RDKIT_AVAILABLE:
            status.append("  • draw_molecule")

        status.extend(["", f"Output directory: {_get_output_dir()}"])
        return "\n".join(status)
