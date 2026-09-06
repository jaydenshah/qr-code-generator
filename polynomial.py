from gf256 import GF256
from typing import Callable, Self

class Polynomial:
    def __init__(self, add: Callable[[int, int], int], multiply: Callable[[int, int], int]) -> None:
        self.add_func: Callable[[int, int], int] = add
        self.multiply_func: Callable[[int, int], int] = multiply

    # https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-implement-multiple-constructors
    @classmethod
    def fromGaloisField(cls, gf256: GF256) -> Self:
        return cls(gf256.add, gf256.multiply)

    # Strip leading zeroes
    def _normalise(self, x: list[int]) -> list[int]:      
        i: int = 0
        while i < len(x) and x[i] == 0:
            i += 1

        return x[i:]

    def add(self, x: list[int], y: list[int]) -> list[int]:
        sum: list[int] = [0] * max(len(x), len(y))
        for i in range(-1, -len(sum) - 1, -1):
            if i >= -len(x):
                sum[i] = self.add_func(sum[i], x[i])
            if i >= -len(y):
                sum[i] = self.add_func(sum[i], y[i])
        return self._normalise(sum)

    def multiply(self, x: list[int], y: list[int]) -> list[int]:
        product: list[int] = [0] * (len(x) + len(y) - 1)
        for i, x_coeff in enumerate(x):
            for j, y_coeff in enumerate(y):
                product[i + j] = self.add_func(product[i + j], self.multiply_func(x_coeff, y_coeff))

        return self._normalise(product)

# temp code
def convert_polynomial_to_alpha_exponents(GF: GF256, x: list[int]) -> list[int | None]:
    alpha_exponents: list[int | None] = []
    for coefficient in x:
        if coefficient == 0:
            alpha_exponents.append(None)
            continue

        alpha_exponents.append(GF._LOG[coefficient])

    return alpha_exponents

GF = GF256(0x11d, 2)
P = Polynomial.fromGaloisField(GF)
