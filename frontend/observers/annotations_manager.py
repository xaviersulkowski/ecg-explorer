from enum import Enum


from frontend.observers.observer_abc import Subject
from models.annotation import QRSComplex
from models.ecg import LeadName, ECGContainer


class AnnotationEvents(Enum):
    ANNOTATIONS_UPDATE = 1
    ANNOTATIONS_DELETE = 2


class AnnotationsManager(Subject):
    """
    ECGPlotHandler should subscribe
    """

    def __init__(self):
        super().__init__()
        self._annotations_per_lead: dict[LeadName, list[QRSComplex]] = {}

    @property
    def annotations(self) -> dict[LeadName, list[QRSComplex]]:
        return self._annotations_per_lead

    @annotations.setter
    def annotations(self, annotations):
        self._annotations_per_lead = annotations
        self.notify_subscribers(
            event=AnnotationEvents.ANNOTATIONS_UPDATE, annotations=annotations
        )

    def clear_annotations(self):
        self._annotations_per_lead = {
            lead: [] for lead, _ in self._annotations_per_lead.items()
        }
        self.notify_subscribers(event=AnnotationEvents.ANNOTATIONS_DELETE)

    def empty_from_ecg_container(self, ecg_container: ECGContainer):
        self._annotations_per_lead = {x.label: [] for x in ecg_container.ecg_leads}
