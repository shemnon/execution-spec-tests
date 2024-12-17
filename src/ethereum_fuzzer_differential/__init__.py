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
3. Nethermind had RIP-7212 p256verify activated in Prague.
   Test [PR #1021](https://github.com/ethereum/execution-spec-tests/pull/1021)
4. Besu created a "ghost" account when calling a non-existent account that prevented a subsequent
   value-bearing EXTCALL from being charged for account creation.
   Test [PR #1025](https://github.com/ethereum/execution-spec-tests/pull/1025)
5. Evmone does not have a fully functional expmod precompile. Clients under test need to be
   configured to use [an
   external library.](https://github.com/ethereum/evmone/blob/master/README.md?plain=1#L100-L102)

"""
