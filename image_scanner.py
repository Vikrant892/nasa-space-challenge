"""
image_scanner.py - scan planet/moon images and turn them into music

the idea: divide an image into a grid, analyze each cell's brightness
and color, then map those to musical notes. so you literally "play"
a picture of jupiter or the moon

this was the part that got the judges excited at the hackathon
"""

import numpy as np
from PIL import Image, ImageFilter

# using the same note mapping from sonification module
from sonification import NOTE_FREQS, NOTE_NAMES, NOTE_VALUES


def load_and_resize(image_input, target_size=(256, 256)):
    """
    load image and resize to standard dimensions
    accepts file path string or PIL Image or uploaded file bytes
    """
    if isinstance(image_input, str):
        img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input
    elif hasattr(image_input, 'read'):
        img = Image.open(image_input)
    else:
        # assume its bytes or something
        import io
        img = Image.open(io.BytesIO(image_input))

    img = img.convert('RGB')
    img = img.resize(target_size, Image.LANCZOS)
    return img


def image_to_grid(img, grid_rows=8, grid_cols=8):
    """
    divide image into grid cells and compute stats for each cell

    returns a 2d list of dicts, each containing:
    - brightness: average brightness (0-255)
    - r, g, b: average color channels
    - contrast: std dev of brightness in that cell
    """
    arr = np.array(img)
    h, w = arr.shape[:2]

    cell_h = h // grid_rows
    cell_w = w // grid_cols

    grid = []

    for row in range(grid_rows):
        grid_row = []
        for col in range(grid_cols):
            y1 = row * cell_h
            y2 = (row + 1) * cell_h
            x1 = col * cell_w
            x2 = (col + 1) * cell_w

            cell = arr[y1:y2, x1:x2]

            # compute brightness (simple average of RGB)
            brightness = np.mean(cell)

            # individual channels
            r_avg = np.mean(cell[:,:,0])
            g_avg = np.mean(cell[:,:,1])
            b_avg = np.mean(cell[:,:,2])

            # contrast as standard deviation
            gray = np.mean(cell, axis=2)
            contrast = np.std(gray)

            grid_row.append({
                'brightness': float(brightness),
                'r': float(r_avg),
                'g': float(g_avg),
                'b': float(b_avg),
                'contrast': float(contrast),
                'row': row,
                'col': col,
            })

        grid.append(grid_row)

    return grid


def grid_to_notes(grid, mode='brightness'):
    """
    convert grid analysis to note parameters

    mode options:
    - 'brightness': brighter = higher pitch
    - 'color': red channel = pitch, green = duration, blue = volume
    - 'contrast': high contrast areas get emphasized

    reads left to right, top to bottom (like reading a book)
    """
    notes = []

    for row in grid:
        for cell in row:
            if mode == 'brightness':
                # map brightness (0-255) to note index
                norm_bright = cell['brightness'] / 255.0
                note_idx = int(norm_bright * (len(NOTE_VALUES) - 1))
                note_idx = min(note_idx, len(NOTE_VALUES) - 1)

                freq = NOTE_VALUES[note_idx]
                name = NOTE_NAMES[note_idx]

                # brighter = louder too
                volume = 0.2 + norm_bright * 0.7
                duration = 0.15 + (1 - norm_bright) * 0.25  # dark = longer notes
                sustain = 0.1 + norm_bright * 0.2

            elif mode == 'color':
                # red -> pitch
                norm_r = cell['r'] / 255.0
                note_idx = int(norm_r * (len(NOTE_VALUES) - 1))
                note_idx = min(note_idx, len(NOTE_VALUES) - 1)
                freq = NOTE_VALUES[note_idx]
                name = NOTE_NAMES[note_idx]

                # green -> duration (0.1 to 0.6s)
                norm_g = cell['g'] / 255.0
                duration = 0.1 + norm_g * 0.5

                # blue -> volume
                norm_b = cell['b'] / 255.0
                volume = 0.15 + norm_b * 0.75

                sustain = 0.2

            elif mode == 'contrast':
                # use contrast to weight the note
                norm_bright = cell['brightness'] / 255.0
                note_idx = int(norm_bright * (len(NOTE_VALUES) - 1))
                note_idx = min(note_idx, len(NOTE_VALUES) - 1)
                freq = NOTE_VALUES[note_idx]
                name = NOTE_NAMES[note_idx]

                # high contrast = louder and longer
                norm_contrast = min(cell['contrast'] / 80.0, 1.0)  # 80 is roughly max std dev
                volume = 0.1 + norm_contrast * 0.8
                duration = 0.1 + norm_contrast * 0.4
                sustain = 0.1 + norm_contrast * 0.3
            else:
                # fallback
                freq = 440
                name = 'A4'
                volume = 0.5
                duration = 0.3
                sustain = 0.2

            notes.append({
                'frequency': freq,
                'note_name': name,
                'duration': duration,
                'volume': round(volume, 3),
                'sustain': round(sustain, 3),
                'grid_pos': (cell['row'], cell['col']),
                'brightness': cell['brightness'],
            })

    return notes


def scan_image(image_input, grid_size=8, mode='brightness'):
    """
    main entry point - give it an image, get back notes

    image_input: file path, PIL Image, or file-like object
    grid_size: how many rows/cols to divide into (default 8x8 = 64 notes)
    mode: 'brightness', 'color', or 'contrast'

    returns: (notes_list, grid_data, processed_image)
    """
    img = load_and_resize(image_input)
    grid = image_to_grid(img, grid_size, grid_size)
    notes = grid_to_notes(grid, mode)

    return notes, grid, img


def get_grid_visualization(grid, img_size=256):
    """
    create a visualization of the grid analysis
    returns a PIL image with grid overlay showing brightness values
    """
    from PIL import ImageDraw, ImageFont

    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    vis = Image.new('RGB', (img_size, img_size), (30, 30, 30))
    draw = ImageDraw.Draw(vis)

    cell_w = img_size // cols
    cell_h = img_size // rows

    for row in grid:
        for cell in row:
            x1 = cell['col'] * cell_w
            y1 = cell['row'] * cell_h
            x2 = x1 + cell_w - 1
            y2 = y1 + cell_h - 1

            # color based on brightness
            b = int(cell['brightness'])
            b = min(255, max(0, b))
            draw.rectangle([x1, y1, x2, y2], fill=(b, b, b), outline=(100, 100, 100))

    return vis


# for testing
if __name__ == '__main__':
    # create a test gradient image
    print("creating test image...")
    test_img = Image.new('RGB', (256, 256))
    pixels = test_img.load()
    for y in range(256):
        for x in range(256):
            pixels[x, y] = (x, y, (x+y)//2)

    notes, grid, processed = scan_image(test_img, grid_size=4, mode='brightness')
    print(f"got {len(notes)} notes from 4x4 grid")

    for i, n in enumerate(notes[:4]):
        print(f"  note {i}: {n['note_name']} freq={n['frequency']:.1f} vol={n['volume']}")

    print("image scanner working ok")
