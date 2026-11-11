# Exact register computations and trace replay

`run_register_program(program, inputs, max_steps=100000, trace=False)` executes a
specified natural-number register program. Inputs and register values are canonical
decimal strings; arithmetic is exact. Program fields are `id`, `version`,
`register_count`, `inputs` (register indices), `output`, `entry` and `instructions`.
Register and instruction indices are zero-based.

Instructions are CONST, COPY, ADD, MUL, SUB, DIVMOD, JEQ, JLT, JUMP and HALT. SUB
saturates at zero. DIVMOD by zero returns quotient zero and the numerator as
remainder. Read operands are taken before destination writes, including aliased
registers; quotient and remainder destinations must differ. Branches and instruction
continuations are explicit indices. All unused registers initially contain zero.

```python
import goedel as g

program = {
    'id': 'addition-example', 'version': '1.0', 'register_count': 2,
    'inputs': [0, 1], 'output': 0, 'entry': 0,
    'instructions': [
        {'op': 'ADD', 'dst': 0, 'left': 0, 'right': 1, 'next': 1},
        {'op': 'HALT'},
    ],
}
answer = g.run_register_program(program, ['17', '25'], max_steps=1, trace=True)
assert answer['details']['output'] == '42'
assert g.check_register_trace(program, ['17', '25'], answer['witness'])['status'] == 'ESTABLISHED'
```

HALT costs no transition. Reaching it after exactly the allowed transitions still
succeeds. `UNKNOWN` means that the finite budget ended before HALT; it is not a
nontermination result. Trace replay independently checks the initial state, every
local arithmetic transition, control flow and every unchanged register. A valid
finite prefix can be established while its separate `halted` field remains false.
A mutated transition is `REFUTED`, which refutes that submitted trace only.

Limits are 4096 registers, 100000 instructions, at most 1000000 executed transitions,
16000000 bits per register, and 10000 trace states. Program SHA-256 covers canonical
JSON. No dynamic code evaluation, network requests or external executables are used.
A successful execution or replay does not prove arithmetical representability;
that requires the separate, exact program-to-formula correspondence review.
