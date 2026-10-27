"""
Runs task_n(*args) from a student's submission file directly — no runner,
no subprocess-per-runner-invocation. Each call happens in its own child
process so that:

  1. a timeout can be enforced on the call itself (module-level import
     included, since a student could in principle stall there too), and
  2. a segfault / infinite loop / runaway memory use in one student's code
     can't take down the grading run for everyone else.

Communication with the child is via a multiprocessing.Queue; the result
must be picklable, which NumPy arrays, pandas DataFrames/Series, tuples,
and plain Python scalars all are.
"""

import importlib.util
import multiprocessing as mp
import time
import traceback
from queue import Empty

# "forkserver" instead of plain "fork": every worker is forked from a single
# clean, single-threaded server process instead of from this (multithreaded,
# once NumPy/SciPy's BLAS backend spins up) grading process. Preloading
# numpy/pandas/scipy into that server means workers still start almost as
# fast as a plain fork would.
mp.set_forkserver_preload(["numpy", "pandas", "scipy"])
_CTX = mp.get_context("forkserver")


def _load_and_call(submission_path, func_name, args, queue):
    try:
        spec = importlib.util.spec_from_file_location("student_submission", submission_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        func = getattr(module, func_name)

        start = time.perf_counter()
        result = func(*args)
        elapsed = time.perf_counter() - start

        queue.put(("ok", result, elapsed))
    except Exception as e:
        queue.put(("error", f"{type(e).__name__}: {e}", None))
    except BaseException:
        # e.g. a raw SystemExit some over-eager student code triggers
        queue.put(("error", "process raised BaseException:\n" + traceback.format_exc(), None))


def run_task(submission_path, func_name, args, timeout):
    """
    Returns a dict:
      {
        "status":  "ok" | "error" | "timeout",
        "result":  the return value (only if status == "ok"),
        "elapsed": seconds spent inside the call (only if status == "ok"),
        "message": error text (only if status == "error"),
      }
    """
    queue = _CTX.Queue()
    proc = _CTX.Process(
        target=_load_and_call, args=(submission_path, func_name, args, queue), daemon=True
    )
    proc.start()

    # NOTE: queue.get(timeout=...) is called BEFORE proc.join(), not after.
    # A multiprocessing.Queue is backed by a pipe with a limited OS buffer.
    # For a large result (e.g. a big DataFrame/array from the "big" test
    # cases) the child can block *writing* to that pipe until someone reads
    # it. Calling proc.join(timeout) first — waiting for the child to exit
    # before ever draining the queue — deadlocks in exactly that case: the
    # child can't finish exiting until its write completes, and the write
    # can't complete until the parent reads, which the parent isn't doing
    # yet. That deadlock would look indistinguishable from "the student's
    # code is just slow" without actually being that, so get() must come
    # first.
    try:
        status, payload, elapsed = queue.get(timeout=timeout)
    except Empty:
        if proc.is_alive():
            proc.terminate()
            proc.join()
            return {"status": "timeout", "message": f"exceeded {timeout}s wall-clock limit"}
        # process died before producing anything: crash/segfault/OOM-kill
        proc.join()
        return {
            "status": "error",
            "message": f"submission process exited with code {proc.exitcode} "
                       f"and produced no result (likely a crash, not a timeout)",
        }

    # Result received — let the child finish exiting. This should be near-
    # instant now that the pipe has been drained; the generous grace period
    # is just a safety net, not part of the real time budget.
    proc.join(timeout=5)
    if proc.is_alive():
        proc.terminate()
        proc.join()

    if status == "ok":
        return {"status": "ok", "result": payload, "elapsed": elapsed}
    else:
        return {"status": "error", "message": payload}
