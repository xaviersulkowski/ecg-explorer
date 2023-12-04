from typing import Optional

import matplotlib.pyplot as plt

from dataclasses import dataclass, InitVar, field


@dataclass
class Span:
    onset: int
    offset: int
    ax: InitVar[plt.Axes]
    visibility: InitVar[bool] = True
    _span_artist: Optional[plt.Polygon] = field(init=False)

    def __post_init__(self, ax, visibility):
        self._span_artist = ax.axvspan(
            self.onset,
            self.offset,
            facecolor=(1, 0, 0, 0.5),
            lw=2,
        )

        self._span_artist.set_visible(visibility)

    def set_visible(self, status: bool):
        self._span_artist.set_visible(status)

    def highlight(self):
        self._span_artist.set_facecolor((0, 1, 0, 0.5))

    def remove_highlight(self):
        self._span_artist.set_facecolor((1, 0, 0, 0.5))

    def remove(self):
        self._span_artist.remove()
