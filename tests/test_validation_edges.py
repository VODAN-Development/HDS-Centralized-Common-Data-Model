"""Validation edge cases and supported extensions, without fixed graph sizes."""

from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS
from rdflib.namespace import DCTERMS, SH, SKOS, XSD

ROOT = Path(__file__).resolve().parents[1]
H = Namespace('https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/hds-cdm.ttl#')
E = Namespace('https://example.org/')
DCAT = Namespace('http://www.w3.org/ns/dcat#')
SCHEMA = Namespace('http://schema.org/')
PROV = Namespace('http://www.w3.org/ns/prov#')


class ValidationEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = Graph().parse(ROOT / 'hds-cdm.ttl')
        cls.shapes = Graph().parse(ROOT / 'hds-cdm-shapes.ttl')

    def data(self, kind=H.Incident):
        graph = self.ontology + Graph()
        graph.add((E.item, RDF.type, kind))
        return graph

    def check(self, graph, expected, focus=None, path=None):
        conforms, report, text = validate(graph, shacl_graph=self.shapes)
        self.assertEqual(conforms, expected, text)
        if not expected and focus is not None:
            results = list(report.subjects(SH.focusNode, focus))
            self.assertTrue(results, text)
            if path is not None:
                self.assertTrue(any((r, SH.resultPath, path) in report for r in results), text)

    def add_domain(self, graph, term=E.additionalDomain):
        graph.add((term, RDF.type, SKOS.Concept))
        graph.add((term, SKOS.prefLabel, Literal('Additional domain', lang='en')))
        graph.add((term, SKOS.inScheme, H.incidentDomainScheme))
        return term

    def test_additional_domains_translations_and_optional_descriptions(self):
        graph = self.data()
        concept = self.add_domain(graph)
        graph.add((concept, SKOS.prefLabel, Literal('Extra domein', lang='nl')))
        graph.add((E.item, H.incidentDomain, concept))
        self.check(graph, True)  # No description and no hasTopConcept link required.
        graph.add((H.incidentDomainScheme, SKOS.hasTopConcept, concept))
        self.check(graph, True)

    def test_concept_label_required_language_tag_and_unique_language(self):
        for labels, expected in (([], False), ([Literal('Plain label')], False),
                                 ([Literal('One', lang='en'), Literal('Two', lang='en')], False),
                                 ([Literal('One', lang='en'), Literal('Een', lang='nl')], True)):
            with self.subTest(labels=labels):
                graph = self.data()
                concept = self.add_domain(graph)
                graph.remove((concept, SKOS.prefLabel, None))
                for label in labels:
                    graph.add((concept, SKOS.prefLabel, label))
                self.check(graph, expected, concept if not expected else None, SKOS.prefLabel)

    def test_descriptions_optional_but_language_tagged_and_unique(self):
        for term in (H.incidentDomainScheme, H.military):
            for values, expected in (([], True), ([Literal('Plain text')], False),
                                     ([Literal('One', lang='en'), Literal('Two', lang='en')], False),
                                     ([Literal('One', lang='en'), Literal('Een', lang='nl')], True)):
                with self.subTest(term=term, values=values):
                    graph = self.data()
                    graph.remove((term, DCTERMS.description, None))
                    for value in values:
                        graph.add((term, DCTERMS.description, value))
                    self.check(graph, expected, term if not expected else None, DCTERMS.description)

    def test_scheme_title_type_and_top_concepts_are_validated(self):
        mutations = ((H.incidentDomainScheme, RDF.type, SKOS.ConceptScheme),
                     (H.incidentDomainScheme, DCTERMS.title, None),
                     (H.incidentDomainScheme, SKOS.hasTopConcept, None))
        for triple in mutations:
            with self.subTest(removed=triple):
                graph = self.data()
                graph.remove(triple)
                self.check(graph, False, H.incidentDomainScheme)
        graph = self.data()
        graph.add((H.incidentDomainScheme, DCTERMS.title, Literal('Another title', lang='en')))
        self.check(graph, False, H.incidentDomainScheme, DCTERMS.title)

    def test_incident_domain_must_be_iri_typed_concept_in_the_scheme(self):
        for value, typed, member, expected in ((E.domain, True, True, True),
                                              (E.domain, False, True, False),
                                              (E.domain, True, False, False),
                                              (BNode(), True, True, False),
                                              (Literal('military'), False, False, False)):
            with self.subTest(value=value, typed=typed, member=member):
                graph = self.data()
                graph.add((E.item, H.incidentDomain, value))
                if typed:
                    graph.add((value, RDF.type, SKOS.Concept))
                    graph.add((value, SKOS.prefLabel, Literal('Domain', lang='en')))
                if member:
                    graph.add((value, SKOS.inScheme, H.incidentDomainScheme))
                if typed and not member:
                    self.check(graph, False, value, SKOS.inScheme)
                else:
                    self.check(graph, expected, E.item if not expected else None, H.incidentDomain)

    def test_in_scheme_has_value_is_not_exactly_one(self):
        graph = self.data()
        graph.add((H.military, SKOS.inScheme, E.otherScheme))
        self.check(graph, True)  # Required membership remains; another is allowed.
        graph.remove((H.military, SKOS.inScheme, H.incidentDomainScheme))
        self.check(graph, False, H.military, SKOS.inScheme)

    def test_class_level_location_links_validate_concept_values(self):
        for kind in (H.Camp, H.MigrationRoute):
            for value in (Literal('migration'), E.undeclaredConcept, E.location):
                with self.subTest(kind=kind, value=value):
                    graph = self.data()
                    graph.add((E.location, RDF.type, DCTERMS.Location))
                    graph.add((kind, SCHEMA.location, value))
                    self.check(graph, False, kind, SCHEMA.location)
            graph = self.data()
            concept = self.add_domain(graph)
            graph.add((kind, SCHEMA.location, concept))
            self.check(graph, True)

    def test_text_fields_accept_plain_and_language_tagged_literals_only(self):
        fields = ((H.Incident, DCTERMS.description), (H.Incident, RDFS.label),
                  (H.Report, DCTERMS.title), (PROV.Agent, RDFS.label))
        for kind, prop in fields:
            for value, expected in ((Literal('Text'), True), (Literal('Tekst', lang='nl'), True),
                                    (Literal(42), False), (E.textResource, False)):
                with self.subTest(kind=kind, prop=prop, value=value):
                    graph = self.data(kind)
                    graph.add((E.item, prop, value))
                    self.check(graph, expected, E.item if not expected else None, prop)

    def test_incident_and_resource_datatypes(self):
        cases = ((H.Incident, SCHEMA.startDate, Literal('2026-11-24T10:00:00Z', datatype=XSD.dateTime), Literal('2026-11-24')),
                 (H.Incident, SCHEMA.endDate, Literal('2026-11-24T11:00:00Z', datatype=XSD.dateTime), Literal(42)),
                 (H.Incident, H.victimCount, Literal(3), Literal('3')),
                 (H.Incident, H.confidentiality, Literal('restricted'), Literal(1)),
                 (H.Incident, H.status, Literal('open'), Literal(True)),
                 (PROV.Agent, H.actorType, Literal('data owner'), E.actorType),
                 (H.Report, PROV.generatedAtTime, Literal('2026-11-24T10:00:00Z', datatype=XSD.dateTime), Literal('today')),
                 (H.Report, SCHEMA.identifier, Literal('https://example.org/report', datatype=XSD.anyURI), E.report),
                 (H.Report, DCTERMS.identifier, Literal('report-1'), Literal(1)))
        for kind, prop, good, bad in cases:
            with self.subTest(kind=kind, prop=prop):
                graph = self.data(kind)
                graph.add((E.item, prop, good))
                self.check(graph, True)
                graph.set((E.item, prop, bad))
                self.check(graph, False, E.item, prop)

    def test_catalogue_version_and_iri_fields(self):
        for kind in (DCAT.Catalog, DCAT.Dataset):
            for prop in (DCTERMS.conformsTo, DCTERMS.language):
                graph = self.data(kind)
                graph.add((E.item, prop, E.value))
                self.check(graph, True)
                graph.set((E.item, prop, Literal('value')))
                self.check(graph, False, E.item, prop)
            for prop, good, bad in ((DCAT.version, Literal('1.0'), E.version),
                                    (DCTERMS.hasVersion, E.version, Literal('1.0'))):
                graph = self.data(kind)
                graph.add((E.item, prop, good))
                self.check(graph, True)
                graph.set((E.item, prop, bad))
                self.check(graph, False, E.item, prop)

    def test_dataset_containment_and_distribution_classes(self):
        for kind, prop, value_type in ((H.Incident, DCTERMS.isPartOf, DCAT.Dataset),
                                       (H.Incident, DCTERMS.isPartOf, H.Report),
                                       (DCAT.Dataset, DCTERMS.isPartOf, DCAT.Catalog),
                                       (DCAT.Dataset, DCAT.distribution, DCAT.Distribution)):
            with self.subTest(kind=kind, prop=prop, value_type=value_type):
                graph = self.data(kind)
                graph.add((E.item, prop, E.target))
                graph.add((E.target, RDF.type, value_type))
                self.check(graph, True)
                graph.remove((E.target, RDF.type, value_type))
                self.check(graph, False, E.item, prop)

    def test_removed_constraints_do_not_make_open_shapes_prohibitions(self):
        for kind, prop in ((DCAT.Distribution, DCTERMS.license), (H.Report, DCTERMS.subject)):
            graph = self.data(kind)
            graph.add((E.item, prop, Literal('Unconstrained extension')))
            self.check(graph, True)
