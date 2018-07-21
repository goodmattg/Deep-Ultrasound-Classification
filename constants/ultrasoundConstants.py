import numpy as np
from enum import Enum

FOCUS_HASH_LABEL = 'FOCUS'
FRAME_LABEL = 'FRAME'

class HSV_COLOR_THRESHOLD(Enum):
    LOWER = [60, 50, 50]
    UPPER = [100, 255, 255]

class HSV_GRAYSCALE_THRESHOLD(Enum):
    LOWER = [1, 1, 1]
    UPPER = [255, 255, 255]

class IMAGE_TYPE(Enum):
    GRAYSCALE = 'GRAYSCALE'
    COLOR = 'COLOR'
    
IMAGE_TYPE_LABEL = 'IMAGE_TYPE'

class READOUT_ABBREVS(Enum):
    COLOR_MODE = 'COLOR_MODE'
    COLOR_TYPE = 'COLOR_TYPE'
    RADIALITY = 'RADIALITY'
    RAD = 'RAD'
    ARAD = 'ARAD'
    COLOR_LEVEL = 'COL'
    CPA = 'CPA'
    WALL_FILTER = 'WF'
    PULSE_REPITITION_FREQUENCY = 'PRF'
    SIZE = 'SIZE'

TUMOR_UNSPECIFIED = 'UNSPEC'
TUMOR_BENIGN = 'BENIGN'
TUMOR_MALIGNANT = 'MALIGNANT'
TUMOR_TYPES = [TUMOR_BENIGN, TUMOR_MALIGNANT]

def tumor_integer_label(tumor_type):
    if tumor_type is TUMOR_BENIGN:
        return 0
    elif tumor_type is TUMOR_MALIGNANT:
        return 1
    else:
        return 2

TUMOR_TYPE_LABEL = 'TUMOR_TYPE'

WALL_FILTER_MODES = ['LOW', 'MED', 'HIGH']