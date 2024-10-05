"""
synthesizer.py - piano tone generator using numpy

generates sine wave tones with ADSR envelope to make them
sound vaguely piano-like. not gonna win any audio awards but
it works for a hackathon demo lol

uses 44100 Hz sample rate because thats standard
"""

import numpy as np
import struct
import io

SAMPLE_RATE = 44100


def adsr_envelope(length, attack=0.05, decay=0.1, sustain_level=0.7, release=0.15, sustain_time=0.3):
    """
    attempt at an ADSR envelope

    attack: time to reach peak (seconds)
    decay: time from peak to sustain level
    sustain_level: amplitude during sustain (0-1)
    release: time to fade to 0
    sustain_time: how long to hold at sustain level

    returns numpy array of envelope values
    """
    total_samples = length

    attack_samples = int(attack * SAMPLE_RATE)
    decay_samples = int(decay * SAMPLE_RATE)
    sustain_samples = int(sustain_time * SAMPLE_RATE)
    release_samples = int(release * SAMPLE_RATE)

    # make sure we don't exceed total length
    total_adsr = attack_samples + decay_samples + sustain_samples + release_samples
    if total_adsr > total_samples:
        # scale everything down proportionally
        scale = total_samples / total_adsr
        attack_samples = int(attack_samples * scale)
        decay_samples = int(decay_samples * scale)
        sustain_samples = int(sustain_samples * scale)
        release_samples = total_samples - attack_samples - decay_samples - sustain_samples

    envelope = np.zeros(total_samples)

    pos = 0

    # attack: 0 -> 1
    if attack_samples > 0:
        envelope[pos:pos+attack_samples] = np.linspace(0, 1, attack_samples)
        pos += attack_samples

    # decay: 1 -> sustain_level
    if decay_samples > 0:
        envelope[pos:pos+decay_samples] = np.linspace(1, sustain_level, decay_samples)
        pos += decay_samples

    # sustain: hold at sustain_level
    if sustain_samples > 0:
        envelope[pos:pos+sustain_samples] = sustain_level
        pos += sustain_samples

    # release: sustain_level -> 0
    remaining = total_samples - pos
    if remaining > 0:
        envelope[pos:] = np.linspace(sustain_level, 0, remaining)

    return envelope


def generate_tone(frequency, duration, volume=0.8, sustain_time=0.3):
    """
    generate a piano-ish tone at the given frequency

    we layer a few harmonics to make it sound less like a pure sine wave
    real pianos have way more complex harmonics but this is close enough
    """
    num_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)

    # fundamental
    wave = np.sin(2 * np.pi * frequency * t)

    # add some harmonics for richness
    # 2nd harmonic at lower volume
    wave += 0.5 * np.sin(2 * np.pi * (frequency * 2) * t)
    # 3rd harmonic even quieter
    wave += 0.25 * np.sin(2 * np.pi * (frequency * 3) * t)
    # 4th harmonic barely there
    wave += 0.125 * np.sin(2 * np.pi * (frequency * 4) * t)

    # normalize before envelope
    wave = wave / np.max(np.abs(wave))

    # apply ADSR
    env = adsr_envelope(
        num_samples,
        attack=0.01,    # piano has fast attack
        decay=0.08,
        sustain_level=0.6,
        release=duration * 0.3,
        sustain_time=sustain_time
    )
    wave = wave * env

    # apply volume
    wave = wave * volume

    # soft clip to avoid harshness
    wave = np.tanh(wave * 1.5) / 1.5

    return wave


def mix_notes(notes_params, gap=0.05):
    """
    take a list of note parameter dicts and create a mixed audio sequence

    notes_params: list of dicts with keys: frequency, duration, volume, sustain
    gap: silence between notes in seconds

    returns: numpy array of audio samples
    """
    if not notes_params:
        return np.zeros(SAMPLE_RATE)  # 1 sec of silence

    gap_samples = int(gap * SAMPLE_RATE)
    silence = np.zeros(gap_samples)

    parts = []
    for note in notes_params:
        freq = note.get('frequency', 440)
        dur = note.get('duration', 0.5)
        vol = note.get('volume', 0.7)
        sus = note.get('sustain', 0.3)

        tone = generate_tone(freq, dur, vol, sus)
        parts.append(tone)
        parts.append(silence)

    audio = np.concatenate(parts)

    # final normalization
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.9

    return audio


def chord(frequencies, duration=1.0, volume=0.6, sustain_time=0.4):
    """
    play multiple notes simultaneously
    for when you want to hear a whole planet at once lol
    """
    num_samples = int(SAMPLE_RATE * duration)
    mixed = np.zeros(num_samples)

    for freq in frequencies:
        tone = generate_tone(freq, duration, volume / len(frequencies), sustain_time)
        # make sure lengths match (they should but just in case)
        min_len = min(len(mixed), len(tone))
        mixed[:min_len] += tone[:min_len]

    # normalize
    peak = np.max(np.abs(mixed))
    if peak > 0:
        mixed = mixed / peak * 0.9

    return mixed


def to_wav_bytes(audio_data):
    """
    convert numpy audio array to WAV format bytes
    needed for streamlit's audio player

    returns bytes object containing valid WAV file
    """
    # convert to 16-bit PCM
    audio_16bit = np.int16(audio_data * 32767)

    buf = io.BytesIO()

    # write WAV header manually because i didn't want to add another dependency
    num_samples = len(audio_16bit)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = SAMPLE_RATE * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    # RIFF header
    buf.write(b'RIFF')
    buf.write(struct.pack('<I', 36 + data_size))
    buf.write(b'WAVE')

    # fmt chunk
    buf.write(b'fmt ')
    buf.write(struct.pack('<I', 16))  # chunk size
    buf.write(struct.pack('<H', 1))   # PCM format
    buf.write(struct.pack('<H', num_channels))
    buf.write(struct.pack('<I', SAMPLE_RATE))
    buf.write(struct.pack('<I', byte_rate))
    buf.write(struct.pack('<H', block_align))
    buf.write(struct.pack('<H', bits_per_sample))

    # data chunk
    buf.write(b'data')
    buf.write(struct.pack('<I', data_size))
    buf.write(audio_16bit.tobytes())

    buf.seek(0)
    return buf.read()


# TODO: add reverb effect? would make it sound way more spacey
# maybe in v2 if we have time


if __name__ == '__main__':
    print("generating test tone...")
    tone = generate_tone(440, 1.0, 0.8, 0.4)
    print(f"  samples: {len(tone)}")
    print(f"  peak: {np.max(np.abs(tone)):.3f}")
    print(f"  duration: {len(tone)/SAMPLE_RATE:.2f}s")

    wav_data = to_wav_bytes(tone)
    print(f"  wav size: {len(wav_data)} bytes")

    # write test file
    with open('test_tone.wav', 'wb') as f:
        f.write(wav_data)
    print("  wrote test_tone.wav")
    print("done!")
