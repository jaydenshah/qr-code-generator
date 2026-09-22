from enum import Enum
from typing import Self

from gf256 import GF256
from polynomial import Polynomial

class Mode(Enum):
    NUMERIC = 0
    ALPHANUMERIC = 1
    BYTE = 2
    KANJI = 3

class ECC(Enum):
    L = 0
    M = 1
    Q = 2
    H = 3

class Bitstream:
    def __init__(self, max_length: int, init_bytes: list[int] = []) -> None:
        self.max_length: int = max_length
        self.bits: list[int] = []

        for init_byte in init_bytes:
            self.append(init_byte, 8)

    def __add__(self, other: Self) -> Self:
        sum_bitstream = type(self)(self.max_length + other.max_length)
        sum_bitstream.bits = self.bits + other.bits

        return sum_bitstream

    def append(self, value: int, length: int) -> None:
        if len(self.bits) >= self.max_length:
            return
        
        self.bits.extend([(value >> i) & 1 for i in range(length -1, -1, -1)])

        if len(self.bits) > self.max_length:
            self.bits = self.bits[:self.max_length]

    def is_full(self) -> bool:
        return len(self.bits) >= self.max_length

    def to_bytes(self) -> list[int]:
        bytes: list[int] = []
        for i in range(0, self.max_length, 8):
            bytes.append(0)
            for j in range(8):
                if i + j >= len(self.bits):
                    break

                bytes[-1] |= self.bits[i + j] << (7 - j)

        return bytes
    
