import logging
import pickle

import numpy as np
import pydicom as dicom

from dataclasses import dataclass, field
from typing import Any, Optional, TypeAlias

from models.annotation import Annotation

LeadName: TypeAlias = str


@dataclass
class ECGLead:
    label: LeadName
    raw_waveform: np.ndarray[float]
    waveform: Optional[np.ndarray[float]] = None
    units: Optional[str] = None
    fs: Optional[float] = None  # sampling frequency in Hz
    is_filtered: bool = False

    ann: Annotation = field(default_factory=Annotation)

    def __repr__(self):
        return f"\n{self.label}: \n\tunits: {self.units} \n\tsampling: {self.fs}Hz \n\tdata: {self.waveform}\n"

    def calculate_qrs_lengths(self):
        return [
            (pos.offset - pos.onset) / self.fs * 1000
            for pos in self.ann.qrs_complex_positions or []
        ]

    def calculate_qrs_areas(self):

        areas = []

        for pos in (self.ann.qrs_complex_positions or []):
            # 1. absolut value of a signal
            waveform_abs = self.raw_waveform[pos.onset: pos.offset]

            # 2. "estimate" an ecg baseline, which is a line between QRS onset and offset y = ax + b
            x1, y1 = pos.onset, waveform_abs[0]
            x2, y2 = pos.offset, waveform_abs[-1]

            a = (y1-y2)/(x1-x2)
            b = (x1*y2 - x2*y1)/(x1-x2)

            # 3. adjust waveform, move qrs to the baseline
            baseline = (np.arange(x1, x2) * a) + b
            waveform_adj = waveform_abs - baseline

            # 4. calculate area
            areas.append(
                np.round(
                    np.trapz(waveform_adj), decimals=2
                )
            )

        return areas


class ECGContainer:
    def __init__(self, ecg_leads: list[ECGLead], raw: Any):
        self.ecg_leads: list[ECGLead] = ecg_leads
        self.raw: Any = raw

    @property
    def n_leads(self):
        return len(self.ecg_leads)

    def get_lead(self, lead_name: LeadName) -> Optional[ECGLead]:
        leads = [lead for lead in self.ecg_leads if lead.label == lead_name]
        if len(leads) > 0:
            return leads[0]
        else:
            return None

    @classmethod
    def from_dicom_file(cls, path: str):
        try:
            raw = dicom.dcmread(path)
        except Exception as e:
            logging.warning(f"Couldn't read dicom file: {path}. Reason: {e}")
            raise e
        else:
            logging.info(f"Loaded file successfully")

        waveform = raw.WaveformSequence[0]
        waveform_data = raw.waveform_array(0)
        leads = list()

        for ii, channel in enumerate(waveform.ChannelDefinitionSequence):
            label = channel.ChannelLabel
            units = None
            if "ChannelSensitivity" in channel:  # Type 1C, may be absent
                units = channel.ChannelSensitivityUnitsSequence[0].CodeMeaning

            leads.append(
                ECGLead(
                    label, waveform_data[:, ii], None, units, waveform.SamplingFrequency
                )
            )

        return cls(leads, raw)

    def save_annotations(self, filename):
        annotations = {lead.label: lead.ann for lead in self.ecg_leads}

        with open(filename, "wb") as file:
            pickle.dump(annotations, file, protocol=pickle.HIGHEST_PROTOCOL)

    def load_annotations(self, filename):
        with open(filename, "rb") as file:
            ann = pickle.load(file)

            if not isinstance(ann, dict):
                raise RuntimeError(
                    "File you're trying to load is not an annotation file or is malformed"
                )

            for k, v in ann.items():
                if not isinstance(k, str) and not isinstance(v, Annotation):
                    raise RuntimeError(
                        "File you're trying to load is not an annotation file or is malformed"
                    )

                self.get_lead(k).ann = v
