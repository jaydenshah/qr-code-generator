class GF256:
    def __init__(self, reducing_p: int, generating_p: int) -> None:
        self.reducing_p: int = reducing_p
        self.generating_p: int = generating_p
        self._ANTILOG: list[int] = [0] * 256
        self._LOG: list[int] = [0] * 256
        self._populate_generator_tables()

    # https://en.wikipedia.org/wiki/Finite_field_arithmetic#Rijndael's_(AES)_finite_field
    def _multiply_slow(self, x: int, y: int) -> int:
        product: int = 0
        x &= 0xff
        y &= 0xff

        for _ in range(8):
            if x == 0 or y == 0:
                break
            if y & 1:
                product ^= x
            y >>= 1
            carry: int = x & 128
            x = (x << 1) & 0xff
            if carry:
                x ^= self.reducing_p & 0xff

        return product

    def _populate_generator_tables(self) -> None:
        # x = g^i
        x: int = 1
        for i in range(255):
            self._ANTILOG[i] = x
            self._LOG[x] = i
            x = self._multiply_slow(x, self.generating_p)


    def print_polynomial(self, x: int) -> None:
        degrees: list[int] = []
        degree: int = 0
        while x != 0:
            if x & 1:
                degrees.append(degree)
            x >>= 1
            degree += 1

        if len(degrees) == 0:
            print("0")
            return

        for i, d in enumerate(reversed(degrees)):
            if d == 0:
                print("1" if i == 0 else " + 1", end="")
            elif d == 1:
                print("x" if i == 0 else " + x", end="")
            else:
                print(f"x^{d}" if i == 0 else f" + x^{d}", end="")

        print("")
        
    def add(self, x: int, y: int) -> int:
        return x ^ y

    def multiply(self, x: int, y: int) -> int:
        if x == 0 or y == 0:
            return 0
        
        sum: int = (self._LOG[x] + self._LOG[y]) % 255
        return self._ANTILOG[sum]
