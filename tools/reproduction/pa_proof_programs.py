"""Explicit finite Hilbert-PA verifier, compiled with arithmetization_programs.

Natural-number source only: no oracle, library lookup, semantic decision or
resource cutoff. All formula comparisons use exact definitional expansion of
NUM/and/or/exists/bottom, then literal syntax (including binder indices).
The proof schema and mathematical correspondence are documented separately.
"""


def pa_nth(sequence, offset):
    count = 0
    rest = sequence
    value = 0
    while count <= offset:
        value, rest, valid = pop(rest)
        if valid == 0:
            return 0
        count = count + 1
    return value


def pa_append(reversed_cells, count, tag, label, left, right):
    result = push(tag, reversed_cells)
    result = push(label, result)
    result = push(left, result)
    result = push(right, result)
    return result, count + 1


def pa_finish(reversed_cells, count):
    result = 1
    rest = reversed_cells
    while rest > 1:
        value, rest, valid = pop(rest)
        result = push(value, result)
    result = push(count, result)
    result = push(1, result)
    result = push(20261105, result)
    return result


def pa_count(code):
    return pa_nth(code, 2)


def pa_at(code, index):
    rest = code
    skip = 4 * index - 1
    cursor = 0
    while cursor < skip:
        value, rest, valid = pop(rest)
        cursor = cursor + 1
    tag, rest, valid = pop(rest)
    label, rest, valid = pop(rest)
    left, rest, valid = pop(rest)
    right, rest, valid = pop(rest)
    return tag, label, left, right


def pa_normalize(code):
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
    types = 0
    place = 1
    index = 1
    mapping = 1
    output = 1
    output_count = 0
    result = 0
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
        a = 0
        b = 0
        if left > 0:
            a = pa_nth(mapping, index - left - 1)
        if right > 0:
            b = pa_nth(mapping, index - right - 1)
        if tag == 0:
            output, output_count = pa_append(output, output_count, 2, 0, 0, 0)
            zero = output_count
            result = zero
            if label > 0:
                output, output_count = pa_append(output, output_count, 3, 0, zero, 0)
                one = output_count
                result = one
                output, output_count = pa_append(output, output_count, 3, 0, one, 0)
                two = output_count
                bits = 1
                remaining = label
                while remaining > 1:
                    bits = push(remaining % 2, bits)
                    remaining = remaining // 2
                while bits > 1:
                    bit, bits, valid = pop(bits)
                    output, output_count = pa_append(output, output_count, 5, 0, two, result)
                    result = output_count
                    if bit == 1:
                        output, output_count = pa_append(output, output_count, 3, 0, result, 0)
                        result = output_count
        elif tag == 8:
            output, output_count = pa_append(output, output_count, 7, 0, b, 0)
            output, output_count = pa_append(output, output_count, 10, 0, a, output_count)
            output, output_count = pa_append(output, output_count, 7, 0, output_count, 0)
            result = output_count
        elif tag == 9:
            output, output_count = pa_append(output, output_count, 7, 0, a, 0)
            output, output_count = pa_append(output, output_count, 10, 0, output_count, b)
            result = output_count
        elif tag == 12:
            output, output_count = pa_append(output, output_count, 7, 0, a, 0)
            output, output_count = pa_append(output, output_count, 11, label, output_count, 0)
            output, output_count = pa_append(output, output_count, 7, 0, output_count, 0)
            result = output_count
        elif tag == 13:
            output, output_count = pa_append(output, output_count, 2, 0, 0, 0)
            output, output_count = pa_append(output, output_count, 6, 0, output_count, output_count)
            output, output_count = pa_append(output, output_count, 7, 0, output_count, 0)
            result = output_count
        else:
            output, output_count = pa_append(output, output_count, tag, label, a, b)
            result = output_count
        mapping = push(result, mapping)
        index = index + 1
    if rest != 1:
        return 0
    # NUM(1) leaves an unused literal-two node; preserve the desired root by a
    # final copy, so the final record always denotes the original final root.
    normalized = pa_finish(output, output_count)
    if result != output_count:
        tag, label, left, right = pa_at(normalized, result)
        output, output_count = pa_append(output, output_count, tag, label, left, right)
        normalized = pa_finish(output, output_count)
    return normalized


def pa_same(code_a, index_a, code_b, index_b):
    stack = push(index_a, 1)
    stack = push(index_b, stack)
    while stack > 1:
        b, stack, valid = pop(stack)
        a, stack, valid = pop(stack)
        at, an, al, ar = pa_at(code_a, a)
        bt, bn, bl, br = pa_at(code_b, b)
        if at != bt:
            return 0
        if an != bn:
            return 0
        if al == 0:
            if bl != 0:
                return 0
        else:
            if bl == 0:
                return 0
            stack = push(al, stack)
            stack = push(bl, stack)
        if ar == 0:
            if br != 0:
                return 0
        else:
            if br == 0:
                return 0
            stack = push(ar, stack)
            stack = push(br, stack)
    return 1


