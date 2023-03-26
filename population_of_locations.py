# [[file:README.org::*Prep][Prep:1]]
import os
import logging
import sys

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Prep:1 ends here

# [[file:README.org::*Prep][Prep:2]]
import shutil

def reset_output_dir(output_dir="output"):
  if os.path.exists(output_dir):
      shutil.rmtree(output_dir)
  os.makedirs(output_dir)
  logging.debug("Output directory %s reset", output_dir)
# Prep:2 ends here

# [[file:README.org::*Read in Input][Read in Input:2]]
import requests
import csv
from itertools import islice

def get_csv_input_batches(input_filename='./minimal-sample-input.csv', batch_size=100, skip=0, take=None):
    csv_read_done = object()
    with open(input_filename, 'r') as input_file:
        csv_line = csv.reader(input_file)
        try:
            for _ in range(skip):
                next(csv_line)
        except StopIteration:
            return
        number_processed = 0
        while True:
            res = []
            for _ in range(batch_size):
                try:
                    res.append(next(csv_line))
                    number_processed += 1
                    if take is not None and number_processed >= take:
                        yield res
                        return
                except StopIteration:
                    yield res
                    return
            yield res
# Read in Input:2 ends here

# [[file:README.org::*For each batch][For each batch:1]]
def process_batches(batches, output_file=None):
  for rows in batches:
    logging.debug('Handling batch of %s rows', len(rows))
    identifiers_uris = get_uris_for_batch(rows)
    identifier_populations = find_population_facts(identifiers_uris)
    write_to_output(rows, identifier_populations, output_file=output_file)
# For each batch:1 ends here

# [[file:README.org::*For each row][For each row:1]]
def get_uris_for_batch(rows):
  for identifier, state_code, name, city_county in rows:
    found_results = search_for_term(f"{name}, {state_code}")
    uri = best_matching_uri(found_results, city_county, identifier)
    if not uri is None:
      yield identifier, uri
# For each row:1 ends here

# [[file:README.org::*Search for possible URIs][Search for possible URIs:1]]
import requests
from xml.etree import ElementTree 

def search_for_term(term):
  url = f"https://lookup.dbpedia.org/api/search?query={term}&maxResults=5"
  response = requests.get(url)
  return ElementTree.fromstring(response.content)
# Search for possible URIs:1 ends here

# [[file:README.org::*Identify best matching URI][Identify best matching URI:1]]
def best_matching_uri(tree, city_county, identifier):
    if city_county == "City":
        search_class_uri = ("http://dbpedia.org/ontology/City",)
    elif city_county == "County":
        search_class_uri = ("http://dbpedia.org/ontology/Region", "http://dbpedia.org/ontology/AdministrativeRegion")
    else:
        logging.error("Unknown city or county %s", city_county)
        return None

    for result in tree.findall("Result"):
        classes = result.find("Classes")
        for class_element in classes.findall("Class"):
            if class_element.find("URI").text in search_class_uri:
                return result.find("URI").text

    logging.error("No appropriate uri for %s found. Searched %s", identifier, ElementTree.tostring(tree,encoding='unicode'))
    return None
# Identify best matching URI:1 ends here

# [[file:README.org::*Search for population facts on all URIs][Search for population facts on all URIs:1]]
from SPARQLWrapper import SPARQLWrapper, JSON

def find_population_facts(identifiers_uris_collection):
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  identifiers_uris = list(identifiers_uris_collection)
  formatted_uris = (f'<{uri}>' for _, uri in identifiers_uris if uri)
  query = f"""
      PREFIX dbo: <http://dbpedia.org/ontology/>
      PREFIX dbp: <http://dbpedia.org/property/>

      SELECT ?resource ?population WHERE {{
          VALUES ?resource {{ {' '.join(formatted_uris)} }}
          {{
              ?resource dbo:populationTotal ?population .
          }} UNION {{
              ?resource dbp:populationTotal ?population .
          }}
      }}
  """
  sparql.setQuery(query)
  sparql.setReturnFormat(JSON)
  logging.debug("Using SPARQL query %s", query)
  response = sparql.query().convert()
  bindings = response['results']['bindings']

  for identifier, uri in identifiers_uris:
    population = next(
      (r.get('population', {}).get('value', None)
       for r in bindings
       if r.get('resource', {}).get('value', None) == uri
       ), None)
    if population is not None:
      yield identifier, int(population)
    else:
      logging.debug('Failed to resolve population for %s', identifier)
# Search for population facts on all URIs:1 ends here

# [[file:README.org::*Append output CSV][Append output CSV:1]]
from collections import defaultdict
default_output_file = './output/with_populations.csv'
def write_to_output(rows, identifier_populations_collection, output_file=default_output_file):
    output_file = output_file or default_output_file

    identifier_populations = {}
    for identifier, population in identifier_populations_collection:
        if identifier not in identifier_populations:
          identifier_populations[identifier] = population
    logging.debug('Writing populations: %s', identifier_populations)

    num_resolved = defaultdict(lambda: 0)
    with open(output_file, 'a') as output_file:
        output = csv.writer(output_file)
        for identifier, *others in rows:
            population = identifier_populations.get(identifier, None)
            num_resolved[population is not None] += 1
            output.writerow([identifier, *others, population])
    logging.info("Resolved population for %s locations, failed to resolve for %s", num_resolved[True], num_resolved[False])
# Append output CSV:1 ends here

# [[file:README.org::*Launcher][Launcher:1]]
import argparse

parser = argparse.ArgumentParser(description="Process location populations")
parser.add_argument("--batch-size", type=int, default=50, help="Number of location populations to resolve at a time")
parser.add_argument("--input-file", type=str, default="./minimal-sample-input.csv", help="Path to input CSV file")
parser.add_argument("--output-file", type=str, default="./output/with_population.csv", help="Path to write output CSV file")
parser.add_argument("--skip", type=int, default=0, help="Number of rows to skip in the input CSV file")
parser.add_argument("--take", type=int, default=None, help="Number of rows to process in the input CSV file")
parser.add_argument("--reset-output", type=bool, default=True, help="Reset the output directory by deleting contents and recreating")

if __name__ == '__main__': 
  args = parser.parse_args()
  logging.debug('Start processing')

  if args.reset_output:
    reset_output_dir()

  batches = get_csv_input_batches(input_filename=args.input_file,
                                  batch_size=args.batch_size,
                                  skip=args.skip,
                                  take=args.take,)
  process_batches(batches, output_file=args.output_file)
# Launcher:1 ends here
