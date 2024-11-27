from enum import Enum

from frontend.observers.observer_abc import Subject
from models.ecg import LeadName, ECGLead, ECGContainer


class LeadEvents(Enum):
    LEADS_MAPPING_UPDATE = 1
    LEADS_SELECTION_UPDATE = 2


class LeadsManager(Subject):
    def __init__(self):
        super().__init__()
        # TODO: I don't remember why do we need the int, check out and add comment
        self._leads_mapping: dict[LeadName, tuple[ECGLead, int]] = {}
        self._selected_leads_names: list[LeadName] = []

    @property
    def leads_mapping(self) -> dict[LeadName, tuple[ECGLead, int]]:
        return self._leads_mapping

    @leads_mapping.setter
    def leads_mapping(self, leads_mapping: dict[ECGLead, int]):
        """
        Also sets selected leads as the first one - it makes sense since this method should only be called on the signal (re)load.

        :param leads_mapping: all available leads
        """
        self._leads_mapping = leads_mapping
        self._selected_leads_names = [list(self._leads_mapping.keys())[0]]
        self.notify_subscribers(
            event=LeadEvents.LEADS_MAPPING_UPDATE, leads_mapping=self.leads_mapping
        )
        self.notify_subscribers(
            event=LeadEvents.LEADS_SELECTION_UPDATE,
            selected_names=self._selected_leads_names,
        )

    def set_mapping_from_ecg_container(self, ecg_container: ECGContainer):
        """
        This method should notify Leads Menu
        """
        self.leads_mapping = {
            x.label: (x, cnt) for cnt, x in enumerate(ecg_container.ecg_leads)
        }

    @property
    def selected_leads_names(self) -> list[str]:
        return self._selected_leads_names

    @selected_leads_names.setter
    def selected_leads_names(self, selected_leads_names: list[str]):
        self._selected_leads_names = selected_leads_names
        self.notify_subscribers(
            event=LeadEvents.LEADS_SELECTION_UPDATE, leads=self._selected_leads_names
        )

    @property
    def selected_leads(self) -> list[ECGLead]:
        return [self.leads_mapping[ln][0] for ln in self.selected_leads_names]

    def get_lead(self, lead_name: str) -> ECGLead:
        return self.leads_mapping[lead_name][0]
