"""
//FIXME
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List

from ethereum_clis.file_utils import write_json_file
from ethereum_fuzzer_differential.mutator import StateTestMutator
from ethereum_fuzzer_differential.strategies.basic_strategies import default_strategies
from ethereum_test_fixtures.file import Fixtures, StateFixtures
from ethereum_test_fixtures.state import Fixture as StateFixture


class DifferentialFuzzer:
    """
    Holds the execution state and logic of the differential fuzzer
    """

    corpus: List[StateFixtures]
    work_dir: str
    step_num: int
    runtest_binary: str
    client_list: Dict[str, str]
    test_prefix: str
    mutator: StateTestMutator

    def __init__(
        self,
        corpus: List[StateFixtures],
        work_dir: str,
        runtest_binary: str,
        client_list: Dict[str, str],
        step_num: int = 0,
        test_prefix: str = "mutated_test",
    ) -> None:
        self.corpus = corpus
        self.work_dir = work_dir
        self.runtest_binary = runtest_binary
        self.client_list = client_list
        self.step_num = step_num
        self.test_prefix = test_prefix
        self.mutator = StateTestMutator(default_strategies)

    def run_step(self):
        """Run a single step of the fuzzer."""
        self.step_num = self.step_num + 1
        self.mutate_corpus()
        self.write_corpus()
        if self.execute_runtest():
            self.cleanup_round(self.step_num)
            return True
        else:
            return False

    def mutate_corpus(self):
        """Mutates the corpus."""
        new_corpus = []
        for state in self.corpus:
            try:
                fixtures, mutation = self.mutator.mutate(state)
                new_corpus.append(fixtures)
            except Exception as e:
                print(e)
                new_corpus.append(state)
        self.corpus = new_corpus

    def write_corpus(self):
        """Writes the mutated corpus for the current round to the working directory."""
        for idx, state_test in enumerate(self.corpus):
            test = {
                test_name: test_body.json_dict_with_info()
                for (test_name, test_body) in state_test.root.items()
            }
            write_json_file(
                test,
                os.path.join(
                    self.work_dir, "{}_{}_{}.json".format(self.test_prefix, self.step_num, idx)
                ),
            )

    def execute_runtest(self):
        """Executes goevmlab's runtest against the working files for the current round."""
        clients = [["--" + client[0], client[1]] for client in self.client_list]
        output_dir = os.path.join(
            self.work_dir, "runtest_%s_%s" % (self.test_prefix, self.step_num)
        )
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        args = [
            str(self.runtest_binary),
            *[c for cc in clients for c in cc],
            "--outdir",
            output_dir,
            os.path.join(self.work_dir, "{}_{}_*.json".format(self.test_prefix, self.step_num)),
        ]
        print(args)
        try:
            result = subprocess.run(args, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception("evm process unexpectedly returned a non-zero status code: " f"{e}.")
        except Exception as e:
            raise Exception(f"Unexpected exception calling evm tool: {e}.")
        print(result.stdout)
        print(result.stderr)
        return "Consensus error" not in result.stdout

    def cleanup_round(self, step_num):
        """Removes the corpus files from the current round."""
        round_prefix = "%s_%s_" % (self.test_prefix, self.step_num)
        for subdir, dirs, files in os.walk(self.work_dir):
            for file in files:
                if file.startswith(round_prefix) and file.endswith(".json"):
                    os.remove(os.path.join(subdir, file))


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
