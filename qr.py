from enum import Enum
from typing import Callable, Iterator, Self

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
    def __init__(self, max_length: int) -> None:
        self.max_length: int = max_length
        self.bits: list[int] = []

    def __iter__(self) -> Iterator[int]:
        return iter(self.bits)

    def __reversed__(self) -> Iterator[int]:
        return reversed(self.bits)

    def __str__(self) -> str:
        if self.max_length % 8 == 0:
            return " ".join([f"{byte:02x}" for byte in self.to_bytes()])
        else:
            return " ".join([str(bit) for bit in self.bits])

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
        self._format_bitstream: Bitstream = self._generate_format_bitstream()

        self.matrix: QRMatrix = QRMatrix(17 + self.version * 4)
        self.matrix.insert_message_bitstream(self._message_bitstream)
        self.matrix.apply_mask(lambda x, y: (x + y) % 2 == 0)
        self.matrix.insert_format_bitstream(self._format_bitstream)

    def __str__(self) -> str:
        return str(self.matrix)

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
        ecc_bitstream: Bitstream = Bitstream(56)

        for ecc_byte in ecc:
            ecc_bitstream.append(ecc_byte, 8)

        return ecc_bitstream

    def _generate_format_bitstream(self) -> Bitstream:
        format_bitstream: Bitstream = Bitstream(15)
        format_bitstream.append(1, 2) # low ecc level
        format_bitstream.append(0, 3) # first mask

        format_generator: list[int] = [1, 0, 1, 0, 0, 1, 1, 0, 1, 1, 1]
        ecc: list[int] = self._P.mod(format_bitstream.bits + [0] * 10, format_generator)

        format_bitstream.bits += ecc

        format_mask: list[int] = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]
        format_bitstream.bits = [x ^ y for x, y in zip(format_bitstream.bits, format_mask)]

        return format_bitstream

class QRMatrix:
    def __init__(self, size: int) -> None:
        self.size: int = size
        self.matrix: list[list[int]] = [[0] * size for _ in range(size)]
        self.data_bit_matrix: list[list[bool]] = [[True] * size for _ in range(size)]

        self.draw_square(0, (0, 0), (8, 8))
        self.draw_square(0, (size - 8, 0), (size - 1, 8))
        self.draw_square(0, (0, size - 8), (8, size - 1))

        self.draw_finder_pattern((0, 0))
        self.draw_finder_pattern((0, size - 7))
        self.draw_finder_pattern((size - 7, 0))

        for i in range(8, size - 8):
            if i % 2 == 0:
                self.matrix[i][6] = 1
                self.matrix[6][i] = 1
            self.data_bit_matrix[i][6] = False
            self.data_bit_matrix[6][i] = False

    def __str__(self) -> str:
        string = ""
        for row in self.matrix:
            for module in row:
                string += "██" if module == 1 else "  "
            string += "\n"
        return string

    def draw_square(self, value: int, top_left: tuple[int, int], bottom_right: tuple[int, int]) -> None:
        for y in range(top_left[1], bottom_right[1] + 1):
            for x in range(top_left[0], bottom_right[0] + 1):
                self.matrix[y][x] = value
                self.data_bit_matrix[y][x] = False

    def draw_finder_pattern(self, top_left: tuple[int, int]) -> None:
        self.draw_square(1, top_left, (top_left[0] + 6, top_left[1] + 6))
        self.draw_square(0, (top_left[0] + 1, top_left[1] + 1), (top_left[0] + 5, top_left[1] + 5))
        self.draw_square(1, (top_left[0] + 2, top_left[1] + 2), (top_left[0] + 4, top_left[1] + 4))

    def insert_message_bitstream(self, data: Bitstream) -> None:
        data_it: Iterator[int] = iter(data)

        for left_x in list(range(self.size - 2, 6, -2)) + list(range(4, -1, -2)):
            if (left_x // 2) % 2 == 0:
                y_range: range = range(0, self.size)
            else:
                y_range: range = range(self.size - 1, -1, -1)

            for y in y_range:
                for x in range(left_x + 1, left_x - 1, -1):
                    if not self.data_bit_matrix[y][x]:
                        continue

                    self.matrix[y][x] = next(data_it, 0)

    def apply_mask(self, mask: Callable[[int, int], bool]) -> None:
        for y in range(self.size):
            for x in range(self.size):
                if not self.data_bit_matrix[y][x]:
                    continue

                if mask(x, y):
                    self.matrix[y][x] ^= 1

    def insert_format_bitstream(self, format: Bitstream) -> None:
        self.matrix[self.size - 8][8] = 1

        format_it: Iterator[int] = reversed(format)
        for y in list(range(0, 6)) + list(range(7, 9)) + list(range(self.size - 7, self.size)):
            self.matrix[y][8] = next(format_it)

        format_re: Iterator[int] = iter(format)
        for x in list(range(0, 6)) + [7] + list(range(self.size - 8, self.size)):
            self.matrix[8][x] = next(format_re)

qr = QR("GOOGLE.COM")
print(qr)
