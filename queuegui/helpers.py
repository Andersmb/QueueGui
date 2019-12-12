import os


def modulo_generator(length=3000, mod=3):
    """
    Return a generator yielding modulo values

    :param length: Int, total number of iterations
    :param mod: Int, frequency of "resetting" the counter

    :return: Int, next value in modulo loop
    """
    def reduce_index(length):
        if length < mod:
            return length
        else:
            return reduce_index(length-mod)

    for element in [reduce_index(i) for i in range(length)]:
        yield element


def joinpath(*args):
    return "/".join(args)


def remote_stem(path):
    return path.split("/")[-1]


def splitjoin(s, jd=None, sd=None):
    """

    :param s: string to be formatted
    :param jd: delimiter for joining strings
    :param sd: delimited for splitting string
    :return:
    """
    if not isinstance(s, str):
        raise Exception("You must pass a string to this function")

    if jd is None and sd is None:
        return ' '.join(s.split())
    elif sd is None and jd is not None:
        return jd.join(s.split())
    elif sd is not None and jd is None:
        return ' '.join(s.split(sd))
    else:
        return jd.join(s.split(sd))


def remote_join(*args):
    """
    Join strings by a forward-slash. Useful when a MS Windows user wants to open remote files
    :param args: list of strings to join
    :return:
    """
    return "/".join(args)


def purify_path(path):
    """
    Split a path by forward-slashes, and then os.path.join together again to get correct sep for the OS
    :param path: string
    :return:
    """
    first = path.split("/")[1]
    rest = path.split("/")[2:]
    return os.path.join("/"+first, *rest)