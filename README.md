# Cosmic Keys - Planetary Data Sonification

> NASA Space Apps Challenge 2024 - Global Winner

Turn planetary data into piano music. Scan images of planets and moons, and hear them played as piano tones.

## What it does

- Takes real planetary data (longitude, latitude, velocity, temperature) and maps it to musical notes
- Scan any image of a planet/moon - it divides the image into a grid and turns brightness/color into piano notes
- Composer mode lets you pick which data columns map to which musical parameters
- Generates actual audio using numpy sine wave synthesis with ADSR envelopes

## How the mapping works

| Planetary Data | Musical Parameter |
|---|---|
| Latitude | Pitch (C3 to C6) |
| Longitude | Note duration |
| Orbital velocity | Volume |
| Surface temperature | Sustain time |

For image scanning:
- Image gets divided into NxN grid
- Each cell's brightness/color maps to a note
- Reads left-to-right, top-to-bottom
- Three modes: brightness, color channels, or contrast

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501

## Tech stack

- Python 3.10+
- Streamlit for the dashboard
- NumPy for audio synthesis
- Pillow for image processing
- Pandas for data handling

## The team

Built in 48 hours at NASA Space Apps Challenge 2024. We wanted to make space data accessible in a completely new way - through sound.

The idea came from wondering what Jupiter would sound like if you could "play" its orbital data on a piano. Turns out, the gas giants sound surprisingly mellow.

## Files

```
app.py              - main Streamlit dashboard (3 tabs)
sonification.py     - data-to-music mapping engine
synthesizer.py      - numpy sine wave piano tone generator
image_scanner.py    - image grid analysis -> notes
data/planets.csv    - sample planetary data
```

## License

MIT
