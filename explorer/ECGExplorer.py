import os
import pandas as pd

from detectors.qrs_detectors import PanTompkinsDetector
from filters.ecg_signal_filter import BandPassEcgSignalFilter
from models.annotation import QRSComplex
from models.ecg import ECGContainer, LeadName


class ECGExplorer:
    def __init__(self, container: ECGContainer):
        self._container: ECGContainer = container
        self._filter = BandPassEcgSignalFilter()
        self._r_detector = PanTompkinsDetector()

    @classmethod
    def load_from_file(cls, filepath: str):
        if not os.path.isfile(filepath):
            raise FileNotFoundError()

        ext = os.path.splitext(filepath)[-1].lower()

        if ext == ".dcm":
            return cls(ECGContainer.from_dicom_file(filepath))

    def process(self):
        self._filter.filter(self._container)
        self._r_detector.detect(self._container)

    @property
    def container(self):
        # TODO: check if processed
        return self._container

    def overwrite_annotations(self, lead_name: LeadName, qrs: list[QRSComplex]):
        lead = self._container.get_lead(lead_name)
        if lead:
            lead.ann.qrs_complex_positions = qrs

    def generate_report(self) -> pd.DataFrame:
        def _padded(data: list, size: int) -> list:
            out = [None] * size
            for cnt, l in enumerate(data):
                out[cnt] = l
            return out

        report = pd.DataFrame()

        max_size = max(
            len(lead.ann.qrs_complex_positions) for lead in self._container.ecg_leads
        )

        for lead in self._container.ecg_leads:
            column_root = lead.label.lower().replace(" ", "_")

            report[f"{column_root}_width_ms"] = pd.Series(
                _padded(lead.calculate_qrs_lengths(), max_size)
            )
            report[f"{column_root}_abs_area_mV^2"] = pd.Series(
                _padded(lead.calculate_qrs_areas(), max_size)
            )

        return report

    def save_annotations(self, filename):
        self._container.save_annotations(filename)

    def load_annotations(self, filename):
        self._container.load_annotations(filename)
