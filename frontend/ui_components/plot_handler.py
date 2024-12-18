import logging
import math
import tkinter as tk
from enum import Enum

import numpy as np
import matplotlib.pyplot as plt

from typing import Optional
from tkinter import messagebox
from matplotlib.backend_bases import MouseEvent, KeyEvent
from matplotlib.backends._backend_tk import NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from matplotlib.widgets import SpanSelector, Cursor

from frontend.annotated_cursor import AnnotatedCursor
from frontend.constants import APP_TITTLE
from frontend.observers.annotations_manager import AnnotationsManager, AnnotationEvents
from frontend.observers.container_manager import ContainerManager, ContainerEvents
from frontend.observers.filter_config_manager import FilterManager, FilterEvents
from frontend.observers.leads_manager import LeadsManager, LeadEvents
from frontend.models import AxProperties
from frontend.observers.observer_abc import Observer
from frontend.span.span import Span
from frontend.span.spans_manager import SpanManager
from frontend.utils import do_annotations_overlap
from models.annotation import QRSComplex
from models.ecg import LeadName, ECGLead


class ECGPlotHandler(tk.Frame, Observer):
    X_ECG_GRID_IN_MS = 200
    ECG_PLOT_PACK_CONFIG = {"fill": tk.BOTH, "side": tk.TOP, "expand": True}

    def __init__(
        self,
        parent: tk.Frame,
        leads_manager: LeadsManager,
        annotations_manager: AnnotationsManager,
        container_manager: ContainerManager,
        filter_manager: FilterManager,
        *args,
        **kwargs,
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # ====== widgets ======
        self.fig: plt.Figure = plt.figure()

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        NavigationToolbar2Tk(self.canvas)
        self.canvas.get_tk_widget().pack(**self.ECG_PLOT_PACK_CONFIG)

        # ====== subjects ======
        self.annotations_manager = annotations_manager
        self.annotations_manager.add_subscriber(self)

        self.leads_manager = leads_manager
        self.leads_manager.add_subscriber(self)

        self.container_manager = container_manager
        self.container_manager.add_subscriber(self)

        self.filter_manager = filter_manager
        self.filter_manager.add_subscriber(self)

        # ====== app variables ======
        self.ax_properties: dict[LeadName, AxProperties] = {}
        self.span_managers: dict[LeadName, SpanManager] = {}
        self.cursors: dict[str, Cursor] = {}

        # mouse event that helps to handle actions when a span is selected
        self.mouse_event: Optional[MouseEvent] = None

        self.canvas.mpl_connect("button_press_event", self._select_and_highlight_span)
        self.canvas.mpl_connect("key_press_event", self._handle_key_press_event)

    @classmethod
    def empty(
        cls,
        parent: tk.Frame,
        leads_manager: LeadsManager,
        annotations_manager: AnnotationsManager,
        container_manager: ContainerManager,
        filter_manager: FilterManager,
    ):
        """
        Factory method to create an empty ECGPlotHandler instance.
        """
        return ECGPlotHandler(
            parent,
            leads_manager,
            annotations_manager,
            container_manager,
            filter_manager,
        )

    def update_on_notification(self, event: Enum, *args, **kwargs):
        logging.info(f"Received {event.name} event in ECGPlotHandler")

        if event == ContainerEvents.CONTAINER_UPDATE:
            self._update_plot()

        if event == FilterEvents.DISPLAY_CONFIG_UPDATE:
            self._update_plot()

        if event == AnnotationEvents.ANNOTATIONS_UPDATE:
            # remove existing span artists and draw new ones
            self._update_plot()

        if event == AnnotationEvents.ANNOTATIONS_DELETE:
            # just re-draw waveform
            self._clear_all_spans()

        if event == LeadEvents.LEADS_SELECTION_UPDATE:
            self._update_plot()

    def _update_plot(self):
        """
       Recreate subplots for selected leads and synchronize spans with annotations.
       """
        self.plot_waveforms_for_selected_leads()
        self.synchronize_spans_with_annotations()
        self.canvas.draw_idle()

    def _clear_all_spans(self):
        """
        Clear all spans from the plot and reset annotations.
        """
        logging.info("Clearing existing annotations before re-drawing")
        for manager in self.span_managers.values():
            manager.clear_spans()
        self.canvas.draw_idle()

    def synchronize_spans_with_annotations(self):
        """
        Synchronize the spans on the plot with the data in AnnotationsManager.
        """
        for lead, annotations in self.annotations_manager.annotations.items():
            if lead in self.span_managers:
                self.span_managers[lead].synchronize_with_data(annotations)

    def plot_waveforms_for_selected_leads(self):
        leads = self.leads_manager.selected_leads
        show_processed_signal = self.filter_manager.show_filtered

        self._create_subplots(leads)

        self.cursors.clear()
        for lead_name, ax_props in self.ax_properties.items():
            lead = self.leads_manager.get_lead(lead_name)
            self._plot_waveform(lead, ax_props.ax, ax_props.line, show_processed_signal)

            cursor = AnnotatedCursor(
                line=ax_props.line,
                ax=ax_props.ax,
                numberformat="{0:.2f}[s]\n{1:.2f}[mV]",
                dataaxis="x",
                offset=[10, 10],
                textprops={"color": "black", "fontweight": "normal"},
                useblit=False,
                color="grey",
                linewidth=1,
                fs=lead.fs,
            )
            self.cursors[lead.label] = cursor

            self.span_managers[lead.label] = SpanManager(ax_props.ax)

        self.canvas.draw_idle()
        self.canvas.get_tk_widget().pack(**self.ECG_PLOT_PACK_CONFIG)

    def _on_select_with_axes(self, ax: plt.Axes):
        def on_select(*positions: (float, float)):
            lead_name = ax.get_title()
            ax_props = self.ax_properties[lead_name]
            self._set_selected_span(lead_name, ax_props.ax, *positions)

        return on_select

    def _set_selected_span(
        self, lead_name: str, ax: plt.Axes, onset: float, offset: float
    ):
        if onset == offset:
            logging.info("Onset == offset. Span not selected")
            return

        onset, offset = min(onset, offset), max(onset, offset)
        lead = self.leads_manager.get_lead(lead_name)
        fs = lead.fs

        onset = int(onset / 1000 * fs)
        offset = int(offset / 1000 * fs)

        # find overlapping QRS with selected span
        overlapping = [
            True
            if do_annotations_overlap(onset, offset, x.onset, x.offset) is True
            else False
            for x in self.annotations_manager.annotations[lead.label]
        ]

        if len([i for i in overlapping if i is True]) > 1:
            tk.messagebox.showwarning(
                title=APP_TITTLE,
                message="Your selection cannot overlap with multiple QRS complexes",
            )
            return

        qrs_complex = QRSComplex(onset, offset)

        if any(overlapping):
            # if span overlaps then we need to remove the span and associated Polygon
            self.annotations_manager.annotations[lead.label][overlapping.index(True)] = qrs_complex
            self.span_managers[lead.label].spans[overlapping.index(True)].update(onset, offset)
        else:
            span = Span(onset, offset, ax)
            self.annotations_manager.annotations[lead.label].append(qrs_complex)
            self.span_managers[lead.label].spans.append(span)

        self.canvas.draw_idle()

    def _create_subplots(self, leads: list[ECGLead]):
        self.fig.clear()
        self.ax_properties.clear()
        self.span_managers.clear()

        n_subplots = len(leads) if leads else 1
        n_columns = 2 if n_subplots > 3 else 1
        n_rows = math.ceil(n_subplots / n_columns)

        # axes: dict[LeadName, AxProperties] = {}

        for i, lead in enumerate(leads):
            ax = self.fig.add_subplot(n_rows, n_columns, i + 1)

            if i > 0:
                ax.sharex(list(self.ax_properties.values())[0].ax)

            (line,) = ax.plot([], [])

            span_selector = SpanSelector(
                ax,
                self._on_select_with_axes(ax),
                direction="horizontal",
                useblit=True,
                props=dict(alpha=0.5, facecolor="red"),
                interactive=True,
                minspan=10,
            )

            self.ax_properties[lead.label] = AxProperties(ax, line, span_selector)

        # need to set tight layout after each fig redrawing
        self.fig.tight_layout()

    def _plot_waveform(
        self,
        lead: ECGLead,
        ax: plt.Axes,
        line: plt.Line2D,
        show_processed_signal: bool = False,
    ):
        waveform = lead.waveform if show_processed_signal else lead.raw_waveform

        # scale to milli-volts
        if lead.units == "uV":
            waveform = waveform / 1000
        else:
            raise RuntimeError("Unit not known")

        line.set_data(range(len(waveform)), waveform)

        x = np.arange(0, len(waveform), self.X_ECG_GRID_IN_MS * lead.fs / 1000)
        x_ticks = x / lead.fs
        ax.set_xticks(x)
        ax.set_xlim(0, len(waveform))
        ax.set_xticklabels(x_ticks)
        ax.xaxis.set_tick_params(labelsize=9)

        y_min_round_half_down = (
            round(
                (min(waveform) - (0.5 if (abs(min(waveform)) * 2 % 1) < 0.5 else 0)) * 2
            )
            / 2
        )
        y_max_round_half_up = (
            round((max(waveform) + (0.5 if (max(waveform) * 2 % 1) < 0.5 else 0)) * 2)
            / 2
        )

        y = np.arange(y_min_round_half_down - 1, y_max_round_half_up + 1, 0.5)
        ax.set_yticks(y)
        ax.set_ylim(y_min_round_half_down - 0.1, y_max_round_half_up + 0.1)
        ax.yaxis.set_tick_params(labelsize=9)

        ax.xaxis.set_minor_locator(AutoMinorLocator(5))
        ax.yaxis.set_minor_locator(MultipleLocator(0.1))

        ax.grid(which="major", linestyle="-", linewidth="0.5", color="red")
        ax.grid(which="minor", linestyle="-", linewidth="0.5", color=(1, 0.7, 0.7))

        ax.set_title(f"{lead.label}", x=0.01, y=0.9, transform=ax.transAxes, ha="left")
        ax.set_ylabel(f"mV", fontsize=10)
        ax.set_xlabel(f"seconds", fontsize=10)
        ax.label_outer()

    def _select_and_highlight_span(self, event: tk.Event):
        """
        Handle double-click events to highlight or unhighlight spans.

        Parameters
        ----------
        event : MouseEvent
            The mouse event triggering the action.
        """
        if not isinstance(event, MouseEvent):
            return

        logging.info(f"Mouse event started, is dbclick {event.dblclick}, is inaxes {event.inaxes}")

        if not event.dblclick or event.inaxes is None:
            return

        logging.info(f"Mouse event at point: {event.xdata}")

        self.mouse_event = event

        ax = event.inaxes
        for lead, manager in self.span_managers.items():
            if manager.ax == ax:
                # Find the span under the mouse cursor
                for span in manager.get_spans():
                    if span.onset <= event.xdata <= span.offset:
                        if span.is_highlighted:
                            span.remove_highlight()
                            self.mouse_event = None
                        else:
                            span.highlight()

        self.canvas.draw_idle()

    def _handle_key_press_event(self, event: KeyEvent):
        if self.mouse_event is None:
            return

        if event.key == "ctrl+d" and self.mouse_event.xdata is not None:
            self._delete_selected_span()

    def _delete_selected_span(self):

        if sum([len(x.spans) for x in self.span_managers.values()]) == 0:
            return

        i = None
        selected_lead = self.mouse_event.inaxes.axes.get_title()

        if len(self.span_managers[selected_lead].spans) == 0:
            return

        for cnt, pos in enumerate(self.span_managers[selected_lead].spans):
            if pos.onset < self.mouse_event.xdata < pos.offset:
                i = cnt
                break

        self.span_managers[selected_lead].remove_span_by_index(i)
        self.annotations_manager.annotations[selected_lead].pop(i)

        self.mouse_event = None
        self.canvas.draw_idle()
