"""
Execution loop for EOF differential fuzzing


Trophies
--------

The following bugs were found using the differential fuzzer

1. Besu EOFCREATE memory sizes clamped to i32 instead of i64, impacting gas calculations
   (found with ReplacePushWithAddress).
   Test [PR #989](https://github.com/ethereum/execution-spec-tests/pull/989)
2. Geth DATACOPY values could overflow uint64 (found with ReplacePushWithMagic)
   Test [PR #1020](https://github.com/ethereum/execution-spec-tests/pull/1020)

"""
