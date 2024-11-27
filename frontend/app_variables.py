from dataclasses import dataclass
from typing import Optional

from explorer.ECGExplorer import ECGExplorer


@dataclass
class AppVariables:
    """
    Container for all variables that we pass around the app.
    For these variables we don't need to implement pub-sub.
    """
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    explorer: Optional[ECGExplorer] = None
