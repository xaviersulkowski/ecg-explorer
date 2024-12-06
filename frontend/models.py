from dataclasses import dataclass

from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector


@dataclass
class AxProperties:
    ax: plt.Axes
    line: plt.Line2D
    span_selector: SpanSelector
