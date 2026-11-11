# Canonical syntax and numbering 1.0

Every node has exactly the fields args, kind and name. The args field is an array,
including when empty. The canonical byte representation has sorted keys, no
whitespace and ASCII strings. For example:

```json
{"args":[],"kind":"var","name":"x"}
```

Names match `[A-Za-z][A-Za-z0-9_]*` and have at most 64 characters. Logical
connectives use the empty name; quantifiers store their bound variable name.
The supported kinds are var, const, func, pred, eq, not, and, or, implies, forall,
exists and bottom. Version 0.2.0 additionally supports `num`, whose name is a
canonical natural decimal string of at most 4096 digits and whose args are empty.
This conservative notation does not alter old expression bytes. Each complete expression uses consistent arities for each
function or predicate symbol. No signature is implicitly shared by otherwise
unrelated expressions. Proofs and searches do share one arity registry.

Hard budgets: depth 64 (root at depth 1), 1000 nodes, 65536 canonical serialized
bytes. Public constructors and transformations enforce these budgets. Invalid
types, extra fields and cyclic wire structures are rejected. Deserialize tolerates
JSON whitespace/key order but rejects duplicate keys. No eval or dynamic rule
loading is involved.

The numbering identifier is `goedel-json-byte-v1`. Begin with n=1 and process
canonical UTF-8 bytes b in order, replacing n by 256*n+b. Return the resulting
integer as a canonical decimal string. The leading base-256 digit 1 records the
start of the byte sequence, including leading zero bytes. Uniqueness of base-256
expansion proves that distinct canonical byte strings receive distinct numbers;
syntax canonicalization is injective on this finite tree representation.

The decoder requires a positive decimal string without a leading zero, at most
2500 digits. It checks the sentinel, UTF-8, the tree schema and exact equality to
the canonical payload. Both directions permit at most 1024 encoded bytes. Codes
are never converted to a floating-point number. Python uses exact integers;
R uses an independent exact decimal-string algorithm. This useful engineering
numbering is not claimed to be Goedel's historical numbering or a formal proof
of representability in PA.

SHA-256 fingerprints cover canonical UTF-8 expression bytes. Catalogue hashes
cover the exact packaged JSON file bytes. These are different contracts.
