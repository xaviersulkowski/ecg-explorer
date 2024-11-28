from enum import Enum

from frontend.models import Span
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
        self._annotations_per_lead: dict[LeadName, list[Span]] = {}

    @property
    def annotations(self):
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

    def to_qrs_complexes(self) -> dict[LeadName, list[QRSComplex]]:
        out = {}
        for lead, annotations in self.annotations.items():
            out[lead] = [QRSComplex(a.onset, a.offset) for a in annotations]
        return out
