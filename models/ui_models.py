import logging
from dataclasses import dataclass, field
from typing import Optional

from matplotlib import pyplot as plt
from matplotlib.widgets import SpanSelector


@dataclass
class Span:
    onset: int
    offset: int
    # TODO: this is meh, b/c we re-create artist every time we create new Axes
    _span_artist: Optional[plt.Polygon] = field(init=False, default=None)

    def create_artist(self, ax: plt.Axes, visibility: bool = True):
        self._span_artist = ax.axvspan(
            self.onset,
            self.offset,
            facecolor=(1, 0, 0, 0.5),
            lw=2,
        )

        self._span_artist.set_visible(visibility)

    def set_visible(self, visibility: bool):
        if self._span_artist is None:
            logging.warning(
                f"Span {self}, does not have span artist created. Ignoring `set_visible`..."
            )
            return

        self._span_artist.set_visible(visibility)

    def highlight(self):
        if self._span_artist is None:
            logging.warning(
                f"Span {self}, does not have span artist created. Ignoring `highlight`... "
            )
            return

        self._span_artist.set_facecolor((0, 1, 0, 0.5))

    def remove_highlight(self):
        if self._span_artist is None:
            logging.warning(
                f"Span {self}, does not have span artist created. Ignoring `remove_highlight`..."
            )
            return

        self._span_artist.set_facecolor((1, 0, 0, 0.5))

    def remove_artist(self):
        if self._span_artist is None:
            logging.warning(
                f"Span {self}, does not have span artist created. Ignoring `remove`..."
            )
            return

        if self._span_artist.figure is None:
            return

        self._span_artist.set_visible(False)
        self._span_artist.remove()


@dataclass
class AxProperties:
    ax: plt.Axes
    line: plt.Line2D
    span_selector: SpanSelector
