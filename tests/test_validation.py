"""Behavioral regression tests for the local HDS application profile."""

import importlib.util
from pathlib import Path
import sys
import unittest

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, OWL, SH, SKOS

ROOT = Path(__file__).resolve().parents[1]
H = Namespace("https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/hds-cdm.ttl#")
D = Namespace("https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/incident-domains.ttl#")
E = Namespace("https://example.org/")
DPV = Namespace("https://w3id.org/dpv#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SCHEMA = Namespace("http://schema.org/")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = Graph().parse(ROOT / "hds-cdm.ttl")
        cls.vocabulary = Graph().parse(ROOT / "incident-domains.ttl")
        cls.shapes = Graph().parse(ROOT / "hds-cdm-shapes.ttl")
        cls.vocabulary_shapes = Graph().parse(ROOT / "incident-domains-shapes.ttl")

    def data(self, kind=H.Incident):
        graph = self.ontology + self.vocabulary
        graph.add((E.item, RDF.type, kind))
        return graph

    def conforms(self, graph):
        return validate(graph, shacl_graph=self.shapes)[0]

    def test_meta_validation_and_separation(self):
        self.assertFalse(any(self.ontology.triples((None, RDF.type, SH.NodeShape))))
        self.assertFalse((H.Report, DCTERMS.isPartOf, H.Incident) in self.ontology)
        self.assertTrue(validate(self.data(), shacl_graph=self.shapes, meta_shacl=True)[0])
        self.assertTrue(validate(self.ontology + self.vocabulary,
                                 shacl_graph=self.vocabulary_shapes, meta_shacl=True)[0])

    def test_field_types_independent_of_domain(self):
        for domain in (None, D.environmental, D.military, D.political):
            for prop, good, bad in ((H.casualties, Literal(2), Literal("2")),
                                    (H.outcome, Literal("Resolved"), Literal(2)),
                                    (H.weaponsUsed, Literal("Small arms"), Literal(2))):
                with self.subTest(domain=domain, prop=prop):
                    graph = self.data()
                    if domain:
                        graph.add((E.item, H.incidentDomain, domain))
                    graph.add((E.item, prop, good))
                    self.assertTrue(self.conforms(graph))
                    graph.set((E.item, prop, bad))
                    self.assertFalse(self.conforms(graph))

    def test_optional_repeatable_open_profile(self):
        graph = self.data()
        self.assertTrue(self.conforms(graph))
        graph.add((E.item, H.incidentDomain, D.military))
        graph.add((E.item, H.incidentDomain, D.environmental))
        graph.add((E.item, E.extension, Literal("Allowed")))
        self.assertTrue(self.conforms(graph))

    def test_location_subclasses_and_reports(self):
        for kind in (DCTERMS.Location, H.Camp, H.MigrationRoute):
            graph = self.data()
            graph.add((E.item, SCHEMA.location, E.place))
            graph.add((E.place, RDF.type, kind))
            self.assertTrue(self.conforms(graph))
        graph = self.data(H.Report)
        graph.add((E.item, DCTERMS.subject, E.incident))
        graph.add((E.incident, RDF.type, H.Incident))
        self.assertTrue(self.conforms(graph))
        graph.remove((E.incident, RDF.type, H.Incident))
        self.assertFalse(self.conforms(graph))

    def test_governance_standard_purpose(self):
        graph = self.data(DPV.Consent)
        graph.add((E.item, DPV.hasPurpose, Literal("research")))
        self.assertFalse(self.conforms(graph))
        graph.set((E.item, DPV.hasPurpose, E.purpose))
        graph.add((E.purpose, RDF.type, DPV.Purpose))
        self.assertTrue(self.conforms(graph))

    def test_independent_rights_policy_and_restriction(self):
        graph = self.data(DCAT.Dataset)
        graph.add((E.item, DCTERMS.license, E.license))
        graph.add((E.item, DCTERMS.accessRights, E.access))
        graph.add((E.access, RDF.type, DCTERMS.RightsStatement))
        graph.add((E.item, ODRL.hasPolicy, E.policy))
        graph.add((E.policy, RDF.type, ODRL.Policy))
        graph.add((E.item, H.hasRestriction, E.nonDuoRestriction))
        self.assertTrue(self.conforms(graph))
        graph.set((E.item, H.hasRestriction, Literal("restricted")))
        self.assertFalse(self.conforms(graph))

    def test_governance_party_and_publisher_values(self):
        for prop in (ODRL.assignee, ODRL.assigner, DCTERMS.publisher, DCTERMS.accessRights):
            graph = self.data(DPV.Consent)
            graph.add((E.item, prop, Literal(2)))
            self.assertFalse(self.conforms(graph))
        graph = self.data(ODRL.Policy)
        graph.add((E.item, ODRL.assignee, E.party))
        graph.add((E.party, RDF.type, ODRL.Party))
        self.assertTrue(self.conforms(graph))

    def test_applicable_property_declaration_and_iri(self):
        for value, declared, expected in ((Literal("casualties"), False, False),
                                          (E.field, False, False),
                                          (E.field, True, True),
                                          (BNode(), True, False)):
            graph = self.ontology + self.vocabulary
            graph.add((D.military, H.applicableProperty, value))
            if declared:
                graph.add((value, RDF.type, OWL.DatatypeProperty))
            with self.subTest(value=value):
                self.assertEqual(validate(graph, shacl_graph=self.vocabulary_shapes)[0], expected)


if __name__ == "__main__":
    unittest.main()
