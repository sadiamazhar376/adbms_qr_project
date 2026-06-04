QR_SIZE = 37
DATA_CODEWORDS = 108
ERROR_CODEWORDS = 26
MAX_INPUT_BYTES = 106

def int_to_bits(value, length):
    """Return the integer as a list of bits, most significant first."""
    return [(value >> i) & 1 for i in range(length - 1, -1, -1)]

def gf_multiply(x, y):
    """Multiply two numbers in the Galois Field GF(256)."""
    result = 0
    while y:
        if y & 1:
            result ^= x
        x = (x << 1) ^ 0x11D if x & 0x80 else x << 1
        y >>= 1
    return result & 0xFF

def reed_solomon_generator():
    """Build the Reed-Solomon generator polynomial."""
    generator = [1]
    power = 1
    for _ in range(ERROR_CODEWORDS):
        nxt = [0] * (len(generator) + 1)
        for j, coeff in enumerate(generator):
            nxt[j] ^= coeff
            nxt[j + 1] ^= gf_multiply(coeff, power)
        generator = nxt
        power = gf_multiply(power, 2)
    return generator

def error_codewords(data):
    """Compute the error-correction codewords for the data codewords."""
    generator = reed_solomon_generator()
    blocks = [0] * ERROR_CODEWORDS
    for byte in data:
        factor = byte ^ blocks[0]
        blocks = blocks[1:] + [0]
        for i in range(ERROR_CODEWORDS):
            blocks[i] ^= gf_multiply(generator[i + 1], factor)
    return blocks

def build_qr_matrix(text):
    """Encode text into a QR matrix (list of rows of booleans)."""
    data = text.encode("utf-8")
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("Data exceeds QR capacity limits.")

    # Byte mode header + length + data, then terminator and byte padding.
    bits = [0, 1, 0, 0] + int_to_bits(len(data), 8)
    for byte in data:
        bits += int_to_bits(byte, 8)
    bits += [0] * min(4, DATA_CODEWORDS * 8 - len(bits))
    bits += [0] * (-len(bits) % 8)

    codewords = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    # Fill the rest with the padding pattern, which always starts with 0xEC.
    pad = [0xEC, 0x11]
    pad_index = 0
    while len(codewords) < DATA_CODEWORDS:
        codewords.append(pad[pad_index % 2])
        pad_index += 1

    payload = codewords + error_codewords(codewords)
    final_bits = [bit for cw in payload for bit in int_to_bits(cw, 8)]

    matrix = [[False] * QR_SIZE for _ in range(QR_SIZE)]
    reserved = [[False] * QR_SIZE for _ in range(QR_SIZE)]
    add_finder_and_timing_patterns(matrix, reserved)
    add_alignment_patterns(matrix, reserved)
    add_format_information(matrix, reserved)
    add_data_bits(matrix, reserved, final_bits)
    return matrix

def add_finder_and_timing_patterns(matrix, reserved):
    """Draw the three finder squares and the timing lines."""
    for row in range(QR_SIZE):
        for col in range(QR_SIZE):
            in_finder = (
                (row < 8 and col < 8)
                or (row < 8 and col >= QR_SIZE - 8)
                or (row >= QR_SIZE - 8 and col < 8)
            )
            if in_finder:
                reserved[row][col] = True
                r = row if row < 8 else row - QR_SIZE + 7
                c = col if col < 8 else col - QR_SIZE + 7
                if 0 <= r <= 6 and 0 <= c <= 6:
                    matrix[row][col] = r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4)
            elif row == 6 or col == 6:
                reserved[row][col] = True
                matrix[row][col] = (row % 2 == 0) if col == 6 else (col % 2 == 0)

def add_alignment_patterns(matrix, reserved):
    """Draw the 5x5 alignment patterns for version 5."""
    for center_row in (6, 30):
        for center_col in (6, 30):
            if reserved[center_row][center_col]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    reserved[center_row + dr][center_col + dc] = True
                    matrix[center_row + dr][center_col + dc] = (
                        abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0)
                    )

def add_format_information(matrix, reserved):
    """Place the precomputed format bits for level L, mask 0."""
    # Precomputed 15-bit format string for error level L, mask 0: 111011111000100
    format_bits = [
        True, True, True, False, True, True, True, True,
        True, False, False, False, True, False, False,
    ]
    # The 15 format bits are written twice: once around the top-left finder,
    # and once split across the bottom-left and top-right finders.
    around_top_left = [(8, i) for i in range(6)] + [(8, 7), (8, 8), (7, 8)] + \
        [(14 - i, 8) for i in range(9, 15)]
    split_copy = [(QR_SIZE - 1 - i, 8) for i in range(8)] + \
        [(8, QR_SIZE - 15 + i) for i in range(8, 15)]
    for coords in (around_top_left, split_copy):
        for bit, (row, col) in zip(format_bits, coords):
            matrix[row][col] = bit
            reserved[row][col] = True
    matrix[8][QR_SIZE - 8] = True  # always-dark module
    reserved[8][QR_SIZE - 8] = True

def add_data_bits(matrix, reserved, final_bits):
    """Place data bits in the zig-zag order, applying mask pattern 0."""
    bit_index = 0
    row, col, direction = QR_SIZE - 1, QR_SIZE - 1, -1
    while col > 0:
        if col == 6:
            col -= 1
        while True:
            for current_col in (col, col - 1):
                if not reserved[row][current_col]:
                    bit = bit_index < len(final_bits) and final_bits[bit_index] == 1
                    bit_index += 1
                    if (row + current_col) % 2 == 0:
                        bit = not bit
                    matrix[row][current_col] = bit
            row += direction
            if not 0 <= row < QR_SIZE:
                row -= direction
                direction *= -1
                break
        col -= 2
def matrix_to_svg(matrix, box_size=10, border=4):
    """Render the QR matrix as an SVG string."""
    total = (len(matrix) + border * 2) * box_size
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{total}" '
        f'viewBox="0 0 {total} {total}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]
    for r, row in enumerate(matrix):
        for c, is_dark in enumerate(row):
            if is_dark:
                x = (c + border) * box_size
                y = (r + border) * box_size
                parts.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="black"/>')
    parts.append("</svg>")
    return "".join(parts)