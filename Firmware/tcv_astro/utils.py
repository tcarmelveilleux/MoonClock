def package_relpath(module_path: str, filename: str):
    """Given the __file__ of a module's path and a filename in same directory, return usable path.

    This is for accessing data files within a package/module, without using os.path,
    which neither CircuitPython or MicroPython have.

    Done so that it works both with `/` and `\\` separators portably.
    """
    for sep in ['/', '\\']:
        last_sep_idx = module_path.rfind(sep)
        if last_sep_idx != -1:
            return module_path[:last_sep_idx] + sep + filename

    return filename