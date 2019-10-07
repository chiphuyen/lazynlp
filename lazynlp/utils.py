import hashlib
import os
import re


def dict_sorted_2_file(dictionary, file, reverse=True):
    with open(file, 'w') as out:
        sorted_keys = sorted(dictionary, key=dictionary.get, reverse=reverse)
        for k in sorted_keys:
            out.write('{}\t{}\n'.format(k, dictionary[k]))


def get_hash(txt):
    return hashlib.md5(txt.encode()).digest()


def is_initial(token):
    """
    It's an initial is it matches the pattern ([a-z].)*
    """
    return re.match(r"^([a-z]\.)+?$", token.lower()) is not None


def is_positive_number(string, neg=False):
    if not string:
        return False
    if string.isdigit():
        return True
    idx = string.find('.')
    if idx > -1 and idx < len(string) - 1:
        if idx == 0 and neg:
            return False
        new_string = string[:idx] + string[idx + 1:]
        if new_string.isdigit():
            return True
    rev = string[::-1]
    idx = rev.find(',')

    while idx > 0 and idx % 3 == 0 and rev[:idx].isdigit():
        rev = rev[idx + 1:]
        idx = rev.find(',')

    if idx == -1 and rev.isdigit():
        return True
    return False


def is_number(string):
    """ Return true if:
    integer
    float (both in 32.0323 and .230)
    numbers in the format 239,000,000
    negative number
    """
    if string and string[0] == '-':
        return is_positive_number(string[1:], True)
    return is_positive_number(string)


def get_english_alphabet():
    return set([chr(i) for i in range(ord('a'), ord('z') + 1)])


def sort_files_by_size(files):
    pairs = []
    for file in files:
        size = os.path.getsize(file)
        pairs.append((size, file))
    return sorted(pairs, reverse=True)


def get_filename(path):
    return path[path.rfind('/') + 1:]


def get_raw_url(url):
    """ without http, https, www
    """
    idx = url.rfind('//')
    if idx > -1:
        url = url[idx + 2:]
    if url.startswith('www'):
        url = url[url.find('.') + 1:]
    return url


def sort_lines(file, reverse=False):
    seen = set()
    with open(file, 'r') as f:
        lines = sorted(f.readlines())
    with open(file, 'w') as f:
        for line in lines:
            if line not in seen:
                seen.add(line)
                f.write(line)
