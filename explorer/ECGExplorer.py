import os
import pandas as pd

from detectors.qrs_detectors import PanTompkinsDetector
from filters.ecg_signal_filter import BandPassEcgSignalFilter
from models.ecg import ECGContainer


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

    def generate_report(self) -> pd.DataFrame:
        report = pd.DataFrame()

        for lead in self._container.ecg_leads:
            column_root = lead.label.lower().replace(" ", "_")

            report[f"{column_root}_width_ms"] = pd.Series(lead.calculate_qrs_lengths())
            report[f"{column_root}_abs_area_mV^2"] = pd.Series(lead.calculate_qrs_areas())

        return report
