# Arithmetic representation compiler, version 1.0

This is the build interface for `goedel-arithmetic-register-v1`. It constructs
actual first-order arithmetic formulas for halting computations of explicit
finite programs. It does not infer that an arbitrary program implements
substitution, recognizes PA proofs, terminates, or satisfies HBL conditions.
Those require separate program-specific mathematical correspondence reviews.

`representation_compiler.py` is a build tool. R does not invoke Python at runtime.
The two package implementations consume versioned program/formula data and
independently implement the native operations. `register_programs.json` initially
contains compiler specimens, explicitly not a substitution or PA-proof program.

## Program interface

Each program has exactly these fields:

```json
{
  "id": "program_identifier",
  "version": "1.0",
  "register_count": 3,
  "inputs": [0, 1],
  "output": 2,
  "entry": 0,
  "instructions": [
    {"op": "ADD", "dst": 2, "left": 0, "right": 1, "next": 1},
    {"op": "HALT"}
  ]
}
```

Registers and program counters are zero-based. The program counter is separate
from the numbered registers. Input registers are distinct and receive argument
values in array order. All other registers initially contain zero. Contents are
natural numbers of arbitrary mathematical size. Operands always refer to the
pre-state, including when a destination aliases an operand. Unwritten registers
retain their values. A HALT instruction has no successor. The output is the
designated register in the final state; multiple HALT locations are permitted.

| Operation | Additional fields | Transition |
|---|---|---|
| CONST | dst, value, next | Store the canonical decimal natural `value`. |
| COPY | dst, src, next | Copy the old source value. |
| ADD | dst, left, right, next | Store the sum. |
| MUL | dst, left, right, next | Store the product. |
| SUB | dst, left, right, next | Store `max(left-right,0)`. |
| DIVMOD | quotient, remainder, numerator, denominator, next | For positive divisor store Euclidean quotient/remainder; for divisor zero store quotient zero and the old numerator as remainder. Destinations must differ. |
| JEQ | left, right, then, else | Select the specified target by equality. |
| JLT | left, right, then, else | Select the specified target by strict inequality. |
| JUMP | next | Preserve all registers and jump. |
| HALT | none | Terminate; there is no transition from this state. |

Every register/target is validated. Unknown instructions or fields are rejected.
There is no host-language callback, implicit array operation, proof oracle or
substitution oracle. High-level operations must be compiled into these operations.
The current build tool limits inputs to 4096 registers and 100000 instructions
and constants to 4096 decimal digits. These are implementation resource limits,
not definitions of the mathematical computation relation. Runtime instruction,
integer-size and memory budgets must likewise remain external to that relation.

## Formula DAG interface

A formula DAG has exactly `schema_version`, `nodes` and `root`. A node's position
is its ID, and all child references point to earlier positions. Every node has
exactly `op`, `name` and `args`. Examples:

```json
{"op":"var","name":"x0","args":[]}
{"op":"eq","name":"","args":[0,1]}
{"op":"exists","name":"x2","args":[3]}
```

The expanded arithmetic DAG permits only:

- Term operations: `zero`, `var`, `succ`, `add`, `mul`.
- Formula operations: `eq`, `not`, `and`, `or`, `implies`, `exists`, `forall`.

Names occur only on variables and quantifiers and have form `x0`, `x1`, etc.,
with canonical natural index. A quantifier's single child is its body. Lexical
binding has its ordinary meaning. Shared nodes mean literal sharing of syntax;
unfolding them yields the same ordinary formula. Sharing adds no arithmetic
symbol, axiom, recursive definition, or semantic oracle. Bounds are checked
before materializing an expanded tree; an expansion can be much larger than its
DAG. The compiler reports both DAG and expanded-tree node counts.

The bounded source DAG additionally permits these explicit abbreviations:

| Operation | Contents | Exact interpretation |
|---|---|---|
| num | name is canonical decimal; args empty | The closed binary-Horner numeral below. |
| lt | args `[a,b]` | `exists d (b = a + S(d))`, with fresh d. |
| bexists | name x; args `[bound,body]` | `exists x (x < bound and body)`. |
| bforall | name x; args `[bound,body]` | `forall x (x < bound implies body)`. |

