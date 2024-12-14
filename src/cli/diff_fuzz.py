"""
Runs differential fuzzing
"""


from typing import Dict

import click

from ethereum_fuzzer_differential.differential_fuzzer import DifferentialFuzzer, build_corpus


@click.command(
    help=("Executes EOF differential fuzzing using local generation and goevmlab execution")
)
@click.option(
    "--corpus",
    "-c",
    "corpus_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True),
    required=True,
    help="The corpus, a directory holding state tests",
)
@click.option(
    "--work",
    "-w",
    "work_dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, readable=True, writable=True),
    default="/tmp/diff_fuzz",
    help="The work dir, which will hold temporary files and error results",
)
@click.option(
    "--cleanup-tests",
    "cleanup_tests",
    type=bool,
    default=True,
    help="Cleanup generated tests that are uninteresting from the work dir. Step summaries are unaffected",
)
@click.option(
    "--runtest",
    "-r",
    "runtest_binary",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, executable=True),
    default="runtest",
    help="The goevmlab runtest binary",
)
@click.option(
    "--client",
    "clients",
    type=(str, str),
    multiple=True,
    help="clients to fuzz test against.",
)
@click.option(
    "--skip-trace",
    "skip_trace",
    type=bool,
    required=False,
    default=False,
    help="Skip execution trace comparison and rely on state roots.\nFaster, more compatible EVMs, but less coverage.",
)
@click.option(
    "--max-gas",
    "max_gas",
    type=int,
    required=False,
    default=100_000_000,
    help="Maximum amount of gas to pass out of mutation.",
)
@click.option(
    "--step-count",
    "steps",
    type=int,
    required=False,
    default=10,
    help="Number of mutation steps to run before stopping",
)
@click.option(
    "--step-num",
    "step_num",
    type=int,
    required=False,
    default=1,
    help="Step number to start counting at",
)
def differential_fuzzing(
    corpus_dir: str,
    work_dir: str,
    cleanup_tests: bool,
    runtest_binary: str,
    clients: Dict[str, str],
    skip_trace: bool,
    max_gas: int,
    steps: int,
    step_num: int,
):
    """
    The CLI wrapper run differential fuzzing
    """
    corpus = build_corpus(corpus_dir)

    diff_fuzz = DifferentialFuzzer(
        corpus, work_dir, cleanup_tests, runtest_binary, clients, skip_trace, max_gas, steps=range(step_num, step_num + steps)
    )
    diff_fuzz.run_steps()


if __name__ == "__main__":
    differential_fuzzing()
