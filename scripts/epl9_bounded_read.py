"""Standalone finite-read experiment. No firmware patch or camera deployment.

Uses the existing extended emitter as an assembly utility only. The SD loader
itself is not built or modified. Independent GNU decoding is required by probe.
"""
from epl9_workspace_bridge import ROOT
from epl9_sd_loader import assemble

MODULE_BASE = 0x69200000  # Synthetic; no camera code slot is allocated.
TEMPLATE = ROOT/'firmware_src/epl9_bounded_read.s.in'


def build():
    source = TEMPLATE.read_text(encoding='utf-8')
    data, symbols, rows = assemble(source, MODULE_BASE)
    return dict(data=data, symbols=symbols, rows=rows, source=source)
