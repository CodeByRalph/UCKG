from rdflib import Graph

def extract_triples(file_path):
    g = Graph()
    g.parse(file_path, format="ttl")  # Assuming the file format is Turtle

    for subj, pred, obj in g:
        print(f"Subject: {subj}, Predicate: {pred}, Object: {obj}")

if __name__ == "__main__":
    file_path = "path/to/your/uco_with_instances.ttl"  # Update with the correct path
    extract_triples(file_path)