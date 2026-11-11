"""Concrete natural-number algorithms compiled to the arithmetic register IR.

Every helper is expanded by compile_register.py. There is no Python/library
oracle in the resulting machine. Subtraction is used only where nonnegative;
the register IR totalizes it as saturating subtraction. Invalid codes return 0.
The mathematical programs have no API resource cutoffs.
"""


def power_two(exponent):
    value = 1
    count = 0
    while count < exponent:
        value = value * 2
        count = count + 1
    return value


def push(value, sequence):
    v = value + 1
    power = 1
    remaining = v
    while remaining > 1:
        remaining = remaining // 2
        power = power * 2
    width = power * 2
    block = width - 1 + width * 2 * (v - power)
    return width * width * sequence + block


def pop(sequence):
    if sequence <= 1:
        return 0, 0, 0
    power = 1
    rest = sequence
    while rest % 2 == 1:
        rest = rest // 2
        power = power * 2
    if power == 1:
        return 0, 0, 0
    rest = rest // 2
    half = power // 2
    value = half + rest % half - 1
    tail = rest // half
    if tail == 0:
        return 0, 0, 0
    return value, tail, 1


def child_sort(child, index, types):
    if child == 0:
        return 0
    if child >= index:
        return 0
    place = power_two(child - 1)
    return 1 + (types // place) % 2


def record_sort(tag, label, left, right, index, types):
    if tag > 13:
        return 0
    if tag == 0:
        if left != 0:
            return 0
        if right != 0:
            return 0
        return 2
    if tag == 1:
        if left != 0:
            return 0
        if right != 0:
            return 0
        return 2
    if tag == 11:
        if right != 0:
            return 0
        if child_sort(left, index, types) != 1:
            return 0
        return 1
    if tag == 12:
        if right != 0:
            return 0
        if child_sort(left, index, types) != 1:
            return 0
        return 1
    if label != 0:
        return 0
    if tag == 2:
        if left != 0:
            return 0
        if right != 0:
            return 0
        return 2
    if tag == 13:
        if left != 0:
            return 0
        if right != 0:
            return 0
        return 1
    if tag == 3:
        if right != 0:
            return 0
        if child_sort(left, index, types) != 2:
            return 0
        return 2
    if tag == 7:
        if right != 0:
            return 0
        if child_sort(left, index, types) != 1:
            return 0
        return 1
    if tag < 7:
        if child_sort(left, index, types) != 2:
            return 0
        if child_sort(right, index, types) != 2:
            return 0
        if tag == 6:
            return 1
        return 2
    if child_sort(left, index, types) != 1:
        return 0
    if child_sort(right, index, types) != 1:
        return 0
    return 1


def substitute_closed(code, variable, value):
    magic, rest, valid = pop(code)
    if valid == 0:
        return 0
    if magic != 20261105:
        return 0
    version, rest, valid = pop(rest)
    if valid == 0:
        return 0
    if version != 1:
        return 0
    count, rest, valid = pop(rest)
    if valid == 0:
        return 0
    if count == 0:
        return 0
    originals = 1
    transformed = 1
    types = 0
    place = 1
    index = 1
    while index <= count:
        tag, rest, valid = pop(rest)
        if valid == 0:
            return 0
        label, rest, valid = pop(rest)
        if valid == 0:
            return 0
        left, rest, valid = pop(rest)
        if valid == 0:
            return 0
        right, rest, valid = pop(rest)
        if valid == 0:
            return 0
        kind = record_sort(tag, label, left, right, index, types)
        if kind == 0:
            return 0
        types = types + (kind - 1) * place
        place = place * 2
        originals = push(tag, originals)
        originals = push(label, originals)
        originals = push(left, originals)
        originals = push(right, originals)
        new_tag = tag
        new_label = label
        new_left = left
        new_right = right
        stopped = 0
        if tag == 1:
            if label == variable:
                new_tag = 0
                new_label = value
        if tag == 11:
            if label == variable:
                stopped = 1
        if tag == 12:
            if label == variable:
                stopped = 1
        if stopped == 0:
            if left > 0:
                new_left = left + count
            if right > 0:
                new_right = right + count
        transformed = push(new_tag, transformed)
        transformed = push(new_label, transformed)
        transformed = push(new_left, transformed)
        transformed = push(new_right, transformed)
        index = index + 1
    if rest != 1:
        return 0
    output = 1
    while transformed > 1:
        cell, transformed, valid = pop(transformed)
        output = push(cell, output)
    while originals > 1:
        cell, originals, valid = pop(originals)
        output = push(cell, output)
    output = push(count * 2, output)
    output = push(1, output)
    output = push(20261105, output)
    return output
