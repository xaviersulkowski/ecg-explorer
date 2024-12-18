from typing import Union

from models.annotation import QRSComplex
from models.ecg import LeadName, ECGLead

numeric = Union[int, float]


def do_annotations_overlap(on1: numeric, off1: numeric, on2: numeric, off2: numeric):
    if off1 < on2 or off2 < on1:
        return False
    return True


def merge_existing_annotations_with_lead(
    existing_annotations: dict[LeadName, list[QRSComplex]], lead: ECGLead
) -> tuple[LeadName, list[QRSComplex]]:
    """
    In case we process signal after we made some manual selections, we want to merge these two types of selections.
    Manual selections take precedence over these programmatically detected.
    """

    merged_annotations = existing_annotations.get(lead.label, [])

    if lead.ann.qrs_complex_positions:
        for c in lead.ann.qrs_complex_positions:
            overlapping = [
                True
                if do_annotations_overlap(c.onset, c.offset, x.onset, x.offset) is True
                else False
                for x in existing_annotations.get(lead.label, [])
            ]

            if not any(overlapping):
                merged_annotations.append(
                    QRSComplex(
                        c.onset,
                        c.offset,
                    )
                )

    return lead.label, merged_annotations
