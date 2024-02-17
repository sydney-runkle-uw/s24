from collections import OrderedDict
import json
import os
import traceback
import shutil

import multiprocessing

multiprocessing.set_start_method("fork")

def warn(msg):
    print(f"\033[93mWarning: {msg}\033[00m")

def error(msg):
    print(f"\033[91mError: {msg}\033[00m")

ARGS = None

DEBUG = False
VERBOSE = False

TMP_DIR = "/tmp/_cs544_tester_directory"
TEST_DIR = None
DEBUG_DIR = "_autograder_results"

# full list of tests
INIT = None
TESTS = OrderedDict()
CLEANUP = None

# dataclass for storing test object info
class _unit_test:
    def __init__(self, func, points, timeout, desc):
        self.func = func
        self.points = points
        self.timeout = timeout
        self.desc = desc

    def run(self, ret):
        points = 0

        try:
            result = self.func()
            if not result:
                points = self.points
                result = f"PASS ({self.points}/{self.points})"
        except Exception as e:
            result = traceback.format_exception(e)
            print(f"Exception in {self.func.__name__}:\n")
            print("\n".join(result) + "\n")

        ret.send((points, result))


# init decorator
def init(init_func):
    global INIT
    INIT = init_func
    return init_func


# test decorator
def test(points, timeout=None, desc=""):
    def wrapper(test_func):
        TESTS[test_func.__name__] = _unit_test(
            test_func, points, timeout, desc)

    return wrapper

# debug dir decorator
def debug(debug_func):
    global DEBUG
    DEBUG = debug_func
    return debug_func

# cleanup decorator
def cleanup(cleanup_func):
    global CLEANUP
    CLEANUP = cleanup_func
    return cleanup_func


# get arguments
def get_args():
    return ARGS

# lists all tests
def list_tests():
    for test_name, test in TESTS.items():
        print(f"{test_name}({test.points}): {test.desc}")


# run all tests
def run_tests():
    results = {
        "score": 0,
        "full_score": 0,
        "tests": {},
    }

    for test_name, test in TESTS.items():
        if VERBOSE:
            print(f"===== Running Test {test_name} =====")

        results["full_score"] += test.points

        ret_send, ret_recv = multiprocessing.Pipe()
        proc = multiprocessing.Process(target=test.run, args=(ret_send,))
        proc.start()
        proc.join(test.timeout)
        if proc.is_alive():
            proc.terminate()
            points = 0
            result = "Timeout"
        else:
            (points, result) = ret_recv.recv()

        if VERBOSE:
            print(result)
        results["score"] += points
        results["tests"][test_name] = result

    assert results["score"] <= results["full_score"]
    if VERBOSE:
        print("===== Final Score =====")
        print(json.dumps(results, indent=4))
        print("=======================")

    if DEBUG:
        debug_abs_path = f"{TEST_DIR}/{DEBUG_DIR}"
        shutil.rmtree(debug_abs_path, ignore_errors=True)
        shutil.copytree(src=TMP_DIR, dst=debug_abs_path, dirs_exist_ok=True)
        print(f"Run results are stored to {debug_abs_path}")

    # cleanup code after all tests run
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    return results


# save the result as json
def save_results(results):
    output_file = f"{TEST_DIR}/test.json"
    print(f"Output written to: {output_file}")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)


def check_files(test_dir, required_files):
    if not os.path.isdir(f"{test_dir}/.git"):
        warn(f"{test_dir} is not a repository")
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(f"{test_dir}/{file}"):
            missing_files.append(file)
    if len(missing_files) > 0:
        msg = ", ".join(missing_files)
        warn(f"the following required files are missing: {msg}")


def tester_main(parser, required_files=[]):
    global ARGS, VERBOSE, TEST_DIR, DEBUG

    parser.add_argument(
        "-d", "--dir", type=str, default=".", help="path to your repository"
    )
    parser.add_argument("-l", "--list", action="store_true",
                        help="list all tests")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-g", "--debug", action="store_true",
                        help="create a debug directory with the files used while testing")
    args = parser.parse_args()

    ARGS = args

    if args.list:
        list_tests()
        return

    VERBOSE = args.verbose
    DEBUG = args.debug
    test_dir = args.dir
    if not os.path.isdir(test_dir):
        error("invalid path")
        return
    TEST_DIR = os.path.abspath(test_dir)

    # check if required files are present
    check_files(test_dir, required_files)

    # make a copy of the code
    def ignore(_dir_name, _dir_content): return [
        ".git", ".github", "__pycache__", ".gitignore", "*.pyc", DEBUG_DIR]
    shutil.copytree(src=TEST_DIR, dst=TMP_DIR,
                    dirs_exist_ok=True, ignore=ignore)
    os.chdir(TMP_DIR)

    # run init
    if INIT:
        INIT()

    # run tests
    results = run_tests()
    save_results(results)

    # run cleanup
    if CLEANUP:
        CLEANUP()
