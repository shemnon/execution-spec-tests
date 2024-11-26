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
def differential_fuzzing(
    corpus_dir: str, work_dir: str, runtest_binary: str, clients: Dict[str, str]
):
    """
    The CLI wrapper run differential fuzzing
    """
    corpus = build_corpus(corpus_dir)

    diff_fuzz = DifferentialFuzzer(corpus, work_dir, runtest_binary, clients, step_num=43)
    diff_fuzz.run_step()


if __name__ == "__main__":
    differential_fuzzing()
