#!/usr/bin/env python3
"""Entry point for the local, frozen E-PL9 research builder."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'scripts'))
try:
    from epl9_volunteer_builder import main
except ModuleNotFoundError as exc:
    if exc.name == 'PIL':
        raise SystemExit('Install the pinned dependency first: python -m pip install -r requirements.txt')
    raise
raise SystemExit(main())
