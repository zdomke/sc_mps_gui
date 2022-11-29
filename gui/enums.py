from enum import Enum


class DevThr(str, Enum):
    """Enum used for the Threshold Button in the Selection Details."""
    BPMS = "BPM"
    TORO = "CHRG"
    BLM = "I0_LOSS"
    BACT = "I0_BACT"


class ConfFiles(str, Enum):
    """Enum used for the Embedded Display in the Configure tab."""
    DEF = "resources/conf_def_embed.ui"
    BPMS = "resources/conf_bpm_embed.py"
    ERR = "resources/conf_err_embed.ui"
