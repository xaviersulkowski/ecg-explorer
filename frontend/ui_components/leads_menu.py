import tkinter as tk
from enum import Enum
from tkinter import ttk
from tkinter import messagebox

from frontend.constants import APP_TITTLE
from frontend.observers.leads_manager import LeadEvents, LeadsManager
from frontend.observers.observer_abc import Observer
from models.ecg import LeadName


class LeadsMenuFrame(tk.Frame, Observer):
    def __init__(
        self,
        parent: tk.Frame,
        leads_manager: LeadsManager,
        *args,
        **kwargs
    ):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        self.leads_manager = leads_manager
        self.leads_manager.add_subscriber(self)

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

    def update_on_notification(self, event: Enum, *args, **kwargs):
        if event == LeadEvents.LEADS_MAPPING_UPDATE:
            self._reload_leads_menu(kwargs['leads_mapping'])

    def _clear_all_leads(self):
        self.leads_listbox.selection_clear(0, self.leads_listbox.size())

    def _select_all_leads(self):
        self.leads_listbox.selection_set(0, self.leads_listbox.size())

    def _reload_leads_menu(self, leads_mapping: dict[LeadName, int]):
        if self.leads_listbox['state'] == tk.DISABLED:
            self.leads_listbox.configure(state=tk.NORMAL)

        self.leads_listbox.delete(0, self.leads_listbox.size())
        for name, (lead, cnt) in leads_mapping.items():
            self.leads_listbox.insert(cnt, name)
        self.leads_listbox.selection_set(0)

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
            self.leads_manager.selected_leads_names = currently_selected

    def activate_widgets(self):
        self.leads_listbox.configure(state=tk.NORMAL)
        self.confirm_button.configure(state=tk.NORMAL)
        self.clear_all_button.configure(state=tk.NORMAL)
        self.select_all_button.configure(state=tk.NORMAL)
