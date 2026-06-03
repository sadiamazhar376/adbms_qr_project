
QR_VERSION = 5
QR_SIZE = 37
DATA_CODEWORDS = 108
ERROR_CODEWORDS = 26
MAX_INPUT_BYTES = 106
def int_to_bits(value, length):
    """Convert an integer into a list of binary bits."""
    return [(value >> i) & 1 for i in range(length - 1, -1, -1)]

def gf_multiply(x, y):
    """Galois Field multiplication over GF(256)."""
    result = 0
    while y > 0:
        if y & 1:
            result ^= x

        if x & 0x80:
            x = (x << 1) ^ 0x11D
        else:
            x = x << 1

        y >>= 1

    return result & 0xFF

def calculate_reed_solomon_generator():
    """Generate the Reed-Solomon generator polynomial."""
    generator = [1]

    for i in range(ERROR_CODEWORDS):
        next_poly = [0] * (len(generator) + 1)

        gf_power_value = 1
        for _ in range(i):
            gf_power_value = gf_multiply(gf_power_value, 2)

        for j, coefficient in enumerate(generator):
            next_poly[j] ^= coefficient
            next_poly[j + 1] ^= gf_multiply(coefficient, gf_power_value)

        generator = next_poly

    return generator


def create_error_codewords(data_codewords):
    """Create Reed-Solomon error correction codewords."""
    generator = calculate_reed_solomon_generator()
    error_blocks = [0] * ERROR_CODEWORDS

    for byte in data_codewords:
        factor = byte ^ error_blocks[0]
        error_blocks = error_blocks[1:] + [0]

        for i in range(ERROR_CODEWORDS):
            error_blocks[i] ^= gf_multiply(generator[i + 1], factor)

    return error_blocks

def build_qr_matrix(text):
    """Convert text into a QR matrix."""
    data_bytes = text.encode("utf-8")

    if len(data_bytes) > MAX_INPUT_BYTES:
        raise ValueError("Data exceeds QR capacity limits.")

    bit_stream = [0, 1, 0, 0]
    bit_stream += int_to_bits(len(data_bytes), 8)

    for byte in data_bytes:
        bit_stream += int_to_bits(byte, 8)

    bit_stream += [0] * min(4, DATA_CODEWORDS * 8 - len(bit_stream))

    while len(bit_stream) % 8 != 0:
        bit_stream.append(0)
    # Step Convert bits to codewords
    codewords = [0] * (len(bit_stream) // 8)

    for i, bit in enumerate(bit_stream):
        codewords[i // 8] = (codewords[i // 8] << 1) | bit
    #  Add QR padding bytes
    padding_patterns = [0xEC, 0x11]
    while len(codewords) < DATA_CODEWORDS:
        codewords.append(padding_patterns[len(codewords) % 2])
    # Step D: Add error correction
    error_codewords = create_error_codewords(codewords)
    full_payload = codewords + error_codewords

    final_bits = []

    for codeword in full_payload:
        final_bits += int_to_bits(codeword, 8)

    # Step E: Create blank matrix and reserved matrix
    matrix = [[False] * QR_SIZE for _ in range(QR_SIZE)]
    reserved = [[False] * QR_SIZE for _ in range(QR_SIZE)]

    add_finder_and_timing_patterns(matrix, reserved)
    add_alignment_patterns(matrix, reserved)
    add_format_information(matrix, reserved)
    add_data_bits(matrix, reserved, final_bits)

    return matrix

def add_finder_and_timing_patterns(matrix, reserved):
    """Add finder patterns and timing patterns."""
    for row in range(QR_SIZE):
        for col in range(QR_SIZE):
            is_finder_area = (
                (row < 8 and col < 8)
                or (row < 8 and col >= QR_SIZE - 8)
                or (row >= QR_SIZE - 8 and col < 8)
            )

            if is_finder_area:
                reserved[row][col] = True

                row_offset = row if row < 8 else row - QR_SIZE + 7
                col_offset = col if col < 8 else col - QR_SIZE + 7

                if 0 <= row_offset <= 6 and 0 <= col_offset <= 6:
                    matrix[row][col] = (
                        row_offset in [0, 6]
                        or col_offset in [0, 6]
                        or (2 <= row_offset <= 4 and 2 <= col_offset <= 4)
                    )

            elif row == 6 or col == 6:
                reserved[row][col] = True
                matrix[row][col] = (row % 2 == 0) if col == 6 else (col % 2 == 0)

def add_alignment_patterns(matrix, reserved):
    """Add alignment patterns for QR version 5."""
    for center_row in [6, 30]:
        for center_col in [6, 30]:
            if reserved[center_row][center_col]:
                continue

            for row_offset in range(-2, 3):
                for col_offset in range(-2, 3):
                    row = center_row + row_offset
                    col = center_col + col_offset

                    reserved[row][col] = True
                    matrix[row][col] = (
                        abs(row_offset) == 2
                        or abs(col_offset) == 2
                        or (row_offset == 0 and col_offset == 0)
                    )

def add_format_information(matrix, reserved):
    """Add precomputed format information for Level L and Mask 0."""
    format_bits = [
        True, False, True, False, True,
        False, True, True, True, False,
        True, True, True, False, True
    ]

    for i in range(6):
        matrix[8][i] = format_bits[i]
        reserved[8][i] = True

    matrix[8][7] = format_bits[6]
    reserved[8][7] = True

    matrix[8][8] = format_bits[7]
    reserved[8][8] = True

    matrix[7][8] = format_bits[8]
    reserved[7][8] = True

    for i in range(9, 15):
        matrix[14 - i][8] = format_bits[i]
        reserved[14 - i][8] = True

    for i in range(8):
        matrix[QR_SIZE - 1 - i][8] = format_bits[i]
        reserved[QR_SIZE - 1 - i][8] = True

    for i in range(8, 15):
        matrix[8][QR_SIZE - 15 + i] = format_bits[i]
        reserved[8][QR_SIZE - 15 + i] = True

    matrix[8][QR_SIZE - 8] = True
    reserved[8][QR_SIZE - 8] = True

def add_data_bits(matrix, reserved, final_bits):
    """Place data bits into the QR matrix using zig-zag placement."""
    bit_index = 0
    row = QR_SIZE - 1
    col = QR_SIZE - 1
    direction = -1

    while col > 0:
        if col == 6:
            col -= 1

        while True:
            for current_col in [col, col - 1]:
                if not reserved[row][current_col]:
                    bit = False

                    if bit_index < len(final_bits):
                        bit = final_bits[bit_index] == 1
                        bit_index += 1

                    # Mask pattern 0
                    if (row + current_col) % 2 == 0:
                        bit = not bit

                    matrix[row][current_col] = bit

            row += direction

            if row < 0 or row >= QR_SIZE:
                row -= direction
                direction *= -1
                break

        col -= 2

def matrix_to_svg(matrix, box_size=10, border=4):
    """Convert QR matrix into SVG image."""
    total_size = (len(matrix) + border * 2) * box_size

    svg_elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_size}" height="{total_size}" '
        f'viewBox="0 0 {total_size} {total_size}">',
        '<rect width="100%" height="100%" fill="white"/>'
    ]

    for row_index, row in enumerate(matrix):
        for col_index, is_dark in enumerate(row):
            if is_dark:
                x = (col_index + border) * box_size
                y = (row_index + border) * box_size

                svg_elements.append(
                    f'<rect x="{x}" y="{y}" '
                    f'width="{box_size}" height="{box_size}" '
                    f'fill="black"/>'
                )

    svg_elements.append("</svg>")

    return "".join(svg_elements)