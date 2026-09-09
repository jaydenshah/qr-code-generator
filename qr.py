from enum import Enum
import math

from gf256 import GF256
from polynomial import Polynomial

class Mode(Enum):
    NUMERIC = 1
    ALPHANUMERIC = 2
    BYTE = 4
    KANJI = 8

class QR:
    _VALID_CHARACTERS: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"

    def __init__(self, data: str = "", ecc: str = 'L', version: int = -1) -> None:
        self.data: str = data

        self.ecc: str = ecc
        if ecc != 'L':
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

        self._encode_data()

    def _determine_mode(self) -> Mode:
        for char in self.data:
            if char not in QR._VALID_CHARACTERS:
                raise NotImplementedError("Haven't implemented other modes yet")
            
        return Mode.ALPHANUMERIC

    def _determine_minimum_version(self) -> int:
        if 13 + 11 * (len(self.data) // 2) + 6 * (len(self.data) % 2) > 152:
            raise NotImplementedError("Size of data requires a QR code version that isn't implemented yet")

        return 1

    def _generate_data_bytes(self) -> list[int]:
        data_bytes: list[int] = [0] * 19
        data_bitstream_length: int = 13 + 11 * (len(self.data) // 2) + 6 * (len(self.data) % 2)

        mode_bits: int = 2
        char_count_bits: int = (len(self.data) & ((1 << 9) - 1))
        char_bits: list[int] = [
            QR._VALID_CHARACTERS.index(self.data[i]) * 45 + QR._VALID_CHARACTERS.index(self.data[i + 1]) 
            for i in range(0, len(self.data) - 1, 2)
        ]
        if len(self.data) % 2 != 0:
            char_bits.append(QR._VALID_CHARACTERS.index(self.data[-1]))

        data_bitstream_int: int = mode_bits
        data_bitstream_int <<= 9
        data_bitstream_int |= char_count_bits
        for i in range(len(char_bits) - 1):
            data_bitstream_int <<= 11
            data_bitstream_int |= char_bits[i]

        if len(self.data) != 0:
            if len(self.data) % 2 != 0:
                data_bitstream_int <<= 6
            else:
                data_bitstream_int <<= 11
            data_bitstream_int |= char_bits[-1]

        data_bitstream_int <<= min(152 - data_bitstream_length, 4)
        data_bitstream_length += min(152 - data_bitstream_length, 4)

        data_bitstream_int <<= math.ceil(data_bitstream_length / 8) * 8 - data_bitstream_length
        data_bitstream_length = math.ceil(data_bitstream_length / 8) * 8

        use_first_pad_codeword: bool = True
        while data_bitstream_length < 152:
            data_bitstream_int <<= 8
            data_bitstream_int |= 0b11101100 if use_first_pad_codeword else 0b00010001
            data_bitstream_length += 8

            use_first_pad_codeword = not use_first_pad_codeword

        for i in range(152 // 8):
            data_bytes[18 - i] = data_bitstream_int & ((1 << 8) - 1)
            data_bitstream_int >>= 8

        return data_bytes

    def _generator_poly(self, ecc: int) -> list[int]:
        alpha_i = 1
        g_p = [1]
        for _ in range(ecc):
            g_p = self._P.multiply(g_p, [1, alpha_i])
            alpha_i = self._GF.multiply(alpha_i, self._GF.primitive_p)

        return g_p

    def _generate_ecc(self) -> list[int]:
        message_poly = self._data_bytes + [0] * 7
        generator_poly = self._generator_poly(7)

        return self._P.mod(message_poly, generator_poly)

    def _encode_data(self) -> None:
        self._data_bytes: list[int] = self._generate_data_bytes()
        self._ecc: list[int] = self._generate_ecc()
        self._sequence: list[int] = self._data_bytes + self._ecc
        

qr = QR("HELLO WORLD")




        
        
