"""
Enhanced military classifier — heuristic rules + ML scoring.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── Layer 1: ICAO hex-prefix ranges ──────────────────────────────
# (hex_start, hex_end, label)
_HEX_RANGES: list[tuple[int, int, str]] = [
    (0xAE0000, 0xAEFFFF, "USAF"),
    (0xADF000, 0xADFFFF, "US DoD"),
    (0x43C000, 0x43CFFF, "RAF"),
    (0x43E000, 0x43EFFF, "RAF"),
    (0x3A0000, 0x3A7FFF, "Armée de l'Air"),
    (0x3C4000, 0x3C9FFF, "Luftwaffe"),
    (0x78100A, 0x7817FF, "VKS Russia"),
    (0x150000, 0x157FFF, "VKS Russia 2"),
    (0x710000, 0x710FFF, "PLAAF"),
    (0x780000, 0x780FFF, "PLAAF 2"),
    (0x730000, 0x737FFF, "IRIAF"),
    (0x800000, 0x83FFFF, "IAF"),
    (0x500000, 0x501FFF, "RCAF"),
    (0xC80000, 0xC82FFF, "RAAF"),
    (0x440000, 0x441FFF, "RNoAF"),
    (0x458000, 0x459FFF, "RDAF"),
    (0x478000, 0x478FFF, "FiAF"),
    (0x4A0000, 0x4A1FFF, "Belgian AF"),
    (0x460000, 0x461FFF, "RNLAF"),
    (0x4A8000, 0x4A9FFF, "Swedish AF"),
    (0x340000, 0x3407FF, "Ejército del Aire"),
    (0x300200, 0x3003FF, "AMI Italy"),
    (0x4BA000, 0x4BAFFF, "TurAF"),
    (0xE40000, 0xE40FFF, "FAB Brazil"),
    (0x71A000, 0x71AFFF, "RSAF"),
    (0x738000, 0x73FFFF, "IAF Israel"),
    (0x87F000, 0x87FFFF, "JASDF"),
    (0x84F000, 0x84FFFF, "JMSDF"),
    (0x71B000, 0x71BFFF, "ROKAF"),
    (0x760000, 0x767FFF, "PAF"),
    (0x43F000, 0x43F0FF, "NATO"),
    # ── Expanded: more countries ──
    (0x3E8000, 0x3E8FFF, "Czech AF"),
    (0x480000, 0x480FFF, "Greek AF"),
    (0x4C0000, 0x4C0FFF, "Portuguese AF"),
    (0x700000, 0x700FFF, "Iraqi AF"),
    (0x510000, 0x510FFF, "NZ RNZAF"),
    (0x680000, 0x680FFF, "Singapore RSAF"),
    (0x3F0000, 0x3F0FFF, "Polish AF"),
    (0x4D0000, 0x4D0FFF, "Romanian AF"),
    (0x500800, 0x500FFF, "Canadian Forces"),
]

# ── Layer 2: callsign regex patterns ─────────────────────────────
_CS_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    r"^RCH\d",   r"^SPAR\d",  r"^FORTE\d",  r"^DOOM\d",
    r"^DUKE\d",  r"^REACH\d", r"^NCR\d",    r"^NAVY\d",
    r"^ARMY\d",  r"^USMC\d",  r"^KNIFE\d",  r"^EAGLE\d",
    r"^VIPER\d", r"^VAPOR\d", r"^TOPGUN",   r"^SHADOW",
    r"^GHOST\d", r"^DARK\d",  r"^PAT\d\d",  r"^BISON",
    r"^RRR\d",   r"^GAF\d",   r"^RFR\d",
    r"^NATO\d",  r"^AWACS",   r"^HELLAS",
    r"^IRI\d",   r"^IRIAF",   r"^IRAF\d",   r"^YAS\d",
    r"^IAF\d",   r"^INDIA\d", r"^RVF\d",    r"^VIP\d",
    r"^RUS\d",   r"^CCA\d",   r"^PLAAF",
    r"^GLEX\d",  r"^PTF\d",
    # ── Expanded ──
    r"^COBRA\d", r"^RAVEN\d", r"^HAWK\d",   r"^RAPTOR",
    r"^ATLAS\d", r"^TALON\d", r"^FURY\d",   r"^REAPER",
    r"^WOLF\d",  r"^STORM\d", r"^TITAN\d",  r"^OVERLORD",
]]


@dataclass
class ClassifyResult:
    military: bool
    confidence: float      # 0.0–1.0
    method: str            # "hex", "callsign", "ml", "none"
    label: str             # e.g. "USAF", "RAF"


def classify(icao24: str, callsign: str | None) -> ClassifyResult:
    """Classify an aircraft using heuristic rules."""
    # Layer 1 — hex
    try:
        val = int(icao24, 16)
        for lo, hi, label in _HEX_RANGES:
            if lo <= val <= hi:
                return ClassifyResult(military=True, confidence=0.95, method="hex", label=label)
    except (ValueError, TypeError):
        pass

    # Layer 2 — callsign
    cs = (callsign or "").strip()
    if cs:
        for pattern in _CS_PATTERNS:
            if pattern.match(cs):
                return ClassifyResult(military=True, confidence=0.85, method="callsign", label=cs[:4])

    return ClassifyResult(military=False, confidence=0.0, method="none", label="")
