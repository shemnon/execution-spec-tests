"""
Ethereum EOF test spec definition and filler.
"""
import subprocess
from pathlib import Path
from shutil import which
from subprocess import CompletedProcess, run
from typing import Callable, ClassVar, Generator, List, Optional, Type

from ethereum_test_forks import Fork
from evm_transition_tool import FixtureFormats

from ...common.base_types import Bytes
from ...exceptions import EOFException, EvmoneExceptionParser
from ..base.base_test import BaseFixture, BaseTest
from .types import Fixture, Result


class EOFParse:
    """evmone-eofparse binary."""

    binary: Path

    def __new__(cls):
        """Make EOF binary a singleton."""
        if not hasattr(cls, "instance"):
            cls.instance = super(EOFParse, cls).__new__(cls)
        return cls.instance

    def __init__(
        self,
        binary: Optional[Path | str] = None,
    ):
        if binary is None:
            which_path = which("evmone-eofparse")
            if which_path is not None:
                binary = Path(which_path)
        if binary is None or not Path(binary).exists():
            raise Exception("""`evmone-eofparse` binary executable not found""")
        self.binary = Path(binary)

    def run(self, *args: str, input: str | None = None) -> str:
        """Run evmone with the given arguments"""
        result = run(
            [self.binary, *args],
            capture_output=True,
            text=True,
            input=input,
        )
        return result.stdout


class BesuEOFParse:
    """Besu evmtool code-validate binary."""

    binary: Path
    process: Optional[subprocess.Popen] = None

    def __new__(cls):
        """Make EOF binary a singleton."""
        if not hasattr(cls, "instance"):
            cls.instance = super(BesuEOFParse, cls).__new__(cls)
        return cls.instance

    def __init__(
        self,
        binary: Optional[Path | str] = None,
    ):
        if binary is None:
            which_path = which("evmtool")
            if which_path is not None:
                binary = Path(which_path)
        if binary is None or not Path(binary).exists():
            raise Exception("""`evmtool` binary executable not found""")
        self.binary = Path(binary)

    def start_server(self):
        """
        Starts the t8n-server process, extracts the port, and leaves it running for future re-use.
        """
        args = [
            str(self.binary),
            "code-validate",
        ]

        self.process = subprocess.Popen(
            args=args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def shutdown(self):
        """
        Stops the t8n-server process if it was started
        """
        if self.process:
            self.process.kill()

    def run(self, *args: str, input: str | None = None) -> str:
        """Run evmone with the given arguments"""
        if not self.process:
            self.start_server()

        self.process.stdin.writelines([bytes(input + "\n", "utf-8")])
        self.process.stdin.flush()
        return str(self.process.stdout.readline())


class EOFTest(BaseTest):
    """
    Filler type that tests EOF containers.
    """

    data: Bytes
    expect_exception: EOFException | None = None

    supported_fixture_formats: ClassVar[List[FixtureFormats]] = [
        # TODO: Potentially generate a state test and blockchain test too.
        FixtureFormats.EOF_TEST,
    ]

    def make_eof_test_fixture(
        self,
        *,
        fork: Fork,
        eips: Optional[List[int]],
    ) -> Fixture:
        """
        Generate the EOF test fixture.
        """
        fixture = Fixture(
            vectors={
                "0": {
                    "code": self.data,
                    "results": {
                        fork.blockchain_test_network_name(): {
                            "exception": self.expect_exception,
                            "valid": self.expect_exception is None,
                        }
                    },
                }
            }
        )
        # eof_parse = EOFParse()
        eof_parse = BesuEOFParse()
        for _, vector in fixture.vectors.items():
            expected_result = vector.results.get(str(fork))
            if expected_result is None:
                raise Exception(f"EOF Fixture missing vector result for fork: {fork}")
            result = eof_parse.run(input=str(vector.code))
            self.verify_result(result, expected_result, vector.code)

        return fixture

    def verify_result(self, result: str, expected_result: Result, code: Bytes):
        """
        Checks that the actual reported exception string matches our expected error ENUM
        """
        parser = EvmoneExceptionParser()
        res_error = result.replace("\n", "")
        if expected_result.exception is None:
            if "OK" not in result:
                msg = "Expected eof code to be valid, but got an exception:"
                formatted_message = (
                    f"{msg} \n"
                    f"{code} \n"
                    f"Expected: No Exception \n"
                    f"     Got: {parser.rev_parse_exception(res_error)} ({res_error})"
                )
                raise Exception(formatted_message)
        else:
            if "OK" in res_error:
                expRes = expected_result.exception
                msg = "Expected eof code to be invalid, but got no exception from eof tool:"
                formatted_message = (
                    f"{msg} \n"
                    f"{code} \n"
                    f"Expected: {expRes} ({parser.parse_exception(expRes)}) \n"
                    f"     Got: No Exception"
                )
                raise Exception(formatted_message)
            # else:
            #     expRes = expected_result.exception
            #     if expRes == parser.rev_parse_exception(res_error):
            #         return
            #
            #     msg = "EOF code expected to fail with a different exception, than reported:"
            #     formatted_message = (
            #         f"{msg} \n"
            #         f"{code} \n"
            #         f"Expected: {expRes} ({parser.parse_exception(expRes)}) \n"
            #         f"     Got: {parser.rev_parse_exception(res_error)} ({res_error})"
            #     )
            #     raise Exception(formatted_message)

    def generate(
        self,
        *,
        fork: Fork,
        eips: Optional[List[int]] = None,
        fixture_format: FixtureFormats,
        **_,
    ) -> BaseFixture:
        """
        Generate the BlockchainTest fixture.
        """
        if fixture_format == FixtureFormats.EOF_TEST:
            return self.make_eof_test_fixture(fork=fork, eips=eips)

        raise Exception(f"Unknown fixture format: {fixture_format}")


EOFTestSpec = Callable[[str], Generator[EOFTest, None, None]]
EOFTestFiller = Type[EOFTest]
