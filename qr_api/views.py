from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Person
from .serializers import PersonSerializer


def get_person_url(request, person_id):
    path = reverse("person_detail", kwargs={"person_id": person_id})
    return request.build_absolute_uri(path)


def get_qr_image_url(request, person_url):
    return person_url


# Helper functions
def int_to_bits(value, length):
    return [(value >> i) & 1 for i in range(length - 1, -1, -1)]

def bits_to_int(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value

def generate_qr_matrix(person_url):
    return generate_qr_matrix(person_url)


def matrix_to_svg(matrix):
    size = len(matrix)
    module_size = 10
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{size * module_size}" height="{size * module_size}">'
    ]
    for y, row in enumerate(matrix):
        for x, bit in enumerate(row):
            if bit:
                svg.append(
                    f'<rect x="{x * module_size}" y="{y * module_size}" '
                    f'width="{module_size}" height="{module_size}" fill="#000"/>'
                )
    svg.append("</svg>")
    return "".join(svg)


class GenerateQRCodeAPIView(APIView):
    def post(self, request):
        name = request.data.get("name")
        age = request.data.get("age")
        email = request.data.get("email")
        person_id = request.data.get("person_id")
        city = request.data.get("city")

        if name in [None, ""] or age in [None, ""] or email in [None, ""] or person_id in [None, ""] or city in [None, ""]:
            return Response(
                {"error": "All fields are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            age = int(age)
        except ValueError:
            return Response(
                {"error": "Age must be a number"},
                status=status.HTTP_400_BAD_REQUEST
            )

        person = Person.objects.create(
            name=name,
            age=age,
            email=email,
            person_id=person_id,
            city=city
        )

        person_url = get_person_url(request, person.id)
        qr_image_url = get_qr_image_url(request, person.id)

        try:
            pass
            generate_qr_matrix(person_url)
        except ValueError as error:
            person.delete()
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "message": "Data saved and QR code generated successfully",
            "person_database_id": person.id,
            "qr_contains": person_url,
            "qr_image_url": qr_image_url,
            "person_data_url": person_url
        })


class PersonQRCodeImageView(APIView):
    def get(self, request, person_id):
        try:
            person = Person.objects.get(id=person_id)
        except Person.DoesNotExist:
            return Response({
                "error":"Person not found"
            },
            status=status.HTTP_404_NOT_FOUND
            )
        person_url = get_person_url(request, person.id)
        try:
            matrix = generate_qr_matrix(person_url)
            svg = matrix_to_svg(matrix)
        except ValueError as error:
            return Response({
                "error":str(error)
            },
            status=status.HTTP_400_BAD_REQUEST
            )
        return HttpResponse(svg, content_type="image/svg+xml")


