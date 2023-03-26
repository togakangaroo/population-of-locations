# [[file:README.org::*Prep][Prep:1]]
import os
import shutil

output_dir = "output"

if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir)
# Prep:1 ends here

# [[file:README.org::*Read in Input][Read in Input:2]]
import requests
import csv
from itertools import islice

def get_csv_input_batches(input_filename='./minimal-sample-input.csv', batch_size=100):
    csv_read_done = object()
    with open(input_filename, 'r') as input_file:
        csv_line = csv.reader(input_file)
        while True:
            res = []
            for _ in range(batch_size):
                try:
                    res.append(next(csv_line))
                except StopIteration:
                    yield res
                    return
            yield res
# Read in Input:2 ends here

# [[file:README.org::*Read in Input][Read in Input:4]]
[[['8', 'AK', 'North Slope', 'County'], ['14', 'AK', 'Juneau, City and Borough of', 'City'], ['9', 'AK', 'Northwest Arctic', 'County']], [['10', 'AK', 'Petersburg', 'County'], ['11', 'AK', 'Anchorage', 'City'], ['12', 'AK', 'Bethel', 'City']], [['13', 'AK', 'Fairbanks', 'City']]]
# Read in Input:4 ends here
