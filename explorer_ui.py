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
from typing import Optional

from explorer.ECGExplorer import ECGExplorer
from models.annotation import QRSComplex
from models.ecg import ECGContainer, ECGLead, LeadName
from models.ui_models import Span, AxProperties

APP_TITTLE = "ECG explorer"
matplotlib.use("Agg")


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
        self.show_processed_signal.set(False)

        self.file_path: Optional[str] = None
        self.file_name: Optional[str] = None

        # ====== frames & widgets ======

        self.top_frame = TopFrame(self)
        self.leads_menu_frame = LeadsMenuFrame(self)

        ecg_plot_pack_config = {"fill": tk.BOTH, "side": tk.TOP, "expand": True}
        self.ecg_plot = ECGPlotHandler.empty(self, ecg_plot_pack_config)

        self.bottom_frame = BottomFrame(self)

        self.top_frame.pack(anchor=tk.NW)
        self.leads_menu_frame.pack(anchor=tk.NE, padx=20, pady=20)
        self.ecg_plot.pack(**ecg_plot_pack_config)
        self.bottom_frame.pack(anchor=tk.SE, fill=tk.BOTH)

    def _on_lead_change(self, *_):
        selected_leads = [
            self.get_lead(lead_name) for lead_name in self.selected_leads_names.get()
        ]
        self.selected_leads = selected_leads

        # 1. remove all existing span artists
        self.ecg_plot.clear_annotations()

        # 2. re-draw waveforms and create new axes objects
        self.ecg_plot.plot_waveforms_for_selected_leads(self.selected_leads)

        # 3. re-draw annotations if any
        self.ecg_plot.draw_annotations_for_selected_leads()

    def get_lead(self, lead_name: str) -> ECGLead:
        return self.container.ecg_leads[self.leads_mapping[lead_name]]

    def load_signal(self, filename: str):
        def enable_options_on_signal_load():
            self.top_frame.activate_widgets()
            self.bottom_frame.activate_widgets()
            self.leads_menu_frame.activate_widgets()

        self.explorer = ECGExplorer.load_from_file(filename)
        self.container = self.explorer.container

        head, tail = os.path.split(filename)

        self.file_path = head
        self.file_name = tail.split(".")[0]

        enable_options_on_signal_load()

        self.leads_mapping = {
            x.label: cnt for cnt, x in enumerate(self.container.ecg_leads)
        }

        self.leads_menu_frame.reload_leads_menu(self.leads_mapping)
        self.leads_menu_frame.leads_listbox.selection_set(0)

        self.selected_leads = [
            self.get_lead(list(self.leads_mapping.keys())[0]),
        ]

        self.ecg_plot.clear_annotations()
        self.spans_per_lead = {x.label: [] for x in self.container.ecg_leads}

        self.ecg_plot.update_ecg_container(self.container)
        self.ecg_plot.plot_waveforms_for_selected_leads(self.selected_leads)

    def process_signal(self):
        self.explorer.process()
        showinfo(title=APP_TITTLE, message="Processing done!")
        self.top_frame.r2.configure(state=tk.NORMAL)

        for lead in self.container.ecg_leads:
            self.create_spans_from_qrs_annotations(lead)

        self.ecg_plot.draw_annotations_for_selected_leads()

    def clear_all_spans(self):
        for k in self.spans_per_lead.keys():
            self.spans_per_lead[k].clear()

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

    # def update_waveform(self):
    #     lead = self.selected_lead
    #     waveform = (
    #         lead.waveform
    #         if self.show_processed_signal.get() is True
    #         else lead.raw_waveform
    #     )
    #
    #     if waveform is None:
    #         showwarning(title=APP_TITTLE, message="Process the signal first!")
    #         return
    #
    #     self.line.set_data(range(len(waveform)), waveform)
    #     self.canvas.draw()

    def exit_main(self):
        self.parent.destroy()
        exit()


