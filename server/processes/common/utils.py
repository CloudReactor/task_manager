from typing import Any
from collections import abc
import logging
import re


logger = logging.getLogger(__name__)


def generate_clone_name(name):
    p = re.compile(r"(.+) \(Copy (\d+)\)", re.IGNORECASE)
    m = p.match(name)

    if m:
        return f"{m.group(1)} (Copy {int(m.group(2)) + 1})"
    else:
        return f"{name} (Copy 1)"


# From glglgl on
# https://stackoverflow.com/questions/4978738/is-there-a-python-equivalent-of-the-c-sharp-null-coalescing-operator
def coalesce(*arg):
    return next((a for a in arg if a is not None), None)


def deepmerge_with_lists_pair(x: Any, y: Any) -> Any:
    if isinstance(x, str): # because string is iterable
        return y

    if isinstance(x, abc.Mapping):
        if isinstance(y, abc.Mapping):
            for k, v in y.items():
                if k in x:
                    x[k] = deepmerge_with_lists_pair(x[k], v)
                else:
                    x[k] = v

            return x

        logger.warning(f"Attempt to merge dict {x} with non-dict {y}")
        return y

    if isinstance(x, abc.Iterable):
        if isinstance(y, abc.Iterable):
          x_len = len(x)
          y_len = len(y)
          for i, v in enumerate(x):
              if i < y_len:
                  x[i] = deepmerge_with_lists_pair(x[i], y[i])
              else:
                  break

          i = x_len
          while i < y_len:
              x.append(y[i])
              i += 1
        else:
            logger.warning(f"Attempt to merge iterable {x} with non-iterable {y}")
            return y

    return y

def deepmerge_with_lists(*args) -> Any:
    """
    Deep merge, including dict elements of lists.
    The first argument is modified in place.
    """
    first = None

    for i, a in enumerate(args):
        if i == 0:
            first = a
        else:
            first = deepmerge_with_lists_pair(first, a)

    return first