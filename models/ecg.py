import logging
import pickle

import numpy as np
import pydicom as dicom

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional, TypeAlias, List, Literal
from xml.etree import ElementTree as ET

from models.annotation import Annotation

LeadName: TypeAlias = str


@dataclass
class ECGLead:
    label: LeadName
    raw_waveform: np.ndarray[float]
    waveform: Optional[np.ndarray[float]] = None
    units: Optional[Literal["uV"]] = None
    fs: Optional[float] = None  # sampling frequency in Hz
    is_filtered: bool = False

    ann: Annotation = field(default_factory=Annotation)

    def __repr__(self):
        return f"\n{self.label}: \n\tunits: {self.units} \n\tsampling: {self.fs}Hz \n\tdata: {self.waveform}\n"

    def calculate_qrs_lengths(self) -> List[float]:
        return [
            (pos.offset - pos.onset) / self.fs * 1000
            for pos in self.ann.qrs_complex_positions or []
        ]

    def calculate_qrs_areas(self) -> list[float]:
        if self.units == "uV":
            waveform = self.raw_waveform
        else:
            raise RuntimeError(f"Unit {self.units} not known")

        areas = np.zeros(len(self.ann.qrs_complex_positions or []))

        for cnt, pos in enumerate(self.ann.qrs_complex_positions or []):
            waveform_abs = np.abs(waveform[pos.onset : pos.offset])

            areas[cnt] = np.trapz(waveform_abs, dx=1 / self.fs)

        return list(map(lambda x: float(f"{x:.2f}"), areas.tolist()))


class ECGContainer:
    EXPECTED_LEADS_ORDER = [
        "I",
        "II",
        "III",
        "aVR",
        "aVL",
        "aVF",
        "V1",
        "V2",
        "V3",
        "V4",
        "V5",
        "V6",
    ]

    def __init__(
        self, ecg_leads: list[ECGLead], raw: Any, description: str, file_path: str
    ):
        self.ecg_leads: list[ECGLead] = self._sort_leads(ecg_leads)
        self.raw: Any = raw
        self.description: str = description
        self.file_path: str = file_path

    @property
    def n_leads(self):
        return len(self.ecg_leads)

    def _sort_leads(self, ecg_leads: list[ECGLead]) -> list[ECGLead]:
        return [
            lead
            for x in self.EXPECTED_LEADS_ORDER
            for lead in ecg_leads
            if lead.label == x
        ]

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
            logging.info(f"Loaded file successfully {path}")

        waveform = raw.WaveformSequence[0]
        waveform_data = raw.waveform_array(0)
        leads = list()

        for ii, channel in enumerate(waveform.ChannelDefinitionSequence):
            label = channel.ChannelLabel.replace("Lead ", "")
            units = None
            if "ChannelSensitivity" in channel:  # Type 1C, may be absent
                units = channel.ChannelSensitivityUnitsSequence[0].CodeMeaning

            if units == "microvolt":
                units = "uV"

            leads.append(
                ECGLead(
                    label, waveform_data[:, ii], None, units, waveform.SamplingFrequency
                )
            )

        return cls(
            leads,
            raw,
            f"{raw.PatientName.given_name} {raw.PatientName.family_name}",
            path,
        )

    @classmethod
    def from_ge_xml_file(cls, path):
        def extract_leads(file_dict: dict) -> list[ECGLead]:
            ecg_dict = file_dict["sapphire"]["xmlData"]["block"]["params"]["ecg"][
                "wav"
            ]["ecgWaveformMXG"]

            sample_rate_unit = ecg_dict["sampleRate"]["U"]
            sample_rate = int(ecg_dict["sampleRate"]["V"])
            if sample_rate_unit == "Hz":
                sample_rate_hz = sample_rate
            elif sample_rate_unit == "kHz":
                sample_rate_hz = sample_rate / 1000
            else:
                raise RuntimeError(
                    "GE XML - could not parse sample rate. Unit not known"
                )

            leads_object = ecg_dict["ecgWaveform"]
            leads_from_file = (
                [leads_object] if type(leads_object) is not list else leads_object
            )

            leads = list()
            for lead in leads_from_file:
                label = lead["lead"]
                units = lead["U"]
                # asizeBT = lead['asizeBT']
                # inv = lead['INV']
                magic_number = lead["S"]
                waveform_str: str = lead["V"]
                waveform_data = np.fromiter(
                    map(lambda x: float(x), waveform_str.split(" ")), dtype=np.float_
                ) * float(magic_number)

                leads.append(ECGLead(label, waveform_data, None, units, sample_rate_hz))

            return leads

        def extract_description(file_dict: dict) -> str:
            given_names_list = (
                file_dict["sapphire"]["demographics"]["patientInfo"]
                .get("name", {})
                .get("given", [])
            )
            given_names = [
                x.get("V", "")
                for x in given_names_list
                if x.get("V") is not None and x["V"] != "NONE"
            ]

            family_name = (
                file_dict["sapphire"]["demographics"]["patientInfo"]
                .get("name", {})
                .get("family", {})
                .get("V", "")
            )

            return " ".join(given_names) + " " + family_name

        try:
            root = ET.parse(path).getroot()
            xml_dict = etree_to_dict(root)
            leads = extract_leads(xml_dict)
            description = extract_description(xml_dict)
        except Exception as e:
            logging.warning(f"Couldn't read GE XLM file: {path}. Reason: {e}")
            raise e
        else:
            logging.info(f"Loaded file successfully {path}")

        return cls(leads, root, description, path)

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

                # legacy leads had "Lead" prefix.
                if "Lead " in k:
                    k = k.replace("Lead ", "")

                self.get_lead(k).ann = v


def etree_to_dict(t):
    def clean_up_tag(tag):
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    tag = clean_up_tag(t.tag)
    d = {tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib:
        d[tag].update((k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[tag]["#text"] = text
        else:
            d[tag] = text
    return d
