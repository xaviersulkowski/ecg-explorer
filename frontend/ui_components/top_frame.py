import logging
import tkinter as tk
from enum import Enum

from tkinter import ttk
from tkinter import filedialog as fd
from tkinter import messagebox
from typing import Callable

from filters.ecg_signal_filter import FilterMethods, FilterConfig
from frontend.app_variables import AppVariables
from frontend.constants import APP_TITTLE
from frontend.observers.annotations_manager import AnnotationsManager
from frontend.observers.container_manager import ContainerManager, ContainerEvents
from frontend.observers.filter_config_manager import FilterManager
from frontend.observers.leads_manager import LeadsManager
from frontend.observers.observer_abc import Observer
from frontend.ui_components.leads_menu import LeadsMenuFrame
from frontend.utils import merge_existing_annotations_with_lead
from models.ecg import ECGContainer


class TopFrame(tk.Frame):
    """
    This class only arranges views. It has no actual functionality.
    """

    def __init__(
        self,
        parent: tk.Frame,
        leads_manager: LeadsManager,
        annotations_manager: AnnotationsManager,
        container_manager: ContainerManager,
        filter_manager: FilterManager,
        load_signal_callback: Callable,
        app_variables: AppVariables,
        *args,
        **kwargs,
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.action_buttons_frame = ActionButtonsFrame(
            self,
            app_variables=app_variables,
            container_manager=container_manager,
            annotations_manager=annotations_manager,
            filter_manager=filter_manager,
            load_signal_callback=load_signal_callback,
        )
        self.action_buttons_frame.pack(anchor=tk.NW, side=tk.LEFT, fill=tk.Y)

        self.description_frame = DescriptionFrame(self, container_manager)
        self.description_frame.pack(
            anchor=tk.N, side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10, expand=True
        )

        self.leads_menu_frame = LeadsMenuFrame(self, leads_manager)
        self.leads_menu_frame.pack(
            anchor=tk.E,
            side=tk.RIGHT,
            padx=10,
            pady=10,
        )

    def activate_widgets(self):
        self.action_buttons_frame.activate_widgets()
        self.leads_menu_frame.activate_widgets()


class DescriptionFrame(tk.Frame, Observer):
    """
    This frame is responsible for displaying ECG description.
    Subscribes for container (aka. signal) change. If the signal changed, description is updated.
    """

    PATH_PREFIX = "path: "

    def __init__(
        self,
        parent: tk.Frame,
        container_manager: ContainerManager,
        *args,
        **kwargs,
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.container_manager = container_manager
        self.container_manager.add_subscriber(self)

        self.path = tk.Text(self, height=2)
        self._setup_text_container(self.path, self.PATH_PREFIX)

        self.description = tk.Text(self, height=2)
        self._setup_text_container(self.description, "")

    def update_on_notification(self, event: Enum, *args, **kwargs):
        if event == ContainerEvents.CONTAINER_UPDATE:
            self._update_description(kwargs["container"])

    def _update_description(self, container: ECGContainer):
        self._write_text(self.path, self.PATH_PREFIX + container.file_path)
        logging.info(f"Loaded new path: {container.file_path}")
        self._write_text(self.description, container.description)
        logging.info(f"Loaded new path: {container.description}")

    @staticmethod
    def _setup_text_container(text_c: tk.Text, prefix: str):
        text_c.insert(tk.END, "" + prefix)
        text_c.config(state=tk.DISABLED)
        text_c.pack()

    @staticmethod
    def _write_text(text_c: tk.Text, text: str):
        text_c.config(state=tk.NORMAL)
        text_c.delete(f"1.0", tk.END)
        text_c.insert(tk.END, text)
        text_c.config(state=tk.DISABLED)


class ActionButtonsFrame(tk.Frame):
    def __init__(
        self,
        parent: tk.Frame,
        app_variables: AppVariables,
        container_manager: ContainerManager,
        annotations_manager: AnnotationsManager,
        filter_manager: FilterManager,
        load_signal_callback: Callable,
        *args,
        **kwargs,
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.app_variables = app_variables
        self.container_manager = container_manager
        self.annotations_manager = annotations_manager
        self.filter_manager = filter_manager
        self.load_signal_callback = load_signal_callback

        self.open_button = tk.Button(
            self,
            text="Select ECG file",
            command=self._select_file_callback,
            bg="ivory4",
        )

        self.process_ecg_button = tk.Button(
            self,
            text="Detect QRS",
            command=self._process_signal_callback,
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
            command=self._clear_annotations_callback,
            state=tk.DISABLED,
        )

        self.filters_setting_button = tk.Button(
            self,
            text="Filter settings",
            command=self._open_settings_window,
            state=tk.NORMAL,
        )

        show_processed = tk.BooleanVar()
        show_processed.set(True)

        def set_show_processed():
            self.filter_manager.show_filtered = show_processed.get()
            logging.info(
                f'Set "show filtered" variable as {filter_manager.show_filtered}'
            )

        self.processed_button = tk.Checkbutton(
            self,
            text="Show processed signal",
            variable=show_processed,
            onvalue=True,
            offvalue=False,
            command=set_show_processed,
            state=tk.DISABLED,
        )

        self.open_button.grid(row=0, column=0, padx=5, pady=5, sticky="nesw")
        self.load_ann_button.grid(row=1, column=0, padx=5, pady=5, sticky="nesw")
        self.process_ecg_button.grid(row=0, column=1, padx=5, pady=5, sticky="nesw")
        self.clear_ann_button.grid(row=1, column=1, padx=5, pady=5, sticky="nesw")
        self.filters_setting_button.grid(row=2, column=0, padx=5, pady=5, sticky="nesw")
        self.processed_button.grid(row=3, column=0, padx=5, pady=5, sticky="nesw")

        self.filters_setting_window = None

    def _process_signal_callback(self):
        logging.info("Processing signal")

        self.app_variables.explorer.process(True)

        updated_annotations = {}
        for lead in self.container_manager.container.ecg_leads:
            lead_name, annotations = merge_existing_annotations_with_lead(
                self.annotations_manager.annotations, lead
            )
            updated_annotations[lead_name] = annotations

        self.annotations_manager.annotations = updated_annotations
        tk.messagebox.showinfo(title=APP_TITTLE, message="Processing done!")

    def _select_file_callback(self):
        filetypes = (("Dicom files", "*.dcm"), ("XML files", "*.Xml"))

        filename = fd.askopenfilename(
            title="Open a file", initialdir="./", filetypes=filetypes
        )

        if filename is None or filename == "" or filename == ():
            tk.messagebox.showinfo(title=APP_TITTLE, message="File not selected")
            return

        self.load_signal_callback(filename)

        tk.messagebox.showinfo(title=APP_TITTLE, message="Successfully loaded file!")

    def _clear_annotations_callback(self):
        should_continue = tk.messagebox.askyesno(
            title=APP_TITTLE,
            message="Do you want to delete all existing annotations?",
        )

        if not should_continue:
            return

        self.annotations_manager.clear_annotations()

    def _load_annotations(self):
        filetypes = (("annotation files", "*.annx"),)
        filename = fd.askopenfilename(title="Open a file", filetypes=filetypes)

        if filename is None or filename == "" or filename == ():
            tk.messagebox.showinfo(title=APP_TITTLE, message="File not selected")
            return

        should_continue = True
        if any(len(span) > 0 for span in self.annotations_manager.annotations.values()):
            should_continue = tk.messagebox.askyesno(
                title=APP_TITTLE,
                message="Loading annotations from the file will overwrite existing annotations. Are you sure?",
            )

        if not should_continue:
            return

        self.app_variables.explorer.load_annotations(filename)
        self.annotations_manager.clear_annotations()

        updated_annotations = {}
        for lead in self.container_manager.container.ecg_leads:
            lead_name, annotations = merge_existing_annotations_with_lead(
                self.annotations_manager.annotations, lead
            )
            updated_annotations[lead_name] = annotations

        self.annotations_manager.annotations = updated_annotations
        tk.messagebox.showinfo(title=APP_TITTLE, message="Annotations loaded!")

    def _open_settings_window(self):
        if self.filters_setting_window is None:
            self.filters_setting_window = FilterSettingsWindow(
                self,
                self.filter_manager,
                self.container_manager,
                self.app_variables,
                self._settings_window_on_close_callback,
                # self._settings_window_filter_changed_callback,
            )

    def _settings_window_on_close_callback(self):
        self.filters_setting_window = None

    def activate_widgets(self):
        self.process_ecg_button.configure(state=tk.NORMAL)
        self.load_ann_button.configure(state=tk.NORMAL)
        self.clear_ann_button.configure(state=tk.NORMAL)
        self.processed_button.configure(state=tk.NORMAL)


class FilterSettingsWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Frame,
        filter_manger: FilterManager,
        container_manger: ContainerManager,
        app_variables: AppVariables,
        on_close_callback: Callable,
        # on_filter_change_callback: Callable,
        *args,
        **kwargs,
    ):
        tk.Toplevel.__init__(self, parent, *args, **kwargs)

        self.on_close_callback = on_close_callback
        # self.on_filter_change_callback = on_filter_change_callback
        self.filter_manager = filter_manger
        self.container_manger = container_manger
        self.app_variables = app_variables

        self.title("Filter settings")

        tk.Label(self, text="Filtering method [from methods]:").pack(pady=10, padx=10)
        self.filtering_methods = FilterMethods.get_filtering_methods()
        self.method_entry = ttk.Combobox(
            self, values=self.filtering_methods, state="readonly"
        )
        self.method_entry.set(self.filter_manager.filter_config.filter_method.value)
        self.method_entry.pack(pady=10, padx=10)
        self.method_entry.bind("<<ComboboxSelected>>", self.on_dropdown_change)

        tk.Label(self, text="Lowcut frequency [Hz]:").pack(pady=10, padx=10)
        self.lowcut_entry = tk.Entry(self)
        self.lowcut_entry.insert(
            0, str(self.filter_manager.filter_config.lowcut_frequency)
        )
        self.lowcut_entry.pack(pady=10, padx=10)

        tk.Label(self, text="Highcut frequency [Hz]:").pack(pady=10, padx=10)
        self.highcut_entry = tk.Entry(self)
        self.highcut_entry.insert(
            0, str(self.filter_manager.filter_config.highcut_frequency)
        )
        self.highcut_entry.pack(pady=10, padx=10)

        tk.Label(self, text="Filter order [number]:").pack(pady=10, padx=10)
        self.order_entry = tk.Entry(self)
        self.order_entry.insert(0, str(self.filter_manager.filter_config.filter_order))
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
            tk.messagebox.showerror(
                "Error", "Lowcut frequency must be a dot separated number, e.g. 1.23"
            )
            return

        lowcut_frequency = None
        if self.lowcut_entry.get():
            try:
                lowcut_frequency = float(self.lowcut_entry.get())
            except ValueError:
                tk.messagebox.showerror(
                    "Error",
                    "Lowcut frequency must be a dot separated number, e.g. 1.23",
                )
                return

        filter_method = FilterMethods(self.method_entry.get())
        if filter_method == FilterMethods.BANDPASS and lowcut_frequency == 0.0:
            tk.messagebox.showerror(
                "Error",
                'When filter method is "bandpass" lowcut frequency must be non-zero number',
            )
            return

        filter_config = FilterConfig(
            filter_method=filter_method,
            filter_order=filter_order,
            highcut_frequency=highcut_frequency,
            lowcut_frequency=lowcut_frequency,
        )

        logging.info(f"Filter config {filter_config}")

        if filter_config != self.filter_manager.filter_config:
            # self.on_filter_change_callback()
            # This should trigger re-draw
            self.filter_manager.filter_config = filter_config
            if self.app_variables.explorer is not None:
                # this line makes me thinking that the explorer should subscribe too 🤔
                self.app_variables.explorer.filter_config = (
                    self.filter_manager.filter_config
                )
                self.app_variables.explorer.process()
                self.container_manger.container = self.app_variables.explorer.container
        else:
            logging.info("No filter changes")

        self.on_close()

    def on_cancel(self):
        self.on_close()

    def on_close(self):
        self.destroy()
        self.on_close_callback()
