"""Exact prefix-free coding of finite natural-number sequences.

The empty sequence is 1. The mathematical function has no machine-size bound;
explicit public limits protect the native computation only.
"""

from __future__ import annotations

import re
from typing import Any

from .syntax import _error

MAX_NAT_DIGITS = 5000000
MAX_SEQUENCE_BITS = 16000000
MAX_SEQUENCE_ITEMS = 1000000


def _natural_text(text: Any, max_digits: int = MAX_NAT_DIGITS) -> None:
    """Validate canonical decimal syntax without constructing an unused big integer."""
    if not isinstance(text, str) or re.fullmatch(r"0|[1-9][0-9]*", text) is None:
        _error("Expected canonical nonnegative decimal text")
    if len(text) > max_digits:
        _error("Natural-number digit budget exceeded", "RESOURCE_LIMIT")


def _nat(text: Any, max_digits: int = MAX_NAT_DIGITS) -> int:
    _natural_text(text, max_digits)
    powers: dict[int, int] = {}

    def parse(part: str) -> int:
        if len(part) <= 512:
            return int(part)
        middle = len(part) // 2
        width = len(part) - middle
        if width not in powers:
            powers[width] = 10**width
        return parse(part[:middle]) * powers[width] + parse(part[middle:])

    return parse(text)


def _decimal(number: int) -> str:
    powers: dict[int, int] = {}

    def render(value: int) -> str:
        if value.bit_length() <= 1600:
            return str(value)
        # A lower approximation is sufficient: the split only needs to be near
        # the middle, and zfill restores the exact lower-place width.
        width = max(1, ((value.bit_length() * 1233) // 4096) // 2)
        if width not in powers:
            powers[width] = 10**width
        high, low = divmod(value, powers[width])
        return render(high) + render(low).zfill(width)

    result = render(number)
    if len(result) > MAX_NAT_DIGITS:
        _error("Natural-number digit budget exceeded", "RESOURCE_LIMIT")
    return result


def _limits(max_items: int, max_bits: int) -> None:
    if type(max_items) is not int or not 0 <= max_items <= MAX_SEQUENCE_ITEMS:
        _error("max_items must be an integer from 0 to 1000000")
    if type(max_bits) is not int or not 1 <= max_bits <= MAX_SEQUENCE_BITS:
        _error("max_bits must be an integer from 1 to 16000000")


def sequence_encode(
    values: list[str], max_items: int = MAX_SEQUENCE_ITEMS, max_bits: int = MAX_SEQUENCE_BITS
) -> str:
    """Encode a sequence of canonical natural decimal strings injectively.

    For v=a+1 and k=bit_length(v), the low 2k-bit cell is
    (2**k-1)+2**(k+1)*(v-2**(k-1)). The remaining sequence follows above it.
    """
    _limits(max_items, max_bits)
    if not isinstance(values, (list, tuple)):
        _error("A finite sequence is required")
    if len(values) > max_items:
        _error("Sequence item budget exceeded", "RESOURCE_LIMIT")
    cells = []
    bits = 1
    for text in values:
        value = _nat(text) + 1
        width = value.bit_length()
        bits += 2 * width
        if bits > max_bits:
            _error("Sequence bit budget exceeded", "RESOURCE_LIMIT")
        block = (1 << width) - 1 + ((value - (1 << (width - 1))) << (width + 1))
        cells.append(format(block, f"0{2 * width}b"))
    return _decimal(int("1" + "".join(reversed(cells)), 2))


def sequence_decode(
    code: str, max_items: int = MAX_SEQUENCE_ITEMS, max_bits: int = MAX_SEQUENCE_BITS
) -> list[str]:
    """Invert sequence_encode; malformed cells and an absent sentinel are errors."""
    _limits(max_items, max_bits)
    number = _nat(code)
    if number.bit_length() > max_bits:
        _error("Sequence bit budget exceeded", "RESOURCE_LIMIT")
    if number == 0:
        _error("Zero has no sequence sentinel")
    bits = bin(number)[2:]
    position = len(bits) - 1
    result = []
    while position > 0:
        if len(result) == max_items:
            _error("Sequence item budget exceeded", "RESOURCE_LIMIT")
        width = 0
        while position >= 0 and bits[position] == "1":
            width += 1
            position -= 1
        if width == 0 or position < width:
            _error("Malformed sequence cell or missing sentinel")
        position -= 1  # zero delimiter
        payload = int(bits[position - width + 2 : position + 1], 2) if width > 1 else 0
        position -= width - 1
        result.append(_decimal((1 << (width - 1)) + payload - 1))
    if position != 0 or bits[0] != "1":
        _error("Missing sequence sentinel")
    return result