def pa_free(code, root, variable):
    stack = push(root, 1)
    while stack > 1:
        index, stack, valid = pop(stack)
        tag, label, left, right = pa_at(code, index)
        if tag == 1:
            if label == variable:
                return 1
        stop = 0
        if tag == 11:
            if label == variable:
                stop = 1
        if stop == 0:
            if left > 0:
                stack = push(left, stack)
            if right > 0:
                stack = push(right, stack)
    return 0


def pa_free_for(code, root, variable, term, term_root):
    stack = push(root, 1)
    while stack > 1:
        index, stack, valid = pop(stack)
        tag, label, left, right = pa_at(code, index)
        stop = 0
        if tag == 11:
            if label == variable:
                stop = 1
            else:
                if pa_free(term, term_root, label) == 1:
                    if pa_free(code, left, variable) == 1:
                        return 0
        if stop == 0:
            if left > 0:
                stack = push(left, stack)
            if right > 0:
                stack = push(right, stack)
    return 1


def pa_sub_equal(code_a, root_a, variable, term, term_root, code_b, root_b):
    stack = push(root_a, 1)
    stack = push(root_b, stack)
    stack = push(0, stack)
    while stack > 1:
        blocked, stack, valid = pop(stack)
        b, stack, valid = pop(stack)
        a, stack, valid = pop(stack)
        at, an, al, ar = pa_at(code_a, a)
        bt, bn, bl, br = pa_at(code_b, b)
        replace = 0
        if blocked == 0:
            if at == 1:
                if an == variable:
                    replace = 1
        if replace == 1:
            if pa_same(term, term_root, code_b, b) == 0:
                return 0
        else:
            if at != bt:
                return 0
            if an != bn:
                return 0
            if at == 11:
                if an == variable:
                    blocked = 1
            if al > 0:
                stack = push(al, stack)
                stack = push(bl, stack)
                stack = push(blocked, stack)
            if ar > 0:
                stack = push(ar, stack)
                stack = push(br, stack)
                stack = push(blocked, stack)
    return 1


def pa_match(code, root, pattern):
    stack = push(root, 1)
    stack = push(pa_count(pattern), stack)
    bound_a = 0
    bound_b = 0
    bound_c = 0
    while stack > 1:
        p, stack, valid = pop(stack)
        a, stack, valid = pop(stack)
        pt, pn, pl, pr = pa_at(pattern, p)
        at, an, al, ar = pa_at(code, a)
        if pt == 14:
            previous = 0
            if pn == 0:
                previous = bound_a
                bound_a = a
            elif pn == 1:
                previous = bound_b
                bound_b = a
            else:
                previous = bound_c
                bound_c = a
            if at < 6:
                return 0
            if previous > 0:
                if pa_same(code, previous, code, a) == 0:
                    return 0
        else:
            if pt != at:
                return 0
            if pn != an:
                return 0
            if pl > 0:
                stack = push(al, stack)
                stack = push(pl, stack)
            if pr > 0:
                stack = push(ar, stack)
                stack = push(pr, stack)
    return 1


def pa_pattern(rule):
    if rule == 1:
        return 378616845355062729729899599167492194303
    if rule == 2:
        return 32741774232736430485401931319481080176880767608330622346316049169776639
    if rule == 3:
        return 733237681293678483974069578686983563436726181116218703871
    if rule == 11:
        return 500916525028717704190487132685665064192049151
    if rule == 12:
        return 34128533460435954929216433013749539833340190205358723760417406975
    if rule == 13:
        return 659269241530276489251887774916317243209608597141772127334720066388438037764767743
    if rule == 14:
        return 7303094192337005764632264550179605053439
    if rule == 15:
        return 2133033341277245731431407528563156690439727583356260119625072639
    if rule == 16:
        return 7303104576930742177100635445239058792447
    if rule == 17:
        return 8532133365108982925472268923064903045895990360676493062035210239
    return 0


