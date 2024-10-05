"""
sonification.py - maps planetary data to musical parameters

basically the core "engine" that takes stuff like longitude, latitude,
velocity etc and turns it into note parameters for the synthesizer.

we use a pretty simple mapping but it sounds surprisingly good lol
"""

import numpy as np
import pandas as pd

# note frequencies for C3 to C6 range (chromatic scale)
# i looked these up on a piano frequency chart at like 2am during the hackathon
NOTE_FREQS = {
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56,
    'E3': 164.81, 'F3': 174.61, 'F#3': 185.00, 'G3': 196.00,
    'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13,
    'E4': 329.63, 'F4': 349.23, 'F#4': 369.99, 'G4': 392.00,
    'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25,
    'E5': 659.25, 'F5': 698.46, 'F#5': 739.99, 'G5': 783.99,
    'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77,
    'C6': 1046.50
}

NOTE_NAMES = list(NOTE_FREQS.keys())
NOTE_VALUES = list(NOTE_FREQS.values())


def latitude_to_pitch(lat):
    """
    map latitude (-90 to 90) to a note in C3-C6 range
    higher latitude = higher pitch, seemed intuitive
    """
    # normalize to 0-1
    normalized = (lat + 90) / 180.0
    normalized = np.clip(normalized, 0, 1)

    # pick note index
    idx = int(normalized * (len(NOTE_NAMES) - 1))
    note_name = NOTE_NAMES[idx]
    freq = NOTE_VALUES[idx]

    return freq, note_name


def longitude_to_duration(lon):
    """
    longitude (-180 to 180) -> note duration in seconds
    maps to roughly 0.15s to 1.2s
    shorter notes for negative longitudes, longer for positive
    """
    normalized = (lon + 180) / 360.0
    duration = 0.15 + normalized * 1.05
    return round(duration, 3)


def velocity_to_volume(vel, max_vel=None):
    """
    orbital velocity -> volume (0.0 to 1.0)
    faster = louder, because why not

    max_vel: if None we just normalize assuming a reasonable range
    """
    if max_vel is None:
        max_vel = 50.0  # km/s, rough upper bound for planets

    normalized = min(abs(vel) / max_vel, 1.0)
    # don't let it go completely silent
    volume = max(0.1, normalized)
    return round(volume, 3)


def temperature_to_sustain(temp, min_temp=-230, max_temp=470):
    """
    surface temperature -> sustain time
    hotter planets get longer sustain (they ring out more)
    cold ones are short and crisp

    temp in celsius
    """
    # normalize
    range_t = max_temp - min_temp
    if range_t == 0:
        return 0.3

    normalized = (temp - min_temp) / range_t
    normalized = np.clip(normalized, 0, 1)

    # sustain between 0.1 and 0.8 seconds
    sustain = 0.1 + normalized * 0.7
    return round(sustain, 3)


def sonify_planet(row):
    """
    take a row of planetary data and return note parameters

    expects columns: name, latitude, longitude, velocity, temperature
    (or close enough, we'll handle missing stuff)
    """
    lat = float(row.get('latitude', 0))
    lon = float(row.get('longitude', 0))
    vel = float(row.get('velocity', 10))
    temp = float(row.get('temperature', 15))  # default to earth-ish

    freq, note_name = latitude_to_pitch(lat)
    duration = longitude_to_duration(lon)
    volume = velocity_to_volume(vel)
    sustain = temperature_to_sustain(temp)

    return {
        'name': row.get('name', 'Unknown'),
        'frequency': freq,
        'note_name': note_name,
        'duration': duration,
        'volume': volume,
        'sustain': sustain,
        'lat': lat,
        'lon': lon,
    }


def sonify_dataframe(df):
    """
    process entire dataframe of planetary data
    returns list of note parameter dicts
    """
    notes = []
    for _, row in df.iterrows():
        try:
            note = sonify_planet(row)
            notes.append(note)
        except Exception as e:
            # skip bad rows, don't crash the whole thing
            print(f"warning: skipped row, error: {e}")
            continue

    return notes


def create_scale_from_data(values, num_notes=8):
    """
    take any array of numeric values and map them to a musical scale
    useful for the composer mode where users pick custom data columns
    """
    if len(values) == 0:
        return []

    min_v = np.min(values)
    max_v = np.max(values)

    if max_v == min_v:
        # everything maps to middle C lol
        return [NOTE_VALUES[len(NOTE_VALUES)//2]] * len(values)

    normalized = (np.array(values, dtype=float) - min_v) / (max_v - min_v)

    # pick evenly spaced notes from our range
    scale_indices = np.linspace(0, len(NOTE_VALUES)-1, num_notes, dtype=int)
    scale_freqs = [NOTE_VALUES[i] for i in scale_indices]

    result = []
    for v in normalized:
        idx = int(v * (num_notes - 1))
        idx = min(idx, num_notes - 1)
        result.append(scale_freqs[idx])

    return result


# quick test
if __name__ == '__main__':
    print("testing sonification mappings...")

    freq, name = latitude_to_pitch(0)
    print(f"  equator (lat=0) -> {name} ({freq:.1f} Hz)")

    freq, name = latitude_to_pitch(90)
    print(f"  north pole (lat=90) -> {name} ({freq:.1f} Hz)")

    dur = longitude_to_duration(0)
    print(f"  prime meridian (lon=0) -> {dur}s")

    vol = velocity_to_volume(13.07)  # earth orbital velocity
    print(f"  earth velocity (13.07 km/s) -> volume {vol}")

    sus = temperature_to_sustain(15)  # earth avg temp
    print(f"  earth temp (15C) -> sustain {sus}s")

    print("\ndone!")
