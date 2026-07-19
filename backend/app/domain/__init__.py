"""The coaching knowledge layer.

Everything the generator and progression engine "know" about training lives in
the JSON files next to this module — exercises (with spine-conscious
contraindication tags and coaching cues), split templates, and progression
parameters. Updating the coaching knowledge means editing those files and
re-seeding; no code changes. A vision-based assessor (Phase 2) will emit the
same gap-report schema these consumers already read.
"""

import json
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

# Muscles each assessment region maps to. Keys are the fixed checklist the
# self-report form (and later the vision assessor) must use.
REGION_MUSCLES = {
    "shoulder_width": ["delts_side"],
    "back_width": ["back_lats"],
    "back_thickness": ["back_upper"],
    "chest": ["chest"],
    "arms": ["biceps", "triceps"],
    "midsection": ["core"],
    "quads": ["quads"],
    "glutes_hams": ["glutes", "hamstrings"],
    "calves": ["calves"],
    "conditioning": ["conditioning"],
}

# Tags excluded when a program is generated spine-conscious.
SPINE_EXCLUDED_TAGS = frozenset(
    {"axial_load", "loaded_spinal_flexion", "unsupported_hinge", "loaded_rotation"}
)


@lru_cache
def load_exercises() -> dict:
    return json.loads((_DIR / "exercises.json").read_text())


@lru_cache
def load_splits() -> dict:
    return json.loads((_DIR / "splits.json").read_text())


@lru_cache
def load_progression() -> dict:
    return json.loads((_DIR / "progression.json").read_text())