def pa_axiom(code, rule, aux_a, aux_b):
    root = pa_count(code)
    if rule <= 3:
        if rule == 0:
            return 0
        if aux_a != 0:
            return 0
        if aux_b != 0:
            return 0
        return pa_match(code, root, pa_pattern(rule))
    if rule >= 11:
        if rule > 17:
            return 0
        if aux_a != 0:
            return 0
        if aux_b != 0:
            return 0
        pattern = pa_pattern(rule)
        return pa_same(code, root, pattern, pa_count(pattern))
    tag, label, left, right = pa_at(code, root)
    if rule == 6:
        if aux_a != 0:
            return 0
        if aux_b != 0:
            return 0
        if tag != 6:
            return 0
        return pa_same(code, left, code, right)
    if tag != 10:
        return 0
    lt, ln, ll, lr = pa_at(code, left)
    rt, rn, rl, rr = pa_at(code, right)
    if rule == 4:
        if aux_b != 0:
            return 0
        if lt != 11:
            return 0
        term = pa_normalize(aux_a)
        if term == 0:
            return 0
        term_root = pa_count(term)
        tt, tn, tl, tr = pa_at(term, term_root)
        if tt >= 6:
            return 0
        if pa_free_for(code, ll, ln, term, term_root) == 0:
            return 0
        return pa_sub_equal(code, ll, ln, term, term_root, code, right)
    if rule == 5:
        if aux_a != 0:
            return 0
        if aux_b != 0:
            return 0
        if lt != 11:
            return 0
        if rt != 10:
            return 0
        it, inn, il, ir = pa_at(code, ll)
        bt, bn, bl, br = pa_at(code, rr)
        if it != 10:
            return 0
        if bt != 11:
            return 0
        if ln != bn:
            return 0
        if pa_free(code, il, ln) != 0:
            return 0
        if pa_same(code, il, code, rl) == 0:
            return 0
        return pa_same(code, ir, code, bl)
    if rule == 7:
        if lt != 6:
            return 0
        if rt != 10:
            return 0
        formula = pa_normalize(aux_a)
        if formula == 0:
            return 0
        fr = pa_count(formula)
        ft, fn, fl, frr = pa_at(formula, fr)
        if ft < 6:
            return 0
        if pa_free_for(formula, fr, aux_b, code, ll) == 0:
            return 0
        if pa_free_for(formula, fr, aux_b, code, lr) == 0:
            return 0
        if pa_sub_equal(formula, fr, aux_b, code, ll, code, rl) == 0:
            return 0
        return pa_sub_equal(formula, fr, aux_b, code, lr, code, rr)
    if rule == 8:
        if aux_a != 0:
            return 0
        if aux_b != 0:
            return 0
        if rt != 11:
            return 0
        if lt != 7:
            return 0
        at, an, al, ar = pa_at(code, ll)
        if at != 10:
            return 0
        nt, nn, nl, nr = pa_at(code, ar)
        if nt != 7:
            return 0
        st, sn, sl, sr = pa_at(code, nl)
        if st != 11:
            return 0
        if sn != rn:
            return 0
        it, inn, il, ir = pa_at(code, sl)
        if it != 10:
            return 0
        if pa_same(code, rl, code, il) == 0:
            return 0
        reversed_cells, n = pa_append(1, 0, 2, 0, 0, 0)
        zero = pa_finish(reversed_cells, n)
        if pa_sub_equal(code, rl, rn, zero, 1, code, al) == 0:
            return 0
        reversed_cells, n = pa_append(1, 0, 1, rn, 0, 0)
        reversed_cells, n = pa_append(reversed_cells, n, 3, 0, 1, 0)
        successor = pa_finish(reversed_cells, n)
        if pa_free_for(code, rl, rn, successor, 2) == 0:
            return 0
        return pa_sub_equal(code, rl, rn, successor, 2, code, ir)
    return 0


def check_pa_proof(proof, conclusion):
    target = pa_normalize(conclusion)
    if target == 0:
        return 0
    target_root = pa_count(target)
    tt, tn, tl, tr = pa_at(target, target_root)
    if tt < 6:
        return 0
    magic, rest, valid = pop(proof)
    if valid == 0:
        return 0
    if magic != 20261106:
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
    previous = 1
    index = 1
    formula = 0
    root = 0
    while index <= count:
        rule, rest, valid = pop(rest)
        if valid == 0:
            return 0
        formula_code, rest, valid = pop(rest)
        if valid == 0:
            return 0
        aux_a, rest, valid = pop(rest)
        if valid == 0:
            return 0
        aux_b, rest, valid = pop(rest)
        if valid == 0:
            return 0
        aux_c, rest, valid = pop(rest)
        if valid == 0:
            return 0
        aux_d, rest, valid = pop(rest)
        if valid == 0:
            return 0
        if aux_c != 0:
            return 0
        if aux_d != 0:
            return 0
        formula = pa_normalize(formula_code)
        if formula == 0:
            return 0
        root = pa_count(formula)
        tag, label, left, right = pa_at(formula, root)
        if tag < 6:
            return 0
        accepted = 0
        if rule == 20:
            if aux_a == 0:
                return 0
            if aux_b == 0:
                return 0
            if aux_a >= index:
                return 0
            if aux_b >= index:
                return 0
            antecedent = pa_nth(previous, index - aux_a - 1)
            implication = pa_nth(previous, index - aux_b - 1)
            it, inn, il, ir = pa_at(implication, pa_count(implication))
            if it != 10:
                return 0
            if pa_same(antecedent, pa_count(antecedent), implication, il) == 0:
                return 0
            accepted = pa_same(formula, root, implication, ir)
        elif rule == 21:
            if aux_a == 0:
                return 0
            if aux_a >= index:
                return 0
            if tag != 11:
                return 0
            if label != aux_b:
                return 0
            premise = pa_nth(previous, index - aux_a - 1)
            accepted = pa_same(formula, left, premise, pa_count(premise))
        else:
            accepted = pa_axiom(formula, rule, aux_a, aux_b)
        if accepted == 0:
            return 0
        previous = push(formula, previous)
        index = index + 1
    if rest != 1:
        return 0
    return pa_same(formula, root, target, target_root)