class QR:
    _VALID_CHARACTERS: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

    def __init__(self, data: str = "", ecc: ECC = ECC.L, version: int = -1) -> None:
        self.data: str = data

        self.ecc: ECC = ecc
        if ecc != ECC.L:
            raise NotImplementedError("Haven't implemented other error correction levels yet")

        self.mode: Mode = self._determine_mode()

        if version == -1:
            self.version: int = self._determine_minimum_version()
        else:
            if version != 1:
                raise NotImplementedError("Haven't implemented other QR code versions yet")
            
            self.version: int = version

        self._GF: GF256 = GF256(0x11d, 2)
        self._P: Polynomial = Polynomial.fromGaloisField(self._GF)

        self._data_bitstream: Bitstream = self._generate_data_bitstream()
        self._ecc_bitstream: Bitstream = self._generate_ecc_bitstream()
        self._message_bitstream: Bitstream = self._data_bitstream + self._ecc_bitstream

        self.matrix: list[list[int]] = self._generate_matrix()

    def _determine_mode(self) -> Mode:
        for char in self.data:
            if char not in QR._VALID_CHARACTERS:
                raise NotImplementedError("Haven't implemented other modes yet")
            
        return Mode.ALPHANUMERIC

    def _determine_minimum_version(self) -> int:
        if 13 + 11 * (len(self.data) // 2) + 6 * (len(self.data) % 2) > 152:
            raise NotImplementedError("Size of data requires a QR code version that isn't implemented yet")

        return 1

    def _generate_data_bitstream(self) -> Bitstream:
        data_bitstream: Bitstream = Bitstream(152)

        data_bitstream.append(2, 4) # mode bits
        data_bitstream.append(len(self.data), 9) # char count bits

        # data bits
        for i in range(0, len(self.data) - 1, 2):
            data_bitstream.append(
                QR._VALID_CHARACTERS.index(self.data[i]) * 45 + 
                QR._VALID_CHARACTERS.index(self.data[i + 1]),
                11)

        if len(self.data) % 2 != 0:
            data_bitstream.append(QR._VALID_CHARACTERS.index(self.data[-1]), 6)

        data_bitstream.append(0, 4) # terminator bits
        while len(data_bitstream.bits) % 8 != 0:
            data_bitstream.append(0, 1) # extend bitstream to codeword boundary

        while not data_bitstream.is_full():
            data_bitstream.append(0b11101100, 8)
            data_bitstream.append(0b00010001, 8)

        return data_bitstream


        # data_bytes: list[int] = [0] * 19
        # data_bitstream_length: int = 13 + 11 * (len(self.data) // 2) + 6 * (len(self.data) % 2)

        # mode_bits: int = 2
        # char_count_bits: int = (len(self.data) & ((1 << 9) - 1))
        # char_bits: list[int] = [
        #     QR._VALID_CHARACTERS.index(self.data[i]) * 45 + QR._VALID_CHARACTERS.index(self.data[i + 1]) 
        #     for i in range(0, len(self.data) - 1, 2)
        # ]
        # if len(self.data) % 2 != 0:
        #     char_bits.append(QR._VALID_CHARACTERS.index(self.data[-1]))

        # data_bitstream_int: int = mode_bits
        # data_bitstream_int <<= 9
        # data_bitstream_int |= char_count_bits
        # for i in range(len(char_bits) - 1):
        #     data_bitstream_int <<= 11
        #     data_bitstream_int |= char_bits[i]

        # if len(self.data) != 0:
        #     if len(self.data) % 2 != 0:
        #         data_bitstream_int <<= 6
        #     else:
        #         data_bitstream_int <<= 11
        #     data_bitstream_int |= char_bits[-1]

        # data_bitstream_int <<= min(152 - data_bitstream_length, 4)
        # data_bitstream_length += min(152 - data_bitstream_length, 4)

        # data_bitstream_int <<= math.ceil(data_bitstream_length / 8) * 8 - data_bitstream_length
        # data_bitstream_length = math.ceil(data_bitstream_length / 8) * 8.

        # use_first_pad_codeword: bool = True
        # while data_bitstream_length < 152:
        #     data_bitstream_int <<= 8
        #     data_bitstream_int |= 0b11101100 if use_first_pad_codeword else 0b00010001
        #     data_bitstream_length += 8

        #     use_first_pad_codeword = not use_first_pad_codeword

        # for i in range(152 // 8):
        #     data_bytes[18 - i] = data_bitstream_int & ((1 << 8) - 1)
        #     data_bitstream_int >>= 8

        # return data_bytes

    def _generator_poly(self, ecc: int) -> list[int]:
        alpha_i: int = 1
        g_p: list[int] = [1]
        for _ in range(ecc):
            g_p = self._P.multiply(g_p, [1, alpha_i])
            alpha_i = self._GF.multiply(alpha_i, self._GF.primitive_p)

        return g_p

    def _generate_ecc_bitstream(self) -> Bitstream:
        data_bytes: list[int] = self._data_bitstream.to_bytes()
        generator: list[int] = self._generator_poly(7)

        ecc: list[int] = self._P.mod(data_bytes + [0] * 7, generator)

        return Bitstream(56, ecc)

    def _generate_format_bitstream(self) -> Bitstream:
        # format_int: int = 1
        # format_int <<= 3
        # format_int |= self.mask
        # format_poly: list[int] = [int((format_int << i) & (1 << 4) != 0) for i in range(5)] + [0] * 10
        # generator_poly: list[int] = [1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1]
        # ecc: list[int] = self._P.mod(format_poly, generator_poly)

        # for ecc_bit in ecc:
        #     format_int <<= 1
        #     format_int |= ecc_bit

        # format_int ^= 0b101010000010010

        # return format_int
        format_bitstream: Bitstream = Bitstream(15)
        format_bitstream.append(1, 2) # low ecc level
        format_bitstream.append(0, 3) # low

        format_generator: list[int] = [1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1]
        ecc: list[int] = self._P.mod(format_bitstream.bits + [0] * 10, format_generator)

        format_bitstream.bits += ecc

        format_mask: list[int] = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]
        format_bitstream.bits = [x ^ y for x, y in zip(format_bitstream.bits, format_mask)]

        return format_bitstream

    def _generate_matrix(self) -> list[list[int]]:
        def draw_square(value: int, top_left: tuple[int, int], bottom_right: tuple[int, int]) -> None:
            for y in range(top_left[1], bottom_right[1] + 1):
                for x in range(top_left[0], bottom_right[0] + 1):
                    matrix[y][x] = value

        def draw_finder_pattern(top_left: tuple[int, int]) -> None:
            draw_square(1, top_left, (top_left[0] + 6, top_left[1] + 6))
            draw_square(0, (top_left[0] + 1, top_left[1] + 1), (top_left[0] + 5, top_left[1] + 5))
            draw_square(1, (top_left[0] + 2, top_left[1] + 2), (top_left[0] + 4, top_left[1] + 4))

        def is_data_bit(coord: tuple[int, int]) -> bool:
            x: int = coord[0]
            y: int = coord[1]

            if x == 6 or y == 6:
                return False

            if x <= 8 and y <= 8:
                return False
            if x >= modules_per_side - 8 and y <= 8:
                return False
            if x <= 8 and y >= modules_per_side - 8:
                return False

            return True

        def print_matrix():
            print("\n\n")
            for thing in matrix:
                print("".join(map(lambda x: "██" if x == 1 else "  ", thing)))
            print("\n\n")

        modules_per_side: int = 17 + 4 * self.version
        matrix: list[list[int]] = [[0] * modules_per_side for _ in range(modules_per_side)]

        draw_finder_pattern((0, 0))
        draw_finder_pattern((0, modules_per_side - 7))
        draw_finder_pattern((modules_per_side - 7, 0))

        for i in range(8, modules_per_side - 8):
            if i % 2 == 0:
                matrix[i][6] = 1
                matrix[6][i] = 1

        message_byte_counter: int = 0
        bit_counter: int = 0
        for left_x in list(range(modules_per_side - 2, 6, -2)) + list(range(4, -1, -2)):
            if (left_x // 2) % 2 == 0:
                y_range: range = range(0, modules_per_side)
            else:
                y_range: range = range(modules_per_side - 1, -1, -1)

            for y in y_range:
                for x_offset in range(1, -1, -1):
                    if not is_data_bit((left_x + x_offset, y)):
                        continue

                    matrix[y][left_x + x_offset] = int((self._message_bytes[message_byte_counter] << bit_counter) & (1 << 7) != 0)
                    bit_counter = (bit_counter + 1) % 8

                    if bit_counter == 0:
                        message_byte_counter += 1

        self.mask: int = 0
        for y in range(modules_per_side):
            for x in range(modules_per_side):
                if not is_data_bit((x, y)):
                    continue

                if (x + y) % 2 == 0:
                    matrix[y][x] ^= 1

        format_int: int = self._generate_format_int()

        matrix[modules_per_side - 8][8] = 1
        for i in range(15):
            bit: int = (format_int >> i) & 1
            if i in range(0, 6):
                matrix[i][8] = bit
            elif i in range(6, 8):
                matrix[i + 1][8] = bit
            else:
                matrix[modules_per_side - 15 + i][8] = bit

        for i in range(15):
            bit: int = (format_int >> i) & 1
            if i in range(0, 8):
                matrix[8][modules_per_side - 1 - i] = bit
            elif i == 8:
                matrix[8][7] = bit
            else:
                matrix[8][14 - i] = bit

        print_matrix()

        return matrix
        
qr = QR("GOOGLE.COM")
