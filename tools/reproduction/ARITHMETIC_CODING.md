# Arithmetic presentation numbering v1

Identifier: goedel-arithmetic-dag-v1. This numbers **DAG presentations**, including
unreachable nodes and repeated identical nodes. It does not identify alpha-
equivalent expressions, or two DAGs with the same expanded root formula. Do not
prune or hash-cons a presentation after taking its code.

For a finite sequence of natural numbers, E([])=1 and
E([a]+tail)=cons(a,E(tail)). Let v=a+1 and k=bit_length(v)>=1. Then

    cons(a,s) = 2^(2*k)*s + (2^k-1) + 2^(k+1)*(v-2^(k-1)).

A cell, read from the least significant end, contains k one bits, a zero,
and the low k-1 bits of v. The rest is the remaining sequence, ending with the
sentinel 1. Every value and code is an exact natural; public wire numbers use
canonical decimal strings. 0 is invalid. Decode rejects unterminated, missing-
sentinel and malformed cells. E([0])=5, E([1])=19, E([2])=27, E([0,0])=21.
Mathematical E/D have no size cutoff; runtime item/bit/digit budgets are explicit.

DAG envelope: exactly schema_version='1.0', nodes, root. Each node is exactly
{op,name,args}. Child references in this envelope are zero-based prior node indices.
For a numbered presentation root MUST be the final node. Each numeric record has
FOUR cells [tag,label,left,right]. Numeric child references are 1-based; zero
means absent. The flat sequence is [20261105,1,N,record1...,recordN...].

| tag | op | label | children / sort |
|---:|---|---|---|
|0|num|literal natural value|none; term|
|1|var|natural index of xN|none; term|
|2|zero|0|none; term|
|3|succ|0|one term|
|4|add|0|two terms|
|5|mul|0|two terms|
|6|eq|0|two terms; formula|
|7|not|0|one formula|
|8|and|0|two formulas|
|9|or|0|two formulas|
|10|implies|0|two formulas|
|11|forall|natural index of xN|one formula|
|12|exists|natural index of xN|one formula|
|13|bottom|0|none; formula|

DAG variable/binder name is x followed by canonical decimal index. Import of an
ordinary Expr name maps it injectively to index=int.from_bytes(b'\x01'+ASCII(name),
'big'). A compiler-generated xN is already in the DAG namespace and is not
re-imported. Decimal numeral names are exact natural literals. NUM denotes the
conservative binary Horner term with nu0=0, nu1=S0, nu(2k)=2*nu(k) and
nu(2k+1)=S(2*nu(k)) for k>=1, two=S(S0). No new arithmetic constant is assumed.

Closed-numeral code substitution SUB(a,i,n) is totalized to 0 for invalid DAG
codes. For a valid N-node presentation retain all N original records and append
N transformed records, in order. A var(i) becomes num(n). A binder for i is
copied with its original child references. All other nodes are copied with each
present child j replaced by j+N. The root becomes 2N. This changes exactly free
occurrences at the denoted root; retained unreachable nodes may contain other
free variables but do not affect the denoted formula. The retained presentation
is essential to the exact fixed-point code equation. Public syntactic validity
and proof validity remain distinct.
