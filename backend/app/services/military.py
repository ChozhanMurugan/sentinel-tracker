"""
Military aircraft classification service.
Ported from the frontend js/config.js heuristics into Python.

Two-layer approach:
  1. ICAO 24-bit hex prefix block matching (most reliable)
  2. Callsign regex pattern matching (catches what hex misses)
"""
from __future__ import annotations
import re

# ── Layer 1: ICAO hex prefix blocks ───────────────────────────────
# Each entry: (hex_start, hex_end_inclusive, label)
_HEX_RANGES: list[tuple[int, int, str]] = [
    # United States
    (0xAE0000, 0xAEFFFF, "USAF"),
    (0xADF000, 0xADFFFF, "US DoD"),
    # United Kingdom
    (0x43C000, 0x43CFFF, "RAF"),
    (0x43E000, 0x43EFFF, "RAF"),
    # France
    (0x3A0000, 0x3A7FFF, "Armée de l'Air"),
    # Germany
    (0x3C4000, 0x3C9FFF, "Luftwaffe"),
    # Russia
    (0x78100A, 0x7817FF, "VKS Russia"),
    (0x150000, 0x157FFF, "VKS Russia 2"),
    # China
    (0x710000, 0x710FFF, "PLAAF"),
    (0x780000, 0x780FFF, "PLAAF 2"),
    # Iran
    (0x730000, 0x737FFF, "IRIAF"),
    # India
    (0x800000, 0x83FFFF, "IAF"),
    # Canada
    (0x500000, 0x501FFF, "RCAF"),
    # Australia
    (0xC80000, 0xC82FFF, "RAAF"),
    # Norway
    (0x440000, 0x441FFF, "RNoAF"),
    # Denmark
    (0x458000, 0x459FFF, "RDAF"),
    # Finland
    (0x478000, 0x478FFF, "FiAF"),
    # Belgium
    (0x4A0000, 0x4A1FFF, "Belgian AF"),
    # Netherlands
    (0x460000, 0x461FFF, "RNLAF"),
    # Sweden
    (0x4A8000, 0x4A9FFF, "Swedish AF"),
    # Spain
    (0x340000, 0x3407FF, "Ejército del Aire"),
    # Italy
    (0x300200, 0x3003FF, "AMI Italy"),
    # Turkey
    (0x4BA000, 0x4BAFFF, "TurAF"),
    # Brazil
    (0xE40000, 0xE40FFF, "FAB Brazil"),
    # Saudi Arabia
    (0x71A000, 0x71AFFF, "RSAF"),
    # Israel
    (0x738000, 0x73FFFF, "IAF Israel"),
    # Japan
    (0x87F000, 0x87FFFF, "JASDF"),
    (0x84F000, 0x84FFFF, "JMSDF"),
    # South Korea
    (0x71B000, 0x71BFFF, "ROKAF"),
    # Pakistan
    (0x760000, 0x767FFF, "PAF"),
    # NATO AWACS / special
    (0x43F000, 0x43F0FF, "NATO"),
]

# ── Layer 2: Callsign regex patterns ──────────────────────────────
_CS_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    # United States
    r"^RCH\d",      # USAF Air Mobility Command
    r"^SPAR\d",     # Special Air Mission (VIPs)
    r"^FORTE\d",    # USAF TACAMO
    r"^DOOM\d",
    r"^DUKE\d",
    r"^REACH\d",
    r"^NCR\d",
    r"^NAVY\d",
    r"^ARMY\d",
    r"^USMC\d",
    r"^KNIFE\d",
    r"^EAGLE\d",
    r"^VIPER\d",
    r"^VAPOR\d",
    r"^TOPGUN",
    r"^SHADOW",
    r"^GHOST\d",
    r"^DARK\d",
    r"^PAT\d\d",
    r"^BISON",
    # UK
    r"^RRR\d",
    r"^GAF\d",
    r"^RFR\d",
    # NATO / Allies
    r"^NATO\d",
    r"^AWACS",
    r"^HELLAS",
    # Iran
    r"^IRI\d",
    r"^IRIAF",
    r"^IRAF\d",
    r"^YAS\d",
    # India
    r"^IAF\d",
    r"^INDIA\d",
    r"^RVF\d",
    r"^VIP\d",      # Indian Govt VIP
    # Russia
    r"^RUS\d",
    # China
    r"^CCA\d",
    r"^PLAAF",
    # Misc
    r"^GLEX\d",     # Global Express mil variants
    r"^PTF\d",
]]


def classify(icao24: str, callsign: str | None) -> bool:
    """
    Return True if the aircraft is likely military.
    
    Args:
        icao24:   ICAO 24-bit hex string (e.g. "ae1234")
        callsign: ATC callsign (may be None or empty)

    Returns:
        bool — True = military
    """
    # Layer 1 — hex range check
    try:
        val = int(icao24, 16)
        for lo, hi, _ in _HEX_RANGES:
            if lo <= val <= hi:
                return True
    except (ValueError, TypeError):
        pass

    # Layer 2 — callsign pattern check
    cs = (callsign or "").strip()
    if cs:
        for pattern in _CS_PATTERNS:
            if pattern.match(cs):
                return True

    return False
