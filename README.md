<div align="center">

<img src="https://img.shields.io/badge/ROB--AI-by_KKEEY-1DB954?style=for-the-badge" alt="ROB-AI"/>
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
<img src="https://img.shields.io/badge/Audio-Harmonic_Mixing-8B5CF6?style=for-the-badge" alt="Audio"/>
<img src="https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge" alt="Proprietary"/>

<br/><br/>

# 🎚️ ROB-AI

### Music Analysis & Harmonic Fix Engine

*Analyzes tracks (key, BPM, energy), flags issues and builds harmonically coherent
mixes/playlists — the analytical brain behind KKEEY's DJ tooling.*

</div>

---

## ⚠️ Copyright Notice

> **© 2026 Kevin Kuck — All Rights Reserved.**
> Proprietary code. Unauthorized copying, distribution, or commercial use is strictly prohibited. See [`LICENSE`](./LICENSE).

---

## 📋 Overview

**ROB-AI** is a Python toolkit for **music analysis and harmonic mixing**. It extracts
musical features from audio, surfaces problems, and assembles harmonically coherent
sequences (Camelot-style key flow) — designed as the analysis layer for DJ/production
workflows.

## ✨ Features

- 🎼 **Track analysis** — key, BPM and energy detection (`analysis_engine.py`).
- 🔀 **Harmonic mixing** — coherent playlist/set building UI (`harmonic_mixing_ui.py`).
- 🧠 Rule-based harmonic flow (±1 Camelot step) for smooth transitions.

## 🚀 Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Audio analysis | (e.g. `librosa` / DSP libraries) |
| Core modules | `analysis_engine.py`, `harmonic_mixing_ui.py` |

## ⚙️ Getting Started

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # if present; otherwise install librosa/numpy etc.
python analysis_engine.py              # analyze tracks
python harmonic_mixing_ui.py           # harmonic mixing UI
```

## 🔒 Security

- No credentials are committed. Any API keys/paths belong in a gitignored **`.env`** (never hardcode).
- Audio files and personal libraries stay local — not committed to version control.
- Review dependencies periodically (`pip audit`).

## 📄 License

**Proprietary — © 2026 Kevin Kuck. All Rights Reserved.** See [`LICENSE`](./LICENSE).

<div align="center">

*Built by Kevin Kuck · KKI*

</div>
