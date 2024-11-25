import logging
import os
import math
import tkinter as tk
import matplotlib.pyplot as plt
import numpy as np

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from matplotlib.widgets import SpanSelector
from matplotlib.backend_bases import MouseEvent, KeyEvent
from tkinter import ttk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo
from typing import Optional, Callable

from explorer.ECGExplorer import ECGExplorer
from filters.ecg_signal_filter import FilterConfig, FilterMethods
from models.annotation import QRSComplex
from models.ecg import ECGContainer, ECGLead, LeadName
from models.ui_models import Span, AxProperties

APP_TITTLE = "ECG explorer"
matplotlib.use("Agg")

logging.basicConfig(level=logging.INFO)

class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        # ====== app variables ======
        self.container: Optional[ECGContainer] = None
        self.explorer: Optional[ECGExplorer] = None
        self.leads_mapping: dict[LeadName, int] = {}

        self.selected_leads_names = tk.Variable()
        self.selected_leads_names.trace_add("write", self._on_lead_change)
        self.selected_leads: Optional[list[ECGLead]] = None

        self.spans_per_lead: dict[LeadName, list[Span]] = {}

        self.show_processed_signal = tk.BooleanVar()
        self.show_processed_signal.set(True)

        self.file_path: Optional[str] = None
        self.file_name: Optional[str] = None
        self.app_filter_config = FilterConfig.default_bandpass()

        # ====== frames & widgets ======

        self.top_frame = TopFrame(self)

        ecg_plot_pack_config = {"fill": tk.BOTH, "side": tk.TOP, "expand": True}
        self.ecg_plot = ECGPlotHandler.empty(self, ecg_plot_pack_config)

        self.top_frame.pack(fill=tk.BOTH, side=tk.TOP)
        self.ecg_plot.pack(**ecg_plot_pack_config)

        self.bottom_frame = BottomFrame(self)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH)

    def _on_lead_change(self, *_):
        # 1. remove all existing span artists
        self.ecg_plot.clear_annotations()

        # 2. replot waveform
        self.replot_waveform_with_selected_leads()

    def replot_waveform_with_selected_leads(self):
        # 1. get selected leads
        selected_leads = [
            self.get_lead(lead_name) for lead_name in self.selected_leads_names.get()
        ]

        self.selected_leads = selected_leads

        # 2. re-draw waveforms and create new axes objects
        self.ecg_plot.plot_waveforms_for_selected_leads(
            self.selected_leads, self.show_processed_signal.get()
        )

        # 3. re-draw annotations if any
        self.ecg_plot.draw_annotations_for_selected_leads()

    def get_lead(self, lead_name: str) -> ECGLead:
        return self.container.ecg_leads[self.leads_mapping[lead_name]]

    def load_signal(self, filename: str):
        def enable_options_on_signal_load():
            self.top_frame.activate_widgets()
            self.bottom_frame.activate_widgets()

        self.explorer = ECGExplorer.load_from_file(filename, self.app_filter_config)
        self.container = self.explorer.container
        self.explorer.process()

        head, tail = os.path.split(filename)

        self.file_path = head
        self.file_name = tail.split(".")[0]

        enable_options_on_signal_load()

        self.leads_mapping = {
            x.label: cnt for cnt, x in enumerate(self.container.ecg_leads)
        }

        self.top_frame.reload_leads_menu(self.leads_mapping)

        self.selected_leads_names.set([list(self.leads_mapping.keys())[0]])

        self.selected_leads = [
            self.get_lead(self.selected_leads_names.get()[0]),
        ]

        self.ecg_plot.clear_annotations()
        self.spans_per_lead = {x.label: [] for x in self.container.ecg_leads}

        self.ecg_plot.update_ecg_container(self.container)
        self.ecg_plot.plot_waveforms_for_selected_leads(
            self.selected_leads, self.show_processed_signal.get()
        )

        self.top_frame.description_frame.update_description(self.container)

    def process_signal(self):
        self.explorer.process()
        showinfo(title=APP_TITTLE, message="Processing done!")

        for lead in self.container.ecg_leads:
            self.create_spans_from_qrs_annotations(lead)

        self.ecg_plot.draw_annotations_for_selected_leads()

    def clear_all_spans(self):
        self.ecg_plot.clear_annotations()
        for k in self.spans_per_lead.keys():
            self.spans_per_lead[k].clear()
        self.ecg_plot.draw_annotations_for_selected_leads()

    def create_spans_from_qrs_annotations(self, lead: ECGLead):
        """
        In case we process signal after we made some manual selections, we want to merge these two types of selections.
        Manual selections take precedence over these programmatically detected.
        """
        if lead.ann.qrs_complex_positions:
            for c in lead.ann.qrs_complex_positions:
                overlapping = [
                    True
                    if _do_spans_overlap(c.onset, c.offset, x.onset, x.offset) is True
                    else False
                    for x in self.spans_per_lead[lead.label]
                ]

                if not any(overlapping):
                    self.spans_per_lead[lead.label].append(
                        Span(
                            c.onset,
                            c.offset,
                        )
                    )

    def update_annotations_from_spans(self):
        for lead, spans in self.spans_per_lead.items():
            qrs = [QRSComplex(span.onset, span.offset) for span in spans]
            self.explorer.overwrite_annotations(lead, qrs)

    def generate_report(self):
        self.update_annotations_from_spans()

        df = self.explorer.generate_report()
        filename = fd.asksaveasfile(
            mode="w", initialfile=f"{self.file_name}.csv", defaultextension=".csv"
        )

        if filename is None:
            return

        df.to_csv(filename)

        showinfo(
            title=APP_TITTLE, message=f"Report generated and saved to {filename.name}"
        )

    def exit_main(self):
        self.parent.destroy()
        exit()


