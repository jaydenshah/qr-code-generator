from gf256 import GF256
from typing import Callable, Self

class Polynomial:
    def __init__(
        self, 
        add: Callable[[int, int], int],
        subtract: Callable[[int, int], int],
        multiply: Callable[[int, int], int],
        divide: Callable[[int, int], int]
    ) -> None:
        self._add_func: Callable[[int, int], int] = add
        self._subtract_func: Callable[[int, int], int] = subtract
        self._multiply_func: Callable[[int, int], int] = multiply
        self._divide_func: Callable[[int, int], int] = divide

    # https://stackoverflow.com/questions/682504/what-is-a-clean-pythonic-way-to-implement-multiple-constructors
    @classmethod
    def fromGaloisField(cls, gf256: GF256) -> Self:
        return cls(gf256.add, gf256.add, gf256.multiply, gf256.divide)

    # Strip leading zeroes
    def _normalise(self, x: list[int]) -> list[int]:      
        i: int = 0
        while i < len(x) and x[i] == 0:
            i += 1

        return x[i:]

    def _addition_alg(self, add_func: Callable[[int, int], int], x: list[int], y: list[int]) -> list[int]:
        sum: list[int] = [0] * max(len(x), len(y))
        for i in range(-1, -len(sum) - 1, -1):
            if i >= -len(x):
                sum[i] = self._add_func(sum[i], x[i])
            if i >= -len(y):
                sum[i] = add_func(sum[i], y[i])
        return self._normalise(sum)

    def _degree(self, x: list[int]) -> int:
        # degree of 0 is undefined. Letting it silently fail because this is a private method
        # only to be used in the division algorithm
        return len(x) - 1

    # https://en.wikipedia.org/wiki/Polynomial_long_division#Pseudocode
    def _division_alg(self, x: list[int], y: list[int]) -> tuple[list[int], list[int]]:
        denominator: list[int] = self._normalise(y)

        if len(denominator) == 0:
            raise ZeroDivisionError

        quotient: list[int] = []
        remainder: list[int] = self._normalise(x)

        while len(remainder) != 0 and self._degree(remainder) >= self._degree(denominator):
            tmp: list[int] = [0] * (self._degree(remainder) - self._degree(denominator) + 1)
            tmp[0] = self._divide_func(remainder[0], denominator[0])
            quotient = self.add(quotient, tmp)
            remainder = self.subtract(remainder, self.multiply(tmp, denominator))

        # quotient and remaineder should be normalised
        return (quotient, remainder)

    def add(self, x: list[int], y: list[int]) -> list[int]:
        return self._addition_alg(self._add_func, x, y)

    def subtract(self, x: list[int], y: list[int]) -> list[int]:
        return self._addition_alg(self._subtract_func, x, y)

    def multiply(self, x: list[int], y: list[int]) -> list[int]:
        product: list[int] = [0] * (len(x) + len(y) - 1)
        for i, x_coeff in enumerate(x):
            for j, y_coeff in enumerate(y):
                product[i + j] = self._add_func(product[i + j], self._multiply_func(x_coeff, y_coeff))

        return self._normalise(product)

    def divide(self, x: list[int], y: list[int]) -> list[int]:
        return self._division_alg(x, y)[0]

    def mod(self, x: list[int], y: list[int]) -> list[int]:
        return self._division_alg(x, y)[1]