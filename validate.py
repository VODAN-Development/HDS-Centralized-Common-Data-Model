"""Validate the HDS vocabulary and, optionally, a Turtle instance-data file."""

import argparse
from pathlib import Path

from pyshacl import validate
from rdflib import Graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", nargs="?", type=Path, help="Optional Turtle instance data")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    ontology = Graph().parse(root / "hds-cdm.ttl", format="turtle")
    vocabulary = Graph().parse(root / "incident-domains.ttl", format="turtle")
    vocabulary_shapes = Graph().parse(root / "incident-domains-shapes.ttl", format="turtle")
    conforms, _, report = validate(
        ontology + vocabulary, shacl_graph=vocabulary_shapes, meta_shacl=True
    )
    print("Vocabulary:")
    print(report)
    if not conforms:
        return 1
    # Meta-validate instance shapes even when no instance data was supplied.
    data = ontology + vocabulary
    if args.data:
        data.parse(args.data, format="turtle")
    shapes = Graph().parse(root / "hds-cdm-shapes.ttl", format="turtle")
    conforms, _, report = validate(data, shacl_graph=shapes, meta_shacl=True)
    print("Instance data:" if args.data else "CDM shapes and reference data:")
    print(report)
    return 0 if conforms else 1


if __name__ == "__main__":
    raise SystemExit(main())
