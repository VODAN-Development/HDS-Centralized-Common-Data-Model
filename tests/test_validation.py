"""Behavioral regression tests for the local HDS application profile."""

from pathlib import Path
import unittest

from pyshacl import validate
from rdflib import BNode, Graph, Literal, Namespace, RDF
from rdflib.namespace import DCTERMS, OWL

ROOT = Path(__file__).resolve().parents[1]
H = Namespace("https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/hds-cdm.ttl#")
E = Namespace("https://example.org/")
DPV = Namespace("https://w3id.org/dpv#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
SCHEMA = Namespace("http://schema.org/")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
PROV = Namespace("http://www.w3.org/ns/prov#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


class ValidationBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = Graph().parse(ROOT / "hds-cdm.ttl")
        cls.shapes = Graph().parse(ROOT / "hds-cdm-shapes.ttl")

    def data(self, kind=H.Incident):
        graph = self.ontology + Graph()
        graph.add((E.item, RDF.type, kind))
        return graph

    def conforms(self, graph):
        return validate(graph, shacl_graph=self.shapes)[0]

    def test_ontology_and_shapes_conform(self):
        self.assertTrue(validate(self.ontology, shacl_graph=self.shapes, meta_shacl=True)[0])

    def test_field_types_independent_of_domain(self):
        for domain in (None, H.environmental, H.military, H.political):
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
        graph.add((E.item, H.incidentDomain, H.military))
        graph.add((E.item, H.incidentDomain, H.environmental))
        graph.add((E.item, E.extension, Literal("Allowed")))
        self.assertTrue(self.conforms(graph))

    def test_location_types_and_reports(self):
        for kind in (H.Camp, H.MigrationRoute):
            with self.subTest(location_shape=kind):
                graph = self.data(kind)
                self.assertTrue(self.conforms(graph))
                graph.add((E.item, SCHEMA.location, E.place))
                self.assertFalse(self.conforms(graph))
                graph.add((E.place, RDF.type, DCTERMS.Location))
                self.assertTrue(self.conforms(graph))
                graph.add((E.item, SCHEMA.location, E.otherPlace))
                graph.add((E.otherPlace, RDF.type, DCTERMS.Location))
                self.assertTrue(self.conforms(graph))
                graph.set((E.item, SCHEMA.location, Literal("A place")))
                self.assertFalse(self.conforms(graph))
        for kind in (DCTERMS.Location, H.Camp, H.MigrationRoute):
            graph = self.data()
            graph.add((E.item, SCHEMA.location, E.place))
            graph.add((E.place, RDF.type, kind))
            self.assertEqual(self.conforms(graph), kind == DCTERMS.Location)
        graph = self.data()
        graph.add((E.item, DCTERMS.isPartOf, E.report))
        graph.add((E.report, RDF.type, H.Report))
        self.assertTrue(self.conforms(graph))
        graph.remove((E.report, RDF.type, H.Report))
        self.assertFalse(self.conforms(graph))

    def test_locations_are_independent_of_domain(self):
        for domains in ((H.migration,), (H.humanTrafficking,), (H.humanitarian,),
                        (H.humanRightsAbuse,), (H.migration, H.humanitarian)):
            for location_type in (None, DCTERMS.Location):
                with self.subTest(domains=domains, location=location_type):
                    graph = self.data()
                    for domain in domains:
                        graph.add((E.item, H.incidentDomain, domain))
                    if location_type:
                        graph.add((E.item, SCHEMA.location, E.place))
                        graph.add((E.place, RDF.type, location_type))
                    self.assertTrue(self.conforms(graph))
        graph = self.data()
        graph.add((E.item, SCHEMA.location, E.untypedLocation))
        self.assertFalse(self.conforms(graph))
        graph = self.ontology + Graph().parse(ROOT / 'examples' / 'locations.ttl')
        self.assertTrue(self.conforms(graph))

    def test_governance_standard_purpose(self):
        example = self.ontology + Graph().parse(ROOT / 'examples' / 'consent.ttl')
        self.assertTrue(self.conforms(example))
        example.remove((E.agent, RDF.type, PROV.Agent))
        self.assertFalse(self.conforms(example))
        example.add((E.agent, RDF.type, DCTERMS.RightsStatement))
        self.assertFalse(self.conforms(example))
        graph = self.data(DPV.Consent)
        graph.add((E.item, DPV.hasPurpose, Literal("research")))
        self.assertFalse(self.conforms(graph))
        graph.set((E.item, DPV.hasPurpose, E.purpose))
        graph.add((E.purpose, RDF.type, DPV.Purpose))
        self.assertTrue(self.conforms(graph))

    def test_dataset_license(self):
        graph = self.data(DCAT.Dataset)
        graph.add((E.item, DCTERMS.license, E.license))
        graph.add((E.license, RDF.type, DCTERMS.RightsStatement))
        self.assertTrue(self.conforms(graph))
        graph.remove((E.license, RDF.type, DCTERMS.RightsStatement))
        self.assertFalse(self.conforms(graph))
        graph.add((E.license, RDF.type, DCTERMS.RightsStatement))
        graph.set((E.item, DCTERMS.license, Literal("restricted")))
        self.assertFalse(self.conforms(graph))

    def test_governance_party_and_publisher_values(self):
        for prop in (ODRL.assignee, DCTERMS.publisher):
            graph = self.data(DPV.Consent)
            graph.add((E.item, prop, Literal(2)))
            self.assertFalse(self.conforms(graph))
        graph = self.data(DPV.Consent)
        graph.add((E.item, ODRL.assignee, E.party))
        graph.add((E.party, RDF.type, PROV.Agent))
        self.assertTrue(self.conforms(graph))

    def test_prov_agents_required_for_all_roles(self):
        for subject_type, prop in ((H.Incident, H.involves), (H.Incident, H.reportedBy),
                                   (DPV.Consent, ODRL.assignee), (DPV.Consent, DCTERMS.accessRights)):
            for agent_type, expected in ((PROV.Agent, True), (E.OtherAgent, False),
                                          (SCHEMA.Person, False), (SCHEMA.Organization, False)):
                with self.subTest(role=prop, type=agent_type):
                    graph = self.data(subject_type)
                    graph.add((E.item, prop, E.agent))
                    graph.add((E.agent, RDF.type, agent_type))
                    graph.add((E.agent, FOAF.name, Literal("Example organisation")))
                    self.assertEqual(self.conforms(graph), expected)
        for subject_type in (DCAT.Dataset, DCAT.Catalog, DPV.Consent):
            for agent_type in (PROV.Agent, E.OtherAgent, SCHEMA.Person, SCHEMA.Organization):
                with self.subTest(publisher_of=subject_type, type=agent_type):
                    graph = self.data(subject_type)
                    graph.add((E.item, DCTERMS.publisher, E.agent))
                    graph.add((E.agent, RDF.type, agent_type))
                    graph.add((E.agent, FOAF.name, Literal("Example publisher", lang="en")))
                    self.assertEqual(self.conforms(graph), agent_type == PROV.Agent)
                    graph.set((E.agent, FOAF.name, Literal(42)))
                    self.assertFalse(self.conforms(graph))

    def test_applicable_property_declaration_and_iri(self):
        for value, declared, expected in ((Literal("casualties"), False, False),
                                          (E.field, False, False),
                                          (E.field, True, True),
                                          (BNode(), True, False)):
            graph = self.ontology + Graph()
            graph.add((H.military, H.applicableProperty, value))
            if declared:
                graph.add((value, RDF.type, OWL.DatatypeProperty))
            with self.subTest(value=value):
                self.assertEqual(validate(graph, shacl_graph=self.shapes)[0], expected)


if __name__ == "__main__":
    unittest.main()
