"""
Execution loop for EOF differential fuzzing


Trophies
--------

The following bugs were found using the differential fuzzer

1. Besu EOFCREATE memory sizes clamped to i32 instead of i64, impacting gas calculations
   (found with ReplacePushWithAddress).
   Besu [PR #7979](https://github.com/hyperledger/besu/pull/7979)
2. Geth DATACOPY values could overflow uint64 (found with ReplacePushWithMagic)
   [Commit](https://github.com/shemnon/go-ethereum/commit/5ce932e592511d491ea535f07989f63e50dd35d5)

"""
