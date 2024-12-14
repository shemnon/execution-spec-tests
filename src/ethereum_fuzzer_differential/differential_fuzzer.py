"""
//FIXME
"""
import glob
import os
import re
import shutil
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List

from ethereum_clis.file_utils import write_json_file
from ethereum_fuzzer_differential.mutator import MutateError, StateTestMutator
from ethereum_fuzzer_differential.strategies.basic_strategies import default_strategies
from ethereum_test_fixtures.file import Fixtures, StateFixtures
from ethereum_test_fixtures.state import Fixture as StateFixture


def build_state_fixtures_context(state: StateFixtures):
    """Extracts all the addresses into a context map."""
    test = next(iter(state.items()))
    fixture = test[1]
    addresses = []
    for (addr, acct) in fixture.pre.root.items():
        addresses.append(addr)
    return {"addresses": sorted(addresses)}


class DifferentialFuzzer:
    """
    Holds the execution state and logic of the differential fuzzer
    """

    corpus: List[StateFixtures]
    work_dir: str
    cleanup_tests: bool
    steps: range
    runtest_binary: str
    client_list: Dict[str, str]
    skip_trace: bool
    test_prefix: str
    mutator: StateTestMutator

    def __init__(
        self,
        corpus: List[StateFixtures],
        work_dir: str,
        cleanup_tests: bool,
        runtest_binary: str,
        client_list: Dict[str, str],
        skip_trace:bool,
        max_gas: int,
        steps: range,
        test_prefix: str = "mutated_test",
    ) -> None:
        self.corpus = corpus
        self.work_dir = work_dir
        self.cleanup_tests = cleanup_tests
        self.runtest_binary = runtest_binary
        self.client_list = client_list
        self.skip_trace = skip_trace
        self.steps = steps
        self.test_prefix = test_prefix
        self.mutator = StateTestMutator(max_gas, default_strategies)

    def run_steps(self):
        """Run the fuzzer over the specified steps range."""
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)
        for step_num in self.steps:
            self.run_step(step_num)

    def run_step(self, step_num: int):
        """Run the fuzzer for a single step."""
        self.mutate_corpus()
        self.write_corpus(step_num)
        clean_run: bool = self.execute_runtest(step_num)
        self.finish_round(step_num)
        return clean_run

    def mutate_corpus(self):
        """Mutates the corpus."""
        new_corpus = []
        for state in self.corpus:
            context = build_state_fixtures_context(state)
            try:
                fixtures, mutation = self.mutator.mutate(state, context)
                new_corpus.append(fixtures)
            except MutateError:
                # Mutation failed for an expected reason, just don't mutate this test
                new_corpus.append(state)
            except Exception as e:
                # bigger issue, log exception
                traceback.print_exc()
                print(e)
                new_corpus.append(state)

        self.corpus = new_corpus

    def write_corpus(self, step_num: int):
        """Writes the mutated corpus for the current round to the working directory."""
        for idx, state_test in enumerate(self.corpus):
            test = {
                test_name: test_body.json_dict_with_info()
                for (test_name, test_body) in state_test.root.items()
            }
            write_json_file(
                test,
                os.path.join(
                    self.work_dir, "{}_{}_{}.json".format(self.test_prefix, step_num, idx)
                ),
            )

    def execute_runtest(self, step_num: int):
        """Executes goevmlab's runtest against the working files for the current round."""
        clients = [["--" + client[0], client[1]] for client in self.client_list]
        output_dir = os.path.join(self.work_dir, "runtest_%s_%s" % (self.test_prefix, step_num))
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        args = [
            str(self.runtest_binary),
            *[c for cc in clients for c in cc],
            "--outdir",
            output_dir,
            *(["--skiptrace"] if self.skip_trace else []),
            os.path.join(self.work_dir, "{}_{}_*.json".format(self.test_prefix, step_num)),
        ]
        with open(os.path.join(output_dir, "runtest-args.txt"), "w") as f:
            f.write(" ".join(args))

        try:
            result = subprocess.run(args, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception("evm process unexpectedly returned a non-zero status code: " f"{e}.")
        except Exception as e:
            raise Exception(f"Unexpected exception calling evm tool: {e}.")

        with open(os.path.join(output_dir, "runtest-out.txt"), "w") as f:
            f.write(result.stdout)
        with open(os.path.join(output_dir, "runtest-err.txt"), "w") as f:
            f.write(result.stderr)

        for bug in set(
            re.findall(
                os.path.join(self.work_dir, r"{}_{}_\d+.json".format(self.test_prefix, step_num)),
                result.stdout,
            )
        ):
            print("Consensus fault found:", bug)
            shutil.move(bug, output_dir)

        return "Consensus error" not in result.stdout

    def finish_round(self, step_num: int):
        """Logs completion and performs configured cleanup steps."""
        print("Finished step %d/%d..." % (step_num, self.steps[-1]))
        if self.cleanup_tests:
            for f in glob.glob(
                os.path.join(self.work_dir, "%s_%s_*.json" % (self.test_prefix, step_num))
            ):
                os.remove(f)


def build_corpus(corpus_dir: str):
    """Builds and edits the corpus files from a seed directory."""
    corpus = []
    for subdir, dirs, files in os.walk(corpus_dir):
        for file in files:
            try:
                state_tests = Fixtures.from_file(
                    Path(os.path.join(subdir, file)), fixture_format=StateFixture
                )
                for (name, state_test) in state_tests.root.items():
                    # re-write info
                    state_test.info = {
                        "comment": "diff_fuzz corpus file",
                        "source": str(file),
                        "mutations": "",
                    }
                corpus.append(state_tests)
            except ValueError:
                # Only mask value errors such as json errors and state test format errors
                continue
    return corpus
