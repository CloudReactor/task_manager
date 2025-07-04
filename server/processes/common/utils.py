from typing import Any, Mapping, Optional
from collections import abc
import logging
import re


logger = logging.getLogger(__name__)


def val_to_str(x: Optional[Any], default: str = "-1") -> str:
    return default if (x is None) else str(x)


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


def deepmerge_with_lists_pair(dest: Any, src: Any,
        append_lists: bool=False, ignore_none: bool=True) -> Any:
    if isinstance(dest, str): # because string is iterable
        if src is None:
            return dest
        else:
            return src

    if isinstance(dest, abc.MutableMapping):
        if (not isinstance(src, str)) and isinstance(src, abc.Mapping):
            for k, v in src.items():
                if k in dest:
                    dest[k] = deepmerge_with_lists_pair(dest[k], v,
                            append_lists=append_lists, ignore_none=ignore_none)
                else:
                    dest[k] = v

            return dest

        logger.warning(f"Attempt to merge dict {dest} with non-dict {src}")
        return src

    if append_lists and isinstance(dest, abc.MutableSequence):
        if isinstance(src, abc.Sequence):
            x_len = len(dest)
            y_len = len(src)
            for i, v in enumerate(dest):
                if i < y_len:
                    dest[i] = deepmerge_with_lists_pair(dest[i], src[i],
                            append_lists=append_lists)
                else:
                    break

            i = x_len
            while i < y_len:
                dest.append(src[i])
                i += 1
        else:
            logger.warning(f"Attempt to merge iterable {dest} with non-iterable {src}")
            return src

    if ignore_none and (src is None):
        return dest

    return src


def deepmerge_core(append_lists: bool, ignore_none: bool, *args) -> Any:
    """
    Deep merge, including dict elements of lists.
    The third argument is modified in place.
    """
    dest = None

    for i, src in enumerate(args):
        if i == 0:
            dest = src
        else:
            dest = deepmerge_with_lists_pair(dest, src,
                    append_lists=append_lists, ignore_none=ignore_none)

    return dest


def deepmerge_with_lists(*args) -> Any:
    """
    Deep merge, including dict elements of lists.
    The first argument is modified in place.
    """
    return deepmerge_core(True, True, *args)


def deepmerge(*args, append_lists: bool=False, ignore_none: bool=True) -> Any:
    """
    Deep merge, overwriting lists.
    The first argument is modified in place.
    """
    return deepmerge_core(append_lists, ignore_none, *args)


def lookup_string(d: Mapping[str, Any], key: str) -> Optional[str]:
    x = d.get(key)
    return str(x) if x else None


def lookup_int(d: Mapping[str, Any], key: str) -> Optional[int]:
    x = d.get(key)
    return None if (not x) and (x != 0) else int(x)


def lookup_bool(d: Mapping[str, Any], key: str) -> Optional[bool]:
    x = d.get(key)
    return None if x is None else bool(x)


def to_camel(string: str) -> str:
    string_split = string.split("_")
    return string_split[0] + "".join(word.capitalize() for word in string_split[1:])


def strip_prefix_before_last_dot(text):
  """
  Strips the prefix of a string up to and including the last '.' character.

  Args:
    text: The input string.

  Returns:
    The substring after the last '.', or the original string if no '.' is found.
  """
  parts = text.rsplit('.', 1)
  if len(parts) > 1:
    return parts[1]
  else:
    return parts[0] # No dot found, return the original string
  