The bound must not contain its own quantified variable freely. Expansion chooses
fresh variable names beyond all existing indices. A `num` is a syntactic term
abbreviation, never an uninterpreted number constant:

    nu(0) = 0
    nu(1) = S(0)
    nu(2k) = 2 * nu(k), for k > 0
    nu(2k+1) = S(2 * nu(k)), for k > 0, where 2 = S(S(0)).

The builder uses this exact recurrence. Each recursive argument appears once,
so the expanded term has size proportional to the number of binary digits.
Decimal parsing/conversion does not change Python's process-wide integer limits.

## Beta trace construction

For a program with R registers, let K=R+1. A state row is
`[pc,r0,...,r(R-1)]`. For natural b,c,i,r, the compiler expands

    Beta(b,c,i,r) :=
      r < 1+(i+1)*c
      and exists q < b+1 (b = q*(1+(i+1)*c)+r).

Cell (t,j) is read using index K*t+j. The computation graph is

    exists length,b,c (
        Initial(b,c,arguments)
        and Final(b,c,length,output)
        and forall t<length Step(row(t),row(t+1))
    ).

Initial fixes every register and the entry pc. Final requires an actual HALT
location and the designated output value. Transition rows are extracted using
bounded existential variables less than b+1. Every beta residue is at most b,
so this bound loses no possible row. Quotient variables have the same safe bound.
`Step` is the disjunction of the actual program instructions; HALT contributes
no branch. The zero-step trace is possible exactly when the entry is a HALT
and its initialized output equals the requested output.

Instruction arithmetic is explicit. In particular:

    SUB(a,b,r): (a<b and r=0) or a=r+b
    DIVMOD(a,d,q,r):
      (d=0 and q=0 and r=a)
      or (not d=0 and r<d and a=d*q+r).

The conjunction asserting unchanged registers is shared through a balanced
segment tree. This reduces storage without weakening any register constraint.

For any finite sequence, suitable b,c exist by the Chinese remainder theorem.
For L cells with largest value A, choosing c=(A+1)*L! makes the L moduli pairwise
coprime and larger than the respective residues. This mathematical existence
argument must not be confused with a runtime search for b. A native trace may
be replayed as a finite array, with beta existence remaining an explicit reviewed
mathematical dependency. Small reference cases can carry fully computed b,c.

## Sigma-1 correspondence and its limits

In PA with the usual defined order notation, the generated source formula has
an existential prefix `length,b,c` and a matrix containing only bounded
quantifiers. `bounded_sigma_one_record` verifies this syntactic property.
`expand_bounded_dag` performs the displayed capture-free definitions, and
`verify_compilation` regenerates the complete artifact from the program.

The resulting `arithmetic_dag` uses only the base signature. It is exactly the
definitional translation of the bounded-order formula. It is **not** claimed to
be literally prenex Sigma-1 when every defined-order quantifier is counted as an
unbounded quantifier in the raw AST. Use the bounded presentation and its
definitional correspondence when invoking arithmetical-hierarchy results.
PA proves the order-definition equivalences; consequently the translation and
its bounded presentation describe the same relation under that interpretation.

This check establishes syntax and exact macro expansion. Separate review must
establish beta sequence existence, instruction determinism, the program's intended
algorithm, and the chosen proof predicate's internal derivability properties.
In particular, neither a generated Sigma-1 computation formula nor agreement
on tested natural inputs by itself establishes D2 or D3. No HBL or formal-kernel
status is promoted by this compiler.

## Build artifact and validation interface

`compile_program(program)` returns program/compiler IDs and versions, the canonical
program SHA-256, free input variable names `x0...`, the next variable as output,
`bounded_dag`, `arithmetic_dag`, their byte hashes, size statistics, hierarchy
record and a narrowly scoped definitional-correspondence record.

`compile_step(program)` produces the transition relation alone for independent
small-state tests. Its variable map states which names denote pre/post pc and
registers. `verify_compilation(program,bundle)` recomputes all fields and returns
false on differences. Recompilation is an integrity check, not an independent
mathematical oracle.

```sh
python3 shared/representation_compiler.py shared/register_programs.json \
  --output generated-formulas.json
```

Private research and proof-review files are not distribution dependencies.
