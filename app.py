"""
Cosmic Keys - Data Sonification App
NASA Space Apps Challenge 2024

Turn planetary data into piano music. Because space should be heard, not just seen.

run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import os

from sonification import sonify_dataframe, sonify_planet, latitude_to_pitch, NOTE_NAMES, NOTE_VALUES
from synthesizer import generate_tone, mix_notes, to_wav_bytes, chord, SAMPLE_RATE
from image_scanner import scan_image, get_grid_visualization


# page config
st.set_page_config(
    page_title="Cosmic Keys",
    page_icon="",  # keeping it simple
    layout="wide"
)

# load css... kinda hacky but works
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        text-align: center;
        color: #888;
        margin-bottom: 2rem;
    }
    .note-display {
        font-family: monospace;
        padding: 8px;
        background: #1a1a2e;
        border-radius: 4px;
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Cosmic Keys</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Turning planetary data into piano music</div>', unsafe_allow_html=True)


@st.cache_data
def load_planet_data():
    """load the bundled CSV data"""
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'planets.csv')

    if os.path.exists(data_path):
        return pd.read_csv(data_path)
    else:
        # fallback with just a few planets if file is missing
        print("warning: planets.csv not found, using fallback data")
        return pd.DataFrame({
            'name': ['Earth', 'Mars', 'Jupiter'],
            'type': ['planet', 'planet', 'planet'],
            'latitude': [0.0, 1.85, 1.303],
            'longitude': [0.0, 49.558, 100.464],
            'velocity': [29.78, 24.07, 13.07],
            'temperature': [15, -65, -110],
            'diameter_km': [12756, 6792, 142984],
            'distance_from_sun_au': [1.0, 1.524, 5.203],
            'orbital_period_days': [365.25, 687.0, 4331.0],
        })


def render_planet_tab():
    """Tab 1: Planet/Moon Sonification from CSV data"""

    st.header("Planet Sonification")
    st.write("Select celestial bodies and hear their data as piano notes")

    df = load_planet_data()

    col1, col2 = st.columns([1, 2])

    with col1:
        # filter by type
        body_types = ['All'] + sorted(df['type'].unique().tolist())
        selected_type = st.selectbox("Filter by type", body_types)

        if selected_type != 'All':
            filtered_df = df[df['type'] == selected_type]
        else:
            filtered_df = df

        # select which bodies to sonify
        selected_names = st.multiselect(
            "Choose celestial bodies",
            filtered_df['name'].tolist(),
            default=filtered_df['name'].tolist()[:3]
        )

        if not selected_names:
            st.warning("pick at least one!")
            return

        selected_df = filtered_df[filtered_df['name'].isin(selected_names)]

        st.write("---")
        st.write("**Playback settings**")
        tempo = st.slider("Tempo (BPM)", 60, 200, 120)
        gap = 60.0 / tempo * 0.1  # gap between notes scales with tempo

        play_mode = st.radio("Play mode", ["Sequential", "Chord"])

    with col2:
        # sonify the selected data
        notes = sonify_dataframe(selected_df)

        if notes:
            # show data table
            st.write("**Sonification Mapping:**")
            mapping_data = []
            for n in notes:
                mapping_data.append({
                    'Body': n['name'],
                    'Note': n['note_name'],
                    'Freq (Hz)': f"{n['frequency']:.1f}",
                    'Duration': f"{n['duration']:.2f}s",
                    'Volume': f"{n['volume']:.0%}",
                    'Sustain': f"{n['sustain']:.2f}s",
                })

            st.dataframe(pd.DataFrame(mapping_data), use_container_width=True, hide_index=True)

            # generate audio
            if st.button("Play Sonification", key="play_planet"):
                with st.spinner("generating audio..."):
                    if play_mode == "Sequential":
                        audio = mix_notes(notes, gap=gap)
                    else:
                        # chord mode - all at once
                        freqs = [n['frequency'] for n in notes]
                        avg_dur = np.mean([n['duration'] for n in notes])
                        avg_vol = np.mean([n['volume'] for n in notes])
                        audio = chord(freqs, duration=max(avg_dur, 1.5), volume=avg_vol)

                    wav_bytes = to_wav_bytes(audio)
                    st.audio(wav_bytes, format='audio/wav')
                    st.success(f"played {len(notes)} notes")

            # show the raw data too
            with st.expander("Raw planetary data"):
                st.dataframe(selected_df, use_container_width=True, hide_index=True)


def render_scanner_tab():
    """Tab 2: Image Scanner - upload planet/moon images"""

    st.header("Image Scanner")
    st.write("Upload an image of a planet or moon and hear it as music")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded = st.file_uploader(
            "Upload a planet/moon image",
            type=['png', 'jpg', 'jpeg', 'webp'],
            key="img_upload"
        )

        # scanner settings
        grid_size = st.slider("Grid size", 3, 12, 6, help="How many rows/cols to divide the image into")

        scan_mode = st.selectbox(
            "Scanning mode",
            ['brightness', 'color', 'contrast'],
            help="How to map image data to notes"
        )

        # TODO: add option to scan in spiral pattern from center outward
        # that would be cool for circular planet images

        note_gap = st.slider("Note spacing (ms)", 10, 200, 50)

    with col2:
        if uploaded is not None:
            # show original image
            st.image(uploaded, caption="Uploaded image", use_container_width=True)

            # do the scan
            notes, grid, processed_img = scan_image(uploaded, grid_size=grid_size, mode=scan_mode)

            # show grid visualization
            grid_vis = get_grid_visualization(grid)
            st.image(grid_vis, caption=f"Grid analysis ({grid_size}x{grid_size})", use_container_width=True)

            st.write(f"**{len(notes)} notes** generated from {grid_size}x{grid_size} grid")

            # show first few notes
            preview_notes = notes[:min(8, len(notes))]
            note_str = " | ".join([f"{n['note_name']}" for n in preview_notes])
            st.code(f"First notes: {note_str}{'...' if len(notes) > 8 else ''}")

            if st.button("Play Image", key="play_image"):
                with st.spinner("synthesizing..."):
                    audio = mix_notes(notes, gap=note_gap/1000.0)
                    wav_bytes = to_wav_bytes(audio)
                    st.audio(wav_bytes, format='audio/wav')

                    # show some stats
                    total_dur = sum(n['duration'] for n in notes) + (note_gap/1000.0 * len(notes))
                    st.info(f"Total duration: {total_dur:.1f}s | Notes: {len(notes)} | Mode: {scan_mode}")
        else:
            st.info("Upload an image to get started! Try a photo of the Moon, Mars, Jupiter...")

            # show a demo with a generated gradient
            st.write("---")
            st.write("**Demo: Generated gradient**")
            if st.button("Generate demo"):
                # create a simple gradient image as demo
                demo = np.zeros((256, 256, 3), dtype=np.uint8)
                for y in range(256):
                    for x in range(256):
                        demo[y, x] = [x, y, 128]

                demo_img = Image.fromarray(demo)
                st.image(demo_img, caption="Demo gradient", width=200)

                notes, grid, _ = scan_image(demo_img, grid_size=grid_size, mode=scan_mode)
                audio = mix_notes(notes, gap=note_gap/1000.0)
                wav_bytes = to_wav_bytes(audio)
                st.audio(wav_bytes, format='audio/wav')


def render_composer_tab():
    """Tab 3: Composer mode - custom data mapping"""

    st.header("Composer Mode")
    st.write("Map any data column to musical parameters")

    df = load_planet_data()

    # let users pick which columns map to what
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.write("**Data Mapping**")

        pitch_col = st.selectbox("Pitch (note frequency)", numeric_cols,
                                  index=numeric_cols.index('latitude') if 'latitude' in numeric_cols else 0)

        duration_col = st.selectbox("Duration (note length)", numeric_cols,
                                     index=numeric_cols.index('longitude') if 'longitude' in numeric_cols else 0)

        volume_col = st.selectbox("Volume (loudness)", numeric_cols,
                                   index=numeric_cols.index('velocity') if 'velocity' in numeric_cols else 0)

        sustain_col = st.selectbox("Sustain (ring out time)", numeric_cols,
                                    index=numeric_cols.index('temperature') if 'temperature' in numeric_cols else 0)

        st.write("---")

        # pitch range
        pitch_range = st.select_slider(
            "Pitch range",
            options=['C3-C4', 'C3-C5', 'C3-C6', 'C4-C5', 'C4-C6'],
            value='C3-C6'
        )

        duration_range = st.slider("Duration range (s)", 0.1, 2.0, (0.15, 0.8))

        # which bodies to include
        selected = st.multiselect(
            "Bodies to include",
            df['name'].tolist(),
            default=df['name'].tolist()
        )

    with col2:
        if not selected:
            st.warning("select some celestial bodies!")
            return

        sub_df = df[df['name'].isin(selected)]

        # build custom mapping
        notes = []

        # normalize each column
        def normalize_col(series):
            mn, mx = series.min(), series.max()
            if mx == mn:
                return pd.Series([0.5] * len(series), index=series.index)
            return (series - mn) / (mx - mn)

        pitch_norm = normalize_col(sub_df[pitch_col])
        dur_norm = normalize_col(sub_df[duration_col])
        vol_norm = normalize_col(sub_df[volume_col])
        sus_norm = normalize_col(sub_df[sustain_col])

        # figure out pitch range bounds
        range_parts = pitch_range.split('-')
        start_idx = NOTE_NAMES.index(range_parts[0])
        end_idx = NOTE_NAMES.index(range_parts[1])
        available_notes = NOTE_NAMES[start_idx:end_idx+1]
        available_freqs = NOTE_VALUES[start_idx:end_idx+1]

        for i, (_, row) in enumerate(sub_df.iterrows()):
            pn = pitch_norm.iloc[i]
            dn = dur_norm.iloc[i]
            vn = vol_norm.iloc[i]
            sn = sus_norm.iloc[i]

            note_idx = int(pn * (len(available_freqs) - 1))
            note_idx = min(note_idx, len(available_freqs) - 1)

            freq = available_freqs[note_idx]
            note_name = available_notes[note_idx]
            duration = duration_range[0] + dn * (duration_range[1] - duration_range[0])
            volume = 0.15 + vn * 0.75
            sustain = 0.05 + sn * 0.5

            notes.append({
                'name': row['name'],
                'frequency': freq,
                'note_name': note_name,
                'duration': round(duration, 3),
                'volume': round(volume, 3),
                'sustain': round(sustain, 3),
            })

        # display mapping
        st.write("**Generated Composition:**")
        comp_data = []
        for n in notes:
            comp_data.append({
                'Body': n['name'],
                'Note': n['note_name'],
                'Freq': f"{n['frequency']:.0f} Hz",
                'Duration': f"{n['duration']:.2f}s",
                'Volume': f"{n['volume']:.0%}",
                'Sustain': f"{n['sustain']:.2f}s",
            })

        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        # playback controls
        pcol1, pcol2 = st.columns(2)
        with pcol1:
            play_seq = st.button("Play Sequence", key="comp_seq")
        with pcol2:
            play_chord_btn = st.button("Play as Chord", key="comp_chord")

        if play_seq:
            with st.spinner("composing..."):
                audio = mix_notes(notes, gap=0.05)
                wav_bytes = to_wav_bytes(audio)
                st.audio(wav_bytes, format='audio/wav')

        if play_chord_btn:
            with st.spinner("composing..."):
                freqs = [n['frequency'] for n in notes]
                audio = chord(freqs, duration=2.0, volume=0.6)
                wav_bytes = to_wav_bytes(audio)
                st.audio(wav_bytes, format='audio/wav')

        # visualization - simple bar chart of frequencies
        st.write("---")
        st.write("**Frequency Distribution**")
        freq_df = pd.DataFrame({
            'Body': [n['name'] for n in notes],
            'Frequency (Hz)': [n['frequency'] for n in notes],
        })
        st.bar_chart(freq_df.set_index('Body'))


# main app with tabs
tab1, tab2, tab3 = st.tabs(["Planet Sonification", "Image Scanner", "Composer"])

with tab1:
    render_planet_tab()

with tab2:
    render_scanner_tab()

with tab3:
    render_composer_tab()


# footer
st.write("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 0.85rem;'>"
    "Cosmic Keys | NASA Space Apps Challenge 2024 | "
    "Data sonification of planetary bodies"
    "</div>",
    unsafe_allow_html=True
)
