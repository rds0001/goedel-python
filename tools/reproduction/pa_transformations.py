"""Total numerical proof joining for the fixed Hilbert PA presentation.

Compile after arithmetization_programs.py. The operation is mathematical data
construction, not a claim that either input proves its intended conclusion.
The closure theorem explicitly assumes their validity and matching conclusions.
"""


def proof_rows(proof):
    magic, rest, valid = pop(proof)
    if valid == 0:
        return 0, 0
    if magic != 20261106:
        return 0, 0
    version, rest, valid = pop(rest)
    if valid == 0:
        return 0, 0
    if version != 1:
        return 0, 0
    count, rest, valid = pop(rest)
    if valid == 0:
        return 0, 0
    if count == 0:
        return 0, 0
    tail = rest
    index = 0
    while index < 6 * count:
        cell, tail, valid = pop(tail)
        if valid == 0:
            return 0, 0
        index = index + 1
    if tail != 1:
        return 0, 0
    return count, rest


def join_pa_mp(first, second, conclusion):
    count_a, rows_a = proof_rows(first)
    count_b, rows_b = proof_rows(second)
    if count_a == 0:
        return 0
    if count_b == 0:
        return 0
    reversed_rows = 1
    while rows_a > 1:
        cell, rows_a, valid = pop(rows_a)
        reversed_rows = push(cell, reversed_rows)
    row = 0
    while row < count_b:
        rule, rows_b, valid = pop(rows_b)
        formula, rows_b, valid = pop(rows_b)
        a, rows_b, valid = pop(rows_b)
        b, rows_b, valid = pop(rows_b)
        c, rows_b, valid = pop(rows_b)
        d, rows_b, valid = pop(rows_b)
        if rule == 20:
            a = a + count_a
            b = b + count_a
        if rule == 21:
            a = a + count_a
        reversed_rows = push(rule, reversed_rows)
        reversed_rows = push(formula, reversed_rows)
        reversed_rows = push(a, reversed_rows)
        reversed_rows = push(b, reversed_rows)
        reversed_rows = push(c, reversed_rows)
        reversed_rows = push(d, reversed_rows)
        row = row + 1
    reversed_rows = push(20, reversed_rows)
    reversed_rows = push(conclusion, reversed_rows)
    reversed_rows = push(count_a, reversed_rows)
    reversed_rows = push(count_a + count_b, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    result = 1
    while reversed_rows > 1:
        cell, reversed_rows, valid = pop(reversed_rows)
        result = push(cell, result)
    result = push(count_a + count_b + 1, result)
    result = push(1, result)
    result = push(20261106, result)
    return result
