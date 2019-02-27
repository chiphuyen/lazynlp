import os
import shutil

from pybloom import BloomFilter

from lazynlp.analytics import *
from lazynlp.utils import *

def create_gutenberg():
	pass

def create_reddit_data():
	pass

def create_wikipedia():
	pass

def filter_files(files, threshold=0.5, gran='word', n=8, capacity=100000000, error_rate=1e-7, header=0, interval=1000000):
	""" Include only files that has less than threshold n-gram overlapping with the current dataset
	Names of all the files that are deemed duplicated are stored in dupped_files.list
	Names of all the files used for the dataset are stored in clean_files.list
	header: number of lines of each file to skip. It's because in our format, the first line is the url
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
			bf = build_ngram(file=file, bf=bf, gran=gran, n=n, uncase=True, alphanumeric=True, interval=interval)
			clean_files.write(file.strip() + '\n')
	total = len(files)
	print('{} duplicated out of {}: {}'.format(dup_count, total, dup_count/total))