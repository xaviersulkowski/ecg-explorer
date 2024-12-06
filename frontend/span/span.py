from dataclasses import dataclass, field
from typing import Optional
import matplotlib.pyplot as plt


@dataclass
class Span:
    onset: int
    offset: int
    ax: plt.Axes
    is_highlighted: bool = False
    _span_artist: Optional[plt.Polygon] = field(init=False, default=None)

    def __post_init__(self):
        self._span_artist = self.ax.axvspan(
            self.onset, self.offset, facecolor=(1, 0, 0, 0.5), lw=2
        )
        self._span_artist.set_visible(True)

    def update(self, onset, offset):

        self.onset = onset
        self.offset = offset

        if self._span_artist:
            xy = self._span_artist.get_xy()

            xy[0, 0] = onset
            xy[1, 0] = onset
            xy[2, 0] = offset
            xy[3, 0] = offset
            xy[4, 0] = onset
            self._span_artist.set_xy(xy)

    def set_visible(self, visibility: bool):
        if self._span_artist:
            self._span_artist.set_visible(visibility)

    def highlight(self):
        if self._span_artist:
            self._span_artist.set_facecolor((0, 1, 0, 0.5))
            self.is_highlighted = True

    def remove_highlight(self):
        if self._span_artist:
            self._span_artist.set_facecolor((1, 0, 0, 0.5))
            self.is_highlighted = False

    def remove_artist(self):
        if self._span_artist:
            self._span_artist.set_visible(False)
            self._span_artist.remove()
            self._span_artist = None

    def set_draggable(self, ax: plt.Axes):
        self._drag_start = None
        self._resize_edge = None

        def on_press(event):
            if not self._span_artist or not event.inaxes == ax:
                return

            contains, _ = self._span_artist.contains(event)
            if contains:
                if abs(event.xdata - self.onset) < abs(event.xdata - self.offset):
                    self._resize_edge = 'left'
                else:
                    self._resize_edge = 'right'
                self._drag_start = event.xdata

        def on_motion(event):
            if not self._drag_start or not self._resize_edge or not event.xdata:
                return

            dx = event.xdata - self._drag_start
            if self._resize_edge == 'left':
                self.onset += dx
            elif self._resize_edge == 'right':
                self.offset += dx
            self._drag_start = event.xdata
            self.update()

        def on_release(event):
            self._drag_start = None
            self._resize_edge = None

        ax.figure.canvas.mpl_connect('button_press_event', on_press)
        ax.figure.canvas.mpl_connect('motion_notify_event', on_motion)
        ax.figure.canvas.mpl_connect('button_release_event', on_release)
