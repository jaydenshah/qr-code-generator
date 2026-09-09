from enum import Enum
import math

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

        self._data_bitstream_length: int = 13 + 11 * (len(self.data) // 2) + 6 * (len(self.data) % 2)
        self._data_bitstream: bytearray = bytearray()
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

    def _encode_data(self) -> None:
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

        data_bitstream_int <<= min(152 - self._data_bitstream_length, 4)
        self._data_bitstream_length += min(152 - self._data_bitstream_length, 4)

        data_bitstream_int <<= math.ceil(self._data_bitstream_length / 8) * 8 - self._data_bitstream_length
        self._data_bitstream_length = math.ceil(self._data_bitstream_length / 8) * 8

        use_first_pad_codeword: bool = True
        while self._data_bitstream_length < 152:
            data_bitstream_int <<= 8
            data_bitstream_int |= 0b11101100 if use_first_pad_codeword else 0b00010001
            self._data_bitstream_length += 8

            use_first_pad_codeword = not use_first_pad_codeword

        print(self._data_bitstream_length)
        print(hex(data_bitstream_int))

qr = QR("HELLO WORLD")




        
        
