# [[file:README.org::*Prep][Prep:1]]
import os
import shutil
import logging

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

# [[file:README.org::*For each batch][For each batch:1]]
def process_batches(batches):
  for rows in batches:
    identifiers_uris = get_uris_for_batch(rows)
    identifier_populations = find_population_facts(identifiers_uris)
    write_to_output(rows, identifier_populations)
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

def find_population_facts(identifiers_uris):
  sparql = SPARQLWrapper("http://dbpedia.org/sparql")
  formatted_uris = (f'<{uri}>' for _, uri in identifiers_uris if uri)
  sparql.setQuery(f"""
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
  """)
  sparql.setReturnFormat(JSON)
  response = sparql.query().convert()
  bindings = response['results']['bindings']

  for identifier, uri in identifier_uris:
    population = next(
      (r.get('population', {}).get('value', None)
       for r in bindings
       if r.get('resource', {}).get('value', None) == uri
       ), None)
    if population is not None:
      yield identifier, int(population)
# Search for population facts on all URIs:1 ends here

# [[file:README.org::*Append output CSV][Append output CSV:1]]
def write_to_output(rows, identifier_populations):
    with open('./output/with_populations.csv', 'a') as output_file:
        output = csv.writer(output_file)
        for identifier, *others in rows:
            population = next((p for idnt, p in identifier_populations if idnt == identifier),
                              None)
            output.writerow([identifier, *others, population])
# Append output CSV:1 ends here
