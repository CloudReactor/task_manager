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


def deepmerge_with_lists_pair(dest: Any, src: Any) -> Any:
    if isinstance(dest, str): # because string is iterable
        return src

    if isinstance(dest, abc.Mapping):
        if (not isinstance(src, str)) and isinstance(src, abc.Mapping):
            for k, v in src.items():
                if k in dest:
                    dest[k] = deepmerge_with_lists_pair(dest[k], v)
                else:
                    dest[k] = v

            return dest

        logger.warning(f"Attempt to merge dict {dest} with non-dict {src}")
        return src

    if isinstance(dest, abc.Iterable):
        if isinstance(src, abc.Iterable):
          x_len = len(dest)
          y_len = len(src)
          for i, v in enumerate(dest):
              if i < y_len:
                  dest[i] = deepmerge_with_lists_pair(dest[i], src[i])
              else:
                  break

          i = x_len
          while i < y_len:
              dest.append(src[i])
              i += 1
        else:
            logger.warning(f"Attempt to merge iterable {dest} with non-iterable {src}")
            return src

    return src


def deepmerge_with_lists(*args) -> Any:
    """
    Deep merge, including dict elements of lists.
    The first argument is modified in place.
    """
    dest = None

    for i, src in enumerate(args):
        if i == 0:
            dest = src
        else:
            dest = deepmerge_with_lists_pair(dest, src)

    return dest