class TopFrame(tk.Frame):
    def __init__(self, parent: MainApplication, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.app = parent

        self.action_buttons_frame = ActionButtonsFrame(self)
        self.action_buttons_frame.pack(anchor=tk.NW, side=tk.LEFT, fill=tk.Y)

        self.description_frame = DescriptionFrame(self)
        self.description_frame.pack(
            anchor=tk.N, side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10, expand=True
        )

        self.leads_menu_frame = LeadsMenuFrame(self)
        self.leads_menu_frame.pack(
            anchor=tk.E,
            side=tk.RIGHT,
            padx=10,
            pady=10,
        )

    def activate_widgets(self):
        self.action_buttons_frame.activate_widgets()
        self.leads_menu_frame.activate_widgets()

    def reload_leads_menu(self, new_mapping):
        self.leads_menu_frame.reload_leads_menu(new_mapping)
        self.leads_menu_frame.leads_listbox.selection_set(0)


class DescriptionFrame(tk.Frame):
    PATH_PREFIX = "path: "

    def __init__(self, parent: TopFrame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.app = parent.app

        self.path = tk.Text(self, height=2)
        self._setup_text_container(self.path, self.PATH_PREFIX)

        self.description = tk.Text(self, height=2)
        self._setup_text_container(self.description, "")

    def update_description(self, container: ECGContainer):
        self._write_text(self.path, container.file_path, len(self.PATH_PREFIX))
        self._write_text(self.description, container.description, len(""))

    @staticmethod
    def _setup_text_container(text_c: tk.Text, prefix: str):
        text_c.insert(tk.END, "" + prefix)
        text_c.config(state=tk.DISABLED)
        text_c.pack()

    @staticmethod
    def _write_text(text_c: tk.Text, text: str, prefix_len: float):
        text_c.config(state=tk.NORMAL)
        text_c.delete(prefix_len + 1.0, tk.END)
        text_c.insert(tk.END, text)
        text_c.config(state=tk.DISABLED)


class ActionButtonsFrame(tk.Frame):
    def __init__(self, parent: TopFrame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.app = parent.app

        self.open_button = tk.Button(
            self, text="Select ECG file", command=self._select_file, bg="ivory4"
        )

        self.process_ecg_button = tk.Button(
            self,
            text="Detect QRS",
            command=self.app.process_signal,
            state=tk.DISABLED,
        )

        self.load_ann_button = tk.Button(
            self,
            text="Load annotations",
            command=self._load_annotations,
            state=tk.DISABLED,
        )

        self.clear_ann_button = tk.Button(
            self,
            text="Clear all annotations",
            command=self._clear_annotations,
            state=tk.DISABLED,
        )

        self.filters_setting_button = tk.Button(
            self,
            text="Filter settings",
            command=self.open_settings_window,
            state=tk.NORMAL,
        )

        self.processed_button = tk.Checkbutton(
            self,
            text="Show processed signal",
            variable=self.app.show_processed_signal,
            onvalue=1,
            offvalue=0,
            command=self.app.replot_waveform_with_selected_leads,
            state=tk.DISABLED,
        )

        self.open_button.grid(row=0, column=0, padx=5, pady=5, sticky="nesw")
        self.load_ann_button.grid(row=1, column=0, padx=5, pady=5, sticky="nesw")
        self.process_ecg_button.grid(row=0, column=1, padx=5, pady=5, sticky="nesw")
        self.clear_ann_button.grid(row=1, column=1, padx=5, pady=5, sticky="nesw")
        self.filters_setting_button.grid(row=2, column=0, padx=5, pady=5, sticky="nesw")
        self.processed_button.grid(row=3, column=0, padx=5, pady=5, sticky="nesw")

        self.filters_setting_window = None

    def open_settings_window(self):
        if self.filters_setting_window is None:
            self.filters_setting_window = FilterSettingsWindow(
                self,
                self.settings_window_on_close_callback,
                self.settings_window_filter_changed_callback,
            )

    def settings_window_filter_changed_callback(self):
        if self.app.container is not None:
            self.app.explorer.filter_config = self.app.app_filter_config
            self.app.explorer.process()
            self.app.replot_waveform_with_selected_leads()
        else:
            logging.info("No filter changes")

    def settings_window_on_close_callback(self):
        self.filters_setting_window = None

    def _select_file(self):
        filetypes = (("Dicom files", "*.dcm"), ("XML files", "*.Xml"))

        filename = fd.askopenfilename(
            title="Open a file", initialdir="./", filetypes=filetypes
        )

        if filename is None or filename == "" or filename == ():
            showinfo(title=APP_TITTLE, message="File not selected")
            return

        showinfo(title=APP_TITTLE, message="Successfully loaded file!")

        self.app.load_signal(filename)

    def _clear_annotations(self):
        should_continue = tk.messagebox.askyesno(
            title=APP_TITTLE,
            message="Do you want to delete all existing annotations?",
        )

        if not should_continue:
            return

        self.app.clear_all_spans()
        self.app.ecg_plot.draw_annotations_for_selected_leads()

    def _load_annotations(self):
        filetypes = (("annotation files", "*.annx"),)
        filename = fd.askopenfilename(title="Open a file", filetypes=filetypes)

        if filename is None or filename == "" or filename == ():
            showinfo(title=APP_TITTLE, message="File not selected")
            return

        should_continue = True
        if any(len(span) > 0 for span in self.app.spans_per_lead.values()):
            should_continue = tk.messagebox.askyesno(
                title=APP_TITTLE,
                message="Loading annotations from the file will overwrite existing annotations. Are you sure?",
            )

        if not should_continue:
            return

        self.app.explorer.load_annotations(filename)
        self.app.clear_all_spans()

        for lead in self.app.container.ecg_leads:
            self.app.create_spans_from_qrs_annotations(lead)

        self.app.ecg_plot.draw_annotations_for_selected_leads()

    def activate_widgets(self):
        self.process_ecg_button.configure(state=tk.NORMAL)
        self.load_ann_button.configure(state=tk.NORMAL)
        self.clear_ann_button.configure(state=tk.NORMAL)
        self.processed_button.configure(state=tk.NORMAL)


class BottomFrame(tk.Frame):
    def __init__(self, parent: MainApplication, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        self.save_annotations_button = tk.Button(
            self,
            text="Save annotations",
            state=tk.DISABLED,
            command=self._on_save_annotations,
        )

        self.generate_report_button = tk.Button(
            self,
            text="Generate report",
            state=tk.DISABLED,
            command=self.parent.generate_report,
        )

        self.quit = tk.Button(
            self,
            text="Quit",
            command=self.parent.exit_main,
            bg="ivory4",
        )

        self.save_annotations_button.pack(side=tk.LEFT, padx=10, pady=10)
        self.generate_report_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.quit.pack(side=tk.RIGHT, padx=10, pady=10)

    def _on_save_annotations(self):
        filename = fd.asksaveasfile(
            mode="w",
            initialfile=f"{self.parent.file_name}.annx",
            defaultextension=".annx",
        )

        if filename is None:
            return

        self.parent.update_annotations_from_spans()
        self.parent.explorer.save_annotations(filename.name)

        showinfo(title=APP_TITTLE, message=f"Annotations saved to {filename.name}")

    def activate_widgets(self):
        self.generate_report_button.configure(state=tk.NORMAL)
        self.save_annotations_button.configure(state=tk.NORMAL)


class LeadsMenuFrame(tk.Frame):
    def __init__(self, parent: TopFrame, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.app = parent.app

        self.leads_listbox = tk.Listbox(
            self, height=3, selectmode=tk.MULTIPLE, state=tk.DISABLED
        )

        scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.leads_listbox.yview,
        )
        self.leads_listbox["yscrollcommand"] = scrollbar.set

        self.select_buttons_frame = tk.Frame(self)

        self.select_all_button = tk.Button(
            self.select_buttons_frame,
            text="Select all",
            command=self._select_all_leads,
            state=tk.DISABLED,
        )

        self.clear_all_button = tk.Button(
            self.select_buttons_frame,
            text="Clear all",
            command=self._clear_all_leads,
            state=tk.DISABLED,
        )

        self.confirm_button = tk.Button(
            self,
            text="Confirm choices",
            command=self._on_confirm_button_click,
            state=tk.DISABLED,
        )

        self.select_all_button.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.clear_all_button.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        self.confirm_button.pack(expand=True, side=tk.BOTTOM, fill=tk.X)
        self.select_buttons_frame.pack(expand=True, side=tk.BOTTOM, fill=tk.X)
        self.leads_listbox.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, expand=True, fill=tk.Y)

    def _clear_all_leads(self):
        self.leads_listbox.selection_clear(0, self.leads_listbox.size())

    def _select_all_leads(self):
        self.leads_listbox.selection_set(0, self.leads_listbox.size())

    def reload_leads_menu(self, leads_mapping: dict[LeadName, int]):
        self.leads_listbox.delete(0, self.leads_listbox.size())
        for name, cnt in leads_mapping.items():
            self.leads_listbox.insert(cnt, name)

    def _on_confirm_button_click(self):
        currently_selected_idx = self.leads_listbox.curselection()
        currently_selected = [self.leads_listbox.get(i) for i in currently_selected_idx]

        if not currently_selected:
            tk.messagebox.showinfo(title=APP_TITTLE, message="No leads selected")
            return

        selected_leads = "\n-".join(currently_selected)
        msg = f"Currently selected leads:\n-{selected_leads}\n\nProceed?"

        should_continue = tk.messagebox.askyesno(title=APP_TITTLE, message=msg)

        if should_continue:
            self.app.selected_leads_names.set(currently_selected)

    def activate_widgets(self):
        self.leads_listbox.configure(state=tk.NORMAL)
        self.confirm_button.configure(state=tk.NORMAL)
        self.clear_all_button.configure(state=tk.NORMAL)
        self.select_all_button.configure(state=tk.NORMAL)


class ECGPlotHandler(tk.Frame):
    X_ECG_GRID_IN_MS = 200

    def __init__(self, parent: MainApplication, pack_config, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        # ====== widgets ======
        self.fig: plt.Figure = plt.figure()

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        NavigationToolbar2Tk(self.canvas)
        self.canvas.get_tk_widget().pack(**pack_config)

        # ====== app variables ======
        self.ecg_container: Optional[ECGContainer] = None
        self.ax_properties: Optional[dict[LeadName, AxProperties]] = None

        # mouse event that helps to handle actions when a span is selected
        self.mouse_event: Optional[MouseEvent] = None

        self.canvas.mpl_connect("button_press_event", self._select_and_highlight_span)
        self.canvas.mpl_connect("key_press_event", self._handle_key_press_event)

    @classmethod
    def empty(cls, parent: MainApplication, pack_config: dict):
        return ECGPlotHandler(parent, pack_config)

    def update_ecg_container(self, ecg_container: ECGContainer):
        self.ecg_container = ecg_container

    def plot_waveforms_for_selected_leads(
            self, leads: list[ECGLead], show_processed_signal: bool = False
    ):
        self._create_subplots(leads)

        for lead_name, ax_props in self.ax_properties.items():
            lead = self.parent.get_lead(lead_name)
            self._plot_waveform(lead, ax_props.ax, ax_props.line, show_processed_signal)

        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, side=tk.TOP, expand=True)

    def _on_select_with_axes(self, ax: plt.Axes):
        def on_select(*positions: (float, float)):
            lead_name = ax.get_title()
            ax_props = self.ax_properties[lead_name]
            self._set_selected_span(lead_name, ax_props.ax, *positions)

        return on_select

    def clear_annotations(self):
        if not len(self.parent.spans_per_lead) > 0:
            return

        for spans in self.parent.spans_per_lead.values():
            for span in spans:
                span.remove_artist()

        self.canvas.draw()

    def _set_selected_span(
            self, lead_name: str, ax: plt.Axes, onset: float, offset: float
    ):
        if onset == offset:
            return

        onset, offset = min(onset, offset), max(onset, offset)
        lead = self.parent.get_lead(lead_name)
        fs = lead.fs

        onset = int(onset / 1000 * fs)
        offset = int(offset / 1000 * fs)

        # find overlapping QRS with selected span
        overlapping = [
            True
            if _do_spans_overlap(onset, offset, x.onset, x.offset) is True
            else False
            for x in self.parent.spans_per_lead[lead.label]
        ]

        if len([i for i in overlapping if i is True]) > 1:
            tk.messagebox.showwarning(
                title=APP_TITTLE,
                message="Your selection cannot overlap with multiple QRS complexes",
            )
            return

        if any(overlapping):
            # if span overlaps then we need to remove the span and associated Polygon
            self.parent.spans_per_lead[lead.label].pop(
                overlapping.index(True)
            ).remove_artist()

        span = Span(onset, offset)
        span.create_artist(ax)

        self.parent.spans_per_lead[lead.label].append(span)
        self.canvas.draw()

    def _create_subplots(self, leads: list[ECGLead]):
        self.fig.clear()

        n_subplots = len(leads)
        n_columns = 2 if n_subplots > 3 else 1
        n_rows = math.ceil(n_subplots / n_columns)

        axes: dict[LeadName, AxProperties] = {}

        for i, lead in enumerate(leads):
            ax = self.fig.add_subplot(n_rows, n_columns, i + 1)

            if i > 0:
                ax.sharex(list(axes.values())[0].ax)

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

            axes[lead.label] = AxProperties(ax, line, span_selector)

        # need to set tight layout after each fig redrawing
        self.fig.tight_layout()

        self.ax_properties = axes

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

    def draw_annotations_for_selected_leads(self):
        for lead in self.parent.selected_leads:
            if self.parent.spans_per_lead.get(lead.label) is not None:
                for span in self.parent.spans_per_lead[lead.label]:
                    ax_props = self.ax_properties[lead.label]
                    span.create_artist(ax_props.ax)

        self.canvas.draw()

    def _select_and_highlight_span(self, event: tk.Event):
        if not isinstance(event, MouseEvent):
            return

        if event.dblclick:
            self.mouse_event = event
            selected_lead = self.mouse_event.inaxes.axes.get_title()

            for span in self.parent.spans_per_lead[selected_lead]:
                if span.onset <= self.mouse_event.xdata <= span.offset:
                    if span.is_highlighted:
                        span.remove_highlight()
                        self.mouse_event = None
                    else:
                        span.highlight()
                    break

            self.canvas.draw()

    def _handle_key_press_event(self, event: KeyEvent):
        if self.mouse_event is None:
            return

        if event.key == "ctrl+d" and self.mouse_event.xdata is not None:
            self._delete_selected_span()

    def _delete_selected_span(self):
        if sum([len(x) for x in self.parent.spans_per_lead.values()]) == 0:
            return

        i = None
        selected_lead = self.mouse_event.inaxes.axes.get_title()

        if len(self.parent.spans_per_lead[selected_lead]) == 0:
            return

        for cnt, pos in enumerate(self.parent.spans_per_lead[selected_lead]):
            if pos.onset < self.mouse_event.xdata < pos.offset:
                i = cnt
                break

        self.parent.spans_per_lead[selected_lead].pop(i).remove_artist()

        self.mouse_event = None
        self.canvas.draw()

class FilterSettingsWindow(tk.Toplevel):
    def __init__(
        self,
        parent: ActionButtonsFrame,
        on_close_callback: Callable,
        on_filter_change_callback: Callable,
        *args,
        **kwargs
    ):
        tk.Toplevel.__init__(self, parent, *args, **kwargs)

        self.app = parent.app
        self.on_close_callback = on_close_callback
        self.on_filter_change_callback = on_filter_change_callback

        self.title("Filter settings")

        tk.Label(self, text="Filtering method [from methods]:").pack(pady=10, padx=10)
        self.filtering_methods = FilterMethods.get_filtering_methods()
        self.method_entry = ttk.Combobox(self, values=self.filtering_methods, state="readonly")
        self.method_entry.set(self.app.app_filter_config.filter_method.value)
        self.method_entry.pack(pady=10, padx=10)
        self.method_entry.bind("<<ComboboxSelected>>", self.on_dropdown_change)

        tk.Label(self, text="Lowcut frequency [Hz]:").pack(pady=10, padx=10)
        self.lowcut_entry = tk.Entry(self)
        self.lowcut_entry.insert(0, str(self.app.app_filter_config.lowcut_frequency))
        self.lowcut_entry.pack(pady=10, padx=10)

        tk.Label(self, text="Highcut frequency [Hz]:").pack(pady=10, padx=10)
        self.highcut_entry = tk.Entry(self)
        self.highcut_entry.insert(0, str(self.app.app_filter_config.highcut_frequency))
        self.highcut_entry.pack(pady=10, padx=10)

        tk.Label(self, text="Filter order [number]:").pack(pady=10, padx=10)
        self.order_entry = tk.Entry(self)
        self.order_entry.insert(0, str(self.app.app_filter_config.filter_order))
        self.order_entry.pack(pady=10, padx=10)

        self.save_button = tk.Button(self, text="Save", command=self.save_settings)
        self.save_button.pack(side=tk.LEFT, padx=10, pady=10)

        self.cancel_button = tk.Button(self, text="Cancel", command=self.on_cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=10, pady=10)

    def on_dropdown_change(self, _):
        if self.method_entry.get() == FilterMethods.LOWPASS.value:
            self.lowcut_entry.delete(0)
            self.lowcut_entry.configure(state=tk.DISABLED)
        else:
            self.lowcut_entry.configure(state=tk.NORMAL)

    def save_settings(self):

        try:
            filter_order = int(self.order_entry.get())
        except ValueError:
            tk.messagebox.showerror("Error", "Filter order must be integer number")
            return

        try:
            highcut_frequency = float(self.highcut_entry.get())
        except ValueError:
            tk.messagebox.showerror("Error", "Lowcut frequency must be a dot separated number, e.g. 1.23")
            return

        lowcut_frequency = None
        if self.lowcut_entry.get():
            try:
                lowcut_frequency = float(self.lowcut_entry.get())
            except ValueError:
                tk.messagebox.showerror("Error", "Lowcut frequency must be a dot separated number, e.g. 1.23")
                return

        filter_method = FilterMethods(self.method_entry.get())
        if filter_method == FilterMethods.BANDPASS and lowcut_frequency == 0.0:
            tk.messagebox.showerror("Error", "When filter method is \"bandpass\" lowcut frequency must be non-zero number")
            return

        filter_config = FilterConfig(
            filter_method=filter_method,
            filter_order=filter_order,
            highcut_frequency=highcut_frequency,
            lowcut_frequency=lowcut_frequency
        )

        logging.info(f"Filter config {filter_config}")

        if filter_config != self.app.app_filter_config:
            self.on_filter_change_callback()
            self.app.app_filter_config = filter_config

        self.on_close()

    def on_cancel(self):
        self.on_close()

    def on_close(self):
        self.destroy()
        self.on_close_callback()

def _do_spans_overlap(on1, off1, on2, off2):
    if off1 < on2 or off2 < on1:
        return False
    return True


if __name__ == "__main__":
    root = tk.Tk()
    MainApplication(root).pack(side="top", fill=tk.BOTH, expand=True)
    root.attributes("-alpha", True)
    root.title(APP_TITTLE)

    root.mainloop()
