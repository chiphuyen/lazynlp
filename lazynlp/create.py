import os
import random
import shutil

from pybloom import BloomFilter

from .analytics import *
from .utils import *


def create_gutenberg():
    pass


def create_reddit_data():
    pass


def create_wikipedia():
    pass


def filter_files(files,
                 threshold=0.5,
                 gran='word',
                 n=8,
                 capacity=100000000,
                 error_rate=1e-7,
                 header=0,
                 interval=1000000):
    """ Include only files that has less than threshold n-gram overlapping
        with the current dataset.
    Names of all the files that are deemed duplicated are stored in
        dupped_files.list
    Names of all the files used for the dataset are stored in
        clean_files.list

    Args:
        header (int):
            number of lines of each file to skip. It's because in our format,
            the first line is the url

    """
    sorted_files = sort_files_by_size(files)
    bf = BloomFilter(capacity=capacity, error_rate=error_rate)
    dupped_files = open('dupped_files.list', 'w')
    clean_files = open('clean_files.list', 'w')

    dup_count = 0

    for size, file in sorted_files:
        overlap = estimate_overlap_bf(bf, file, gran=gran, n=n, header=header)
        if overlap > threshold:
            print("Dup", file)
            dupped_files.write(file.strip() + '\n')
            dup_count += 1
        else:
            bf = build_ngram(file=file,
                             bf=bf,
                             gran=gran,
                             n=n,
                             uncase=True,
                             alphanumeric=True,
                             interval=interval)
            clean_files.write(file.strip() + '\n')
    total = len(files)
    print(f'{dup_count} duplicated out of {total}: {dup_count / total}')


def partition(file, outfold, test_size=0.1, valid_size=0.1):
    """
    outfold will contain:
    train.txt
    valid.txt
    test.txt

    You can choose not to include test or valid by setting its size to -1
    If the size is a fraction of 1, it'll be divided based on that ration.
    If it's an integer larger than 1, test/valid will contain that number of samples
    """
    os.makedirs(outfold, exist_ok=True)
    files = [open(f'{outfold}/{filename}', 'w')
             for filename in ['train.txt', 'valid.txt', 'test.txt']]
    adjusted_test_size = test_size / (1 - valid_size)
    with open(file, 'r') as f:
        for line in f.readlines():
            if not line.strip():
                continue
            if random.random() < valid_size:
                files[1].write(line)
            elif random.random() < adjusted_test_size:
                files[2].write(line)
            else:
                files[0].write(line)