class TopFrame(tk.Frame):
    def __init__(self, parent: MainApplication, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        self.radio_button_frame = tk.Frame(self)

        self.open_button = tk.Button(
            self, text="Select ECG file", command=self._select_file, bg="ivory4"
        )

        self.process_ecg_button = tk.Button(
            self,
            text="Process ECG",
            command=self.parent.process_signal,
            state=tk.DISABLED,
        )

        self.load_ann_button = tk.Button(
            self,
            text="Load annotations",
            command=self._load_annotations,
            state=tk.DISABLED,
        )

        self.r1 = tk.Radiobutton(
            self.radio_button_frame,
            text="Raw signal",
            variable=self.parent.show_processed_signal,
            value=False,
            command=self._on_radio_change,
            state=tk.DISABLED,
        )
        self.r1.pack(anchor=tk.NW)

        self.r2 = tk.Radiobutton(
            self.radio_button_frame,
            text="Processed signal",
            variable=self.parent.show_processed_signal,
            value=True,
            command=self._on_radio_change,
            state=tk.DISABLED,
        )
        self.r2.pack(anchor=tk.NW)

        self.open_button.grid(row=0, column=0, padx=20, pady=20)
        self.load_ann_button.grid(row=1, column=0, padx=20, pady=20)
        self.process_ecg_button.grid(row=0, column=1, padx=10, pady=20)
        self.radio_button_frame.grid(row=0, column=2, padx=10, pady=20)

    def _on_radio_change(self):
        self.parent.update_waveform()

    def _select_file(self):
        filetypes = (("Dicom files", "*.dcm"),)

        filename = fd.askopenfilename(
            title="Open a file", initialdir="./", filetypes=filetypes
        )

        if filename is None or filename == "" or filename == ():
            showinfo(title=APP_TITTLE, message="File not selected")
            return

        showinfo(title=APP_TITTLE, message="Successfully loaded file!")

        self.parent.load_signal(filename)

    def _load_annotations(self):
        filetypes = (("annotation files", "*.annx"),)
        filename = fd.askopenfilename(title="Open a file", filetypes=filetypes)

        if filename is None or filename == "" or filename == ():
            showinfo(title=APP_TITTLE, message="File not selected")
            return

        should_continue = True
        if any(len(span) > 0 for span in self.parent.spans_per_lead.values()):
            should_continue = tk.messagebox.askyesno(
                title=APP_TITTLE,
                message="Loading annotations from the file will overwrite existing annotations. Are you sure?",
            )

        if not should_continue:
            return

        self.parent.explorer.load_annotations(filename)
        self.parent.ecg_plot.clear_annotations()
        self.parent.clear_all_spans()

        for lead in self.parent.container.ecg_leads:
            self.parent.create_spans_from_qrs_annotations(lead)

        self.parent.ecg_plot.draw_annotations_for_selected_leads()

    def activate_widgets(self):
        self.r1.configure(state=tk.NORMAL)
        self.process_ecg_button.configure(state=tk.NORMAL)
        self.load_ann_button.configure(state=tk.NORMAL)


class BottomFrame(tk.Frame):
    def __init__(self, parent: MainApplication, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        # dunno how, but works so I can move "Quit" button to the right side
        self.columnconfigure(2, weight=1)

        self.save_annotations_button = tk.Button(
            self,
            text="Save annotations",
            state=tk.DISABLED,
            command=self._on_save_annotations,
        )

        self.save_annotations_button.grid(row=0, column=0, padx=20, pady=20)

        self.generate_report_button = tk.Button(
            self,
            text="Generate report",
            state=tk.DISABLED,
            command=self.parent.generate_report,
        )

        self.generate_report_button.grid(row=0, column=1, padx=20, pady=20)

        self.quit = tk.Button(
            self,
            text="Quit",
            command=self.parent.exit_main,
            bg="ivory4",
        )

        self.quit.grid(row=0, column=2, padx=20, pady=20, sticky=tk.E)

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
    def __init__(self, parent: MainApplication, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.leads_listbox = tk.Listbox(
            self, height=3, selectmode=tk.MULTIPLE, state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.leads_listbox.yview,
        )
        self.leads_listbox["yscrollcommand"] = scrollbar.set

        self.confirm_button = tk.Button(
            self,
            text="Confirm choices",
            command=self._on_confirm_button_click,
            state=tk.DISABLED,
        )

        self.confirm_button.pack(expand=True, side=tk.BOTTOM, fill=tk.X)
        self.leads_listbox.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, expand=True, fill=tk.Y)

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
            self.parent.selected_leads_names.set(currently_selected)

    def activate_widgets(self):
        self.leads_listbox.configure(state=tk.NORMAL)
        self.confirm_button.configure(state=tk.NORMAL)


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
        if lead.units == "microvolt":
            waveform = waveform / 1000
        else:
            RuntimeError("Unit not known")

        line.set_data(range(len(waveform)), waveform)

        x = np.arange(0, len(waveform), self.X_ECG_GRID_IN_MS * lead.fs / 1000)
        x_ticks = x / lead.fs
        ax.set_xticks(x)
        ax.set_xlim(0, len(waveform))
        ax.set_xticklabels(x_ticks)
        ax.xaxis.set_tick_params(labelsize=9)

        y_min_round_half_down = round((min(waveform) - (0.5 if (abs(min(waveform)) * 2 % 1) < .5 else 0)) * 2) / 2
        y_max_round_half_up = round((max(waveform) + (0.5 if (max(waveform) * 2 % 1) < .5 else 0)) * 2) / 2

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
