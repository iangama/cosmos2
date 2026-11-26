"""Bounded stabilization before preflight only; never used inside measurements."""
import time

TRANSIENT_MESSAGES = (
    'Unresolved candidate in owned snapshot:',
    'Owned scope root missing from Windows snapshot',
    'Owned root parent changed after Windows snapshot',
    'Candidate parent changed after Windows snapshot',
    'Process exited during owned Windows inventory:',
)


def stabilize(inventory, observe, *, seconds=45, required=5, poll_s=1,
              clock=time.monotonic, sleep=time.sleep):
    if seconds <= 0 or required < 1 or poll_s <= 0:
        raise ValueError('Invalid preparation bounds')
    started = clock()
    deadline = started + seconds
    count = 0
    previous = None
    while True:
        if clock() >= deadline:
            raise TimeoutError('Owned process tree did not stabilize before preflight')
        row = dict(offset_s=clock()-started)
        try:
            tree = inventory()
        except (OSError, ValueError) as error:
            if isinstance(error, ValueError) and not str(error).startswith(TRANSIENT_MESSAGES):
                raise
            count = 0
            previous = None
            row.update(error=str(error),error_type=type(error).__name__,
                       cause=repr(error.__cause__) if error.__cause__ else None)
        else:
            count = count + 1 if tree == previous else 1
            previous = tree
            row['owned'] = tree
        row['consecutive_stable'] = count
        observe(row)
        if clock() >= deadline:
            raise TimeoutError('Owned process preparation exceeded its deadline')
        if count >= required:
            return dict(consecutive_stable=count,elapsed_s=clock()-started)
        sleep(min(poll_s,max(0,deadline-clock())))
