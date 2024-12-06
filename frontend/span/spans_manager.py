from typing import List
from frontend.span.span import Span
import matplotlib.pyplot as plt

from models.annotation import QRSComplex


class SpanManager:
    """
    Manages the visualization and interaction of spans on a single matplotlib Axes.
    """

    def __init__(self, ax: plt.Axes):
        """
        Initialize the SpanManager for a given Axes.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The matplotlib Axes on which spans will be managed.
        """
        self.ax = ax
        self.spans: List[Span] = []  # List to hold all managed spans

    def add_span(self, onset: int, offset: int) -> Span:
        """
        Add a new span to the plot and display it.

        Parameters
        ----------
        onset : int
            The start position of the span (in X-axis units).
        offset : int
            The end position of the span (in X-axis units).
        Returns
        -------
        Span
            The created Span object.
        """
        span = Span(onset, offset, self.ax)
        span.set_draggable(self.ax)  # Enable interactivity
        self.spans.append(span)
        return span

    def remove_span_by_index(self, index: int):
        """
        Remove an existing span from the plot and the internal list.

        Parameters
        ----------
        index : int
            Index of span to be removed.
        """

        self.spans.pop(index).remove_artist()

    def clear_spans(self):
        """
        Clear all spans from the plot and reset the internal list.
        """
        for span in self.spans:
            span.remove_artist()
        self.spans.clear()

    def synchronize_with_data(self, spans_data: List[QRSComplex]):
        """
        Synchronize the current spans with provided data.

        Parameters
        ----------
        spans_data : List[Span]
            A list of Span objects to synchronize with.
        """
        self.clear_spans()  # Remove existing spans
        for data_span in spans_data:
            self.add_span(data_span.onset, data_span.offset)
        self.ax.figure.canvas.draw_idle()  # Redraw the canvas to reflect changes

    def get_spans(self) -> List[Span]:
        """
        Get the list of spans currently managed by the SpanManager.

        Returns
        -------
        List[Span]
            A list of all managed Span objects.
        """
        return self.spans