class PersonDetailAPIView(APIView):
    def get(self, request, person_id):
        try:
            person = Person.objects.get(id=person_id)
        except Person.DoesNotExist:
            return Response(
                {"error": "Person not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PersonSerializer(person)
        return Response(serializer.data)




def get_person_url( request, person_id):
        path = reverse("person_detail", kwargs={"person_id": person_id})
        return request.build_absolute_uri(path)
def get_qr_image_url( request, person_id):
        path = reverse("person_qr_image", kwargs={"person_id": person_id})
        return request.build_absolute_uri(path)


# manual QR code generation functions
# QR Version 5-L
QR_VERSION = 5
QR_SIZE = 21 + (QR_VERSION-1)*4
DATA_CODEWORDS = 108
ERROR_CODEWORDS = 26
MAX_INPUT_BYTES = 106

MASK_PATTERN = 0

def generate_qr_matrix(text):
    data_bytes = text.encode("utf-8")

    if len(data_bytes) > MAX_INPUT_BYTES:
        raise ValueError(
            f"Input data exceeds maximum capacity of {MAX_INPUT_BYTES} bytes "
            f"for QR version {QR_VERSION} with error correction level L."
        )
    data_codewords = create_data_codewords(data_bytes)
    error_codewords = create_error_correction_codewords(data_codewords)

    final_codewords = data_codewords + error_codewords
    final_bits = codewords_to_bits(final_codewords)

    matrix = [[False for _ in range(QR_SIZE)] for _ in range(QR_SIZE)]
    reserved = [[False for _ in range(QR_SIZE)] for _ in range(QR_SIZE)]
    add_finder_patterns(matrix, reserved)
    add_alignment_patterns(matrix, reserved)
    add_timing_patterns(matrix, reserved)
    add_format_information(matrix, reserved, MASK_PATTERN)
    add_data_bits(matrix, reserved, final_bits, MASK_PATTERN)

    return matrix
def create_data_codewords(data_bytes):
    bits = []

    # Byte mode indicator
    bits.extend([0, 1, 0, 0])

    # Character count
    length = len(data_bytes)
    bits.extend(int_to_bits(length, 8))

    for byte in data_bytes:
        bits.extend(int_to_bits(byte, 8))

    # Terminator bits
    max_bits = DATA_CODEWORDS * 8
    remaining_bits = max_bits - len(bits)
    bits.extend([0] * min(4, remaining_bits))

    # Make bits multiple of 8
    while len(bits) % 8 != 0:
        bits.append(0)

    # Convert bits to codewords
    codewords = []

    for i in range(0, len(bits), 8):
        codewords.append(bits_to_int(bits[i:i + 8]))

    # Padding bytes
    pad_bytes = [0xEC, 0x11]
    pad_index = 0

    while len(codewords) < DATA_CODEWORDS:
        codewords.append(pad_bytes[pad_index % 2])
        pad_index += 1

    return codewords


def create_error_correction_codewords(data_codewords):
    # Generator polynomial for Reed-Solomon. Provide implementation here
    generator = reed_solomon_generator(ERROR_CODEWORDS)
    result = [0] * ERROR_CODEWORDS

    for data_byte in data_codewords:
        factor = data_byte ^ result[0]
        result = result[1:] + [0]

        for i in range(ERROR_CODEWORDS):
            result[i] ^= gf_multiply(generator[i + 1], factor)

    return result


def codewords_to_bits(codewords):
    bits = []

    for codeword in codewords:
        bits.extend(int_to_bits(codeword, 8))
        
    return bits
def reed_solomon_generator(degree):
    generator = [1]

    for i in range(degree):
        generator = polynomial_multiply(generator, [1, gf_power(2, i)])

    return generator


def polynomial_multiply(poly1, poly2):
    result = [0] * (len(poly1) + len(poly2) - 1)

    for i in range(len(poly1)):
        for j in range(len(poly2)):
            result[i + j] ^= gf_multiply(poly1[i], poly2[j])

    return result


def gf_power(value, power):
    result = 1

    for _ in range(power):
        result = gf_multiply(result, value)

    return result


def gf_multiply(x, y):
    result = 0

    while y > 0:
        if y & 1:
            result ^= x

        x <<= 1

        if x & 0x100:
            x ^= 0x11D

        y >>= 1

    return result

def is_inside(row, col):
    return 0 <= row < QR_SIZE and 0 <= col < QR_SIZE


def add_finder_pattern(matrix, reserved, start_row, start_col):
    for row_offset in range(-1, 8):
        for col_offset in range(-1, 8):
            row = start_row + row_offset
            col = start_col + col_offset

            if not is_inside(row, col):
                continue

            dark = False

            if 0 <= row_offset <= 6 and 0 <= col_offset <= 6:
                if (
                    row_offset in [0, 6]
                    or col_offset in [0, 6]
                    or (2 <= row_offset <= 4 and 2 <= col_offset <= 4)
                ):
                    dark = True

            matrix[row][col] = dark
            reserved[row][col] = True


def add_finder_patterns(matrix, reserved):
    add_finder_pattern(matrix, reserved, 0, 0)
    add_finder_pattern(matrix, reserved, 0, QR_SIZE - 7)
    add_finder_pattern(matrix, reserved, QR_SIZE - 7, 0)


def add_alignment_pattern(matrix, reserved, center_row, center_col):
    for row_offset in range(-2, 3):
        for col_offset in range(-2, 3):
            row = center_row + row_offset
            col = center_col + col_offset

            if not is_inside(row, col):
                continue

            dark = (
                abs(row_offset) == 2
                or abs(col_offset) == 2
                or (row_offset == 0 and col_offset == 0)
            )
            matrix[row][col] = dark
            reserved[row][col] = True


def add_alignment_patterns(matrix, reserved):
    centers = [6, 30]
    for center_row in centers:
        for center_col in centers:
            if reserved[center_row][center_col]:
                continue
            add_alignment_pattern(matrix, reserved, center_row, center_col)


def add_timing_patterns(matrix, reserved):
    for i in range(8, QR_SIZE - 8):
        dark = i % 2 == 0
        matrix[6][i] = dark
        reserved[6][i] = True
        matrix[i][6] = dark
        reserved[i][6] = True


def get_bit(value, index):
    return ((value >> index) & 1) == 1


def set_module(matrix, reserved, row, col, value):
    matrix[row][col] = value
    reserved[row][col] = True


def add_format_information(matrix, reserved, mask_pattern):
    error_level_bits = 0b01
    format_bits = calculate_format_bits(error_level_bits, mask_pattern)

    for i in range(10):
        set_module(matrix, reserved, 8, i, get_bit(format_bits, i))

    set_module(matrix, reserved, 8, 7, get_bit(format_bits, 6))
    set_module(matrix, reserved, 8, 8, get_bit(format_bits, 7))
    set_module(matrix, reserved, 7, 8, get_bit(format_bits, 8))

    for i in range(9, 15):
        set_module(matrix, reserved, 14 - i, 8, get_bit(format_bits, i))
        set_module(matrix, reserved, 8, QR_SIZE - 15 + i, get_bit(format_bits, i))

    for i in range(8):
        set_module(matrix, reserved, QR_SIZE - 1 - i, 8, get_bit(format_bits, i))

    for i in range(8, 15):
        set_module(matrix, reserved, 8, QR_SIZE - 15 + i, get_bit(format_bits, i))

    set_module(matrix, reserved, 8, QR_SIZE - 8, True)


def calculate_format_bits(error_level_bits, mask_pattern):
    data = (error_level_bits << 3) | mask_pattern
    value = data << 10
    generator = 0x537

    for i in range(14, 9, -1):
        if ((value >> i) & 1) == 1:
            value ^= generator << (i - 10)
    
    return ((data << 10) | value) ^ 0x5412


def should_apply_mask(row, col, mask_pattern):
    if mask_pattern == 0:
        return (row + col) % 2 == 0
    return False


def is_inside(row, col):
    return 0 <= row < QR_SIZE and 0 <= col < QR_SIZE


def add_data_bits(matrix, reserved, bits, mask_pattern):
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

                    if bit_index < len(bits):
                        bit = bits[bit_index] == 1
                        bit_index += 1

                    if should_apply_mask(row, current_col, mask_pattern):
                        bit = not bit

                    matrix[row][current_col] = bit

            row += direction

            if row < 0 or row >= QR_SIZE:
                row -= direction
                direction *= -1
                break

        col -= 2
def matrix_to_svg(matrix, box_size=10, border=4):
    size = len(matrix)
    total_size = (size + border * 2) * box_size
    svg_parts=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_size}" height="{total_size}">'
        f'viewBox="0 0 {total_size} {total_size}">',
        '<rect width="100%" height="100%" fill="white"/>'
    ]
    for row in range(size):
        for col in range(size):
            if matrix[row][col]:
                x = (col + border) * box_size
                y = (row + border) * box_size

                svg_parts.append(
                    f'<rect x="{x}" y="{y}" '
                    f'width="{box_size}" height="{box_size}" '
                    f'fill="black"/>'
                )

    svg_parts.append("</svg>")

    return "".join(svg_parts)
    

                                          

                                
 
                       
                        