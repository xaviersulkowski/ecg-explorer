import tkinter as tk
from tkinter import filedialog as fd
from tkinter.messagebox import showinfo
from typing import Callable

from frontend.app_variables import AppVariables
from frontend.constants import APP_TITTLE
from frontend.observers.annotations_manager import AnnotationsManager


# TODO: this
class BottomFrame(tk.Frame):
    def __init__(
        self,
        parent: tk.Frame,
        annotations_manager: AnnotationsManager,
        app_variables: AppVariables,
        # we need access to "master" parent to close it, this is why want this as a callback
        close_app_callback: Callable,
        *args,
        **kwargs,
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.parent = parent
        self.app_variables = app_variables
        self.annotations_manager = annotations_manager

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
            command=self._generate_report,
        )

        self.quit = tk.Button(
            self,
            text="Quit",
            command=close_app_callback,
            bg="ivory4",
        )

        self.save_annotations_button.pack(side=tk.LEFT, padx=10, pady=10)
        self.generate_report_button.pack(side=tk.LEFT, padx=5, pady=10)
        self.quit.pack(side=tk.RIGHT, padx=10, pady=10)

    def _override_qrs_complexes_from_annotations(self):
        for lead, qrs_complexes in self.annotations_manager.annotations.items():
            self.app_variables.explorer.overwrite_annotations(lead, qrs_complexes)

    def _generate_report(self):
        self._override_qrs_complexes_from_annotations()

        df = self.app_variables.explorer.generate_report()
        filename = fd.asksaveasfile(
            mode="w",
            initialfile=f"{self.app_variables.file_name}.csv",
            defaultextension=".csv",
        )
        if filename is None:
            return

        df.to_csv(filename)

        showinfo(
            title=APP_TITTLE, message=f"Report generated and saved to {filename.name}"
        )

    def _on_save_annotations(self):
        filename = fd.asksaveasfile(
            mode="w",
            initialfile=f"{self.app_variables.file_name}.annx",
            defaultextension=".annx",
        )

        if filename is None:
            return

        self._override_qrs_complexes_from_annotations()
        self.app_variables.explorer.save_annotations(filename.name)

        showinfo(title=APP_TITTLE, message=f"Annotations saved to {filename.name}")

    def activate_widgets(self):
        self.generate_report_button.configure(state=tk.NORMAL)
        self.save_annotations_button.configure(state=tk.NORMAL)
