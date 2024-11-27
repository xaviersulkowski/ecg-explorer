import logging
import os
import tkinter as tk

import matplotlib

from explorer.ECGExplorer import ECGExplorer
from filters.ecg_signal_filter import FilterConfig
from frontend.app_variables import AppVariables
from frontend.observers.annotations_manager import AnnotationsManager
from frontend.constants import APP_TITTLE
from frontend.observers.container_manager import ContainerManager
from frontend.observers.filter_config_manager import FilterManager
from frontend.observers.leads_manager import LeadsManager
from frontend.observers.observer_abc import Observer
from frontend.ui_components.bottom_frame import BottomFrame
from frontend.ui_components.plot_handler import ECGPlotHandler
from frontend.ui_components.top_frame import TopFrame

matplotlib.use("Agg")

logging.basicConfig(level=logging.INFO)


class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent

        # ====== publishers ======
        self.leads_manager = LeadsManager()
        self.annotations_manager = AnnotationsManager()
        self.container_manager = ContainerManager()
        self.filter_manager = FilterManager()
        self.filter_manager.filter_config = FilterConfig.default_bandpass()

        # ====== app variables ======
        self.app_variables = AppVariables()

        # ====== frames & widgets ======

        self.top_frame = TopFrame(
            self,
            leads_manager=self.leads_manager,
            annotations_manager=self.annotations_manager,
            container_manager=self.container_manager,
            filter_manager=self.filter_manager,
            load_signal_callback=self.load_signal_callback,
            app_variables=self.app_variables
        )
        self.top_frame.pack(fill=tk.BOTH, side=tk.TOP)

        self.ecg_plot = ECGPlotHandler.empty(
            self,
            self.leads_manager,
            self.annotations_manager,
            self.container_manager,
            self.filter_manager,
        )
        self.ecg_plot.pack(**ECGPlotHandler.ECG_PLOT_PACK_CONFIG)

        self.bottom_frame = BottomFrame(
            self,
            annotations_manager=self.annotations_manager,
            app_variables=self.app_variables,
            close_app_callback=self.exit_main,
        )
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH)

    def load_signal_callback(self, filename: str):
        """
        Entry point, loads signal from a file.

        :param filename: ECG filename. Supported files are:
            1. dicom
            2. XML from GE devices
        """
        def enable_options_on_signal_load():
            self.top_frame.activate_widgets()
            self.bottom_frame.activate_widgets()

        head, tail = os.path.split(filename)

        self.app_variables.file_path = head
        self.app_variables.file_name = tail.split(".")[0]

        explorer = ECGExplorer.load_from_file(
            filename,
            self.filter_manager.filter_config
        )
        self.app_variables.explorer = explorer

        explorer.process()

        container = explorer.container

        self.leads_manager.set_mapping_from_ecg_container(container)
        self.annotations_manager.empty_from_ecg_container(container)
        self.container_manager.container = container

        enable_options_on_signal_load()

    def exit_main(self):
        self.parent.destroy()
        exit()


if __name__ == "__main__":
    root = tk.Tk()
    MainApplication(root).pack(side="top", fill=tk.BOTH, expand=True)
    root.attributes("-alpha", True)
    root.title(APP_TITTLE)

    root.mainloop()
