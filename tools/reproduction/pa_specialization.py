"""Explicit proof specialization for the auxiliary unary/core HBL argument.

Compile after arithmetization_programs.py, pa_proof_programs.py and
pa_transformations.py. The productive numeral convention remains binary Horner.
These mathematical transformers have no API size limit and claim proof validity
only under the stated valid-input proof premises.
"""


def pa_copy_records(code, offset, reversed_cells, output_count):
    count = pa_count(code)
    index = 1
    result = reversed_cells
    n = output_count
    while index <= count:
        tag, label, left, right = pa_at(code, index)
        if left > 0:
            left = left + offset
        if right > 0:
            right = right + offset
        result, n = pa_append(result, n, tag, label, left, right)
        index = index + 1
    return result, n


def pa_unary_term(value):
    result, count = pa_append(1, 0, 2, 0, 0, 0)
    index = 0
    while index < value:
        result, count = pa_append(result, count, 3, 0, count, 0)
        index = index + 1
    return pa_finish(result, count)


def pa_core_canonical(code):
    normalized = pa_normalize(code)
    if normalized == 0:
        return 0
    stack = push(pa_count(normalized), 1)
    stack = push(0, stack)
    values = 1
    output = 1
    count = 0
    while stack > 1:
        phase, stack, valid = pop(stack)
        index, stack, valid = pop(stack)
        tag, label, left, right = pa_at(normalized, index)
        if phase == 0:
            stack = push(index, stack)
            stack = push(1, stack)
            if right > 0:
                stack = push(right, stack)
                stack = push(0, stack)
            if left > 0:
                stack = push(left, stack)
                stack = push(0, stack)
        else:
            new_left = 0
            new_right = 0
            if right > 0:
                new_right, values, valid = pop(values)
            if left > 0:
                new_left, values, valid = pop(values)
            output, count = pa_append(output, count, tag, label, new_left, new_right)
            values = push(count, values)
    return pa_finish(output, count)


def pa_is_closed_term(code):
    root = pa_count(code)
    tag, label, left, right = pa_at(code, root)
    if tag >= 6:
        return 0
    stack = push(root, 1)
    while stack > 1:
        index, stack, valid = pop(stack)
        tag, label, left, right = pa_at(code, index)
        if tag == 1:
            return 0
        if left > 0:
            stack = push(left, stack)
        if right > 0:
            stack = push(right, stack)
    return 1


def pa_extract_root(code, root):
    output, count = pa_copy_records(code, 0, 1, 0)
    tag, label, left, right = pa_at(code, root)
    output, count = pa_append(output, count, tag, label, left, right)
    return pa_finish(output, count)


def pa_closed_term_substitute(code, variable, term):
    original = pa_normalize(code)
    normalized_term = pa_normalize(term)
    if original == 0:
        return 0
    if normalized_term == 0:
        return 0
    if pa_is_closed_term(normalized_term) == 0:
        return 0
    original_count = pa_count(original)
    term_count = pa_count(normalized_term)
    output, count = pa_copy_records(original, 0, 1, 0)
    output, count = pa_copy_records(normalized_term, original_count, output, count)
    shift = original_count + term_count
    tt, tn, tl, tr = pa_at(normalized_term, term_count)
    if tl > 0:
        tl = tl + original_count
    if tr > 0:
        tr = tr + original_count
    index = 1
    while index <= original_count:
        tag, label, left, right = pa_at(original, index)
        replace = 0
        if tag == 1:
            if label == variable:
                replace = 1
        if replace == 1:
            tag = tt
            label = tn
            left = tl
            right = tr
        else:
            stopped = 0
            if tag == 11:
                if label == variable:
                    stopped = 1
            if stopped == 0:
                if left > 0:
                    left = left + shift
                if right > 0:
                    right = right + shift
        output, count = pa_append(output, count, tag, label, left, right)
        index = index + 1
    return pa_finish(output, count)


def pa_implication_code(left_code, right_code):
    a = pa_normalize(left_code)
    b = pa_normalize(right_code)
    if a == 0:
        return 0
    if b == 0:
        return 0
    na = pa_count(a)
    nb = pa_count(b)
    at, an, al, ar = pa_at(a, na)
    bt, bn, bl, br = pa_at(b, nb)
    if at < 6:
        return 0
    if bt < 6:
        return 0
    output, count = pa_copy_records(a, 0, 1, 0)
    output, count = pa_copy_records(b, na, output, count)
    output, count = pa_append(output, count, 10, 0, na, na + nb)
    return pa_finish(output, count)


def pa_forall_instance(universal, term):
    formula = pa_normalize(universal)
    if formula == 0:
        return 0
    tag, variable, body, unused = pa_at(formula, pa_count(formula))
    if tag != 11:
        return 0
    body_code = pa_extract_root(formula, body)
    result = pa_closed_term_substitute(body_code, variable, term)
    if result == 0:
        return 0
    return pa_core_canonical(result)


def specialize_pa_forall(proof, universal, term):
    count, rows = proof_rows(proof)
    if count == 0:
        return 0
    instance = pa_forall_instance(universal, term)
    if instance == 0:
        return 0
    elimination_axiom = pa_implication_code(universal, instance)
    reversed_rows = 1
    while rows > 1:
        cell, rows, valid = pop(rows)
        reversed_rows = push(cell, reversed_rows)
    reversed_rows = push(4, reversed_rows)
    reversed_rows = push(elimination_axiom, reversed_rows)
    reversed_rows = push(term, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(20, reversed_rows)
    reversed_rows = push(instance, reversed_rows)
    reversed_rows = push(count, reversed_rows)
    reversed_rows = push(count + 1, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    result = 1
    while reversed_rows > 1:
        cell, reversed_rows, valid = pop(reversed_rows)
        result = push(cell, result)
    result = push(count + 2, result)
    result = push(1, result)
    result = push(20261106, result)
    return result


def specialize_pa_unary(proof, universal, value):
    return specialize_pa_forall(proof, universal, pa_unary_term(value))


def generalize_pa(proof, conclusion, variable):
    count, rows = proof_rows(proof)
    if count == 0:
        return 0
    formula = pa_normalize(conclusion)
    if formula == 0:
        return 0
    root = pa_count(formula)
    tag, label, left, right = pa_at(formula, root)
    if tag < 6:
        return 0
    output, n = pa_copy_records(formula, 0, 1, 0)
    output, n = pa_append(output, n, 11, variable, root, 0)
    universal = pa_finish(output, n)
    reversed_rows = 1
    while rows > 1:
        cell, rows, valid = pop(rows)
        reversed_rows = push(cell, reversed_rows)
    reversed_rows = push(21, reversed_rows)
    reversed_rows = push(universal, reversed_rows)
    reversed_rows = push(count, reversed_rows)
    reversed_rows = push(variable, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    reversed_rows = push(0, reversed_rows)
    result = 1
    while reversed_rows > 1:
        cell, reversed_rows, valid = pop(reversed_rows)
        result = push(cell, result)
    result = push(count + 1, result)
    result = push(1, result)
    result = push(20261106, result)
    return result
