"""Intentional HDS modelling choices; update these when those choices change.

These assertions are separate from instance validation. They allow additional
domains and metadata while guarding the relationships deliberately kept/removed.
"""

from pathlib import Path
import unittest

from rdflib import Graph, Namespace, RDF, RDFS
from rdflib.namespace import DCTERMS, SH, SKOS

ROOT = Path(__file__).resolve().parents[1]
H = Namespace('https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/hds-cdm.ttl#')
DCAT = Namespace('http://www.w3.org/ns/dcat#')
DPV = Namespace('https://w3id.org/dpv#')
ODRL = Namespace('http://www.w3.org/ns/odrl/2/')
SCHEMA = Namespace('http://schema.org/')


class ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = Graph().parse(ROOT / 'hds-cdm.ttl')
        cls.shapes = Graph().parse(ROOT / 'hds-cdm-shapes.ttl')

    def paths_for(self, kind):
        """Follow reusable sh:node constraints without relying on shape names."""
        pending = list(self.shapes.subjects(SH.targetClass, kind))
        seen, paths = set(), set()
        while pending:
            shape = pending.pop()
            if shape in seen:
                continue
            seen.add(shape)
            paths.update(self.shapes.value(p, SH.path)
                         for p in self.shapes.objects(shape, SH.property))
            pending.extend(self.shapes.objects(shape, SH.node))
        return paths

    def test_ontology_contains_no_shacl(self):
        self.assertFalse(any(str(p).startswith(str(SH)) for _, p, _ in self.ontology))
        self.assertFalse(any(self.ontology.subjects(RDF.type, SH.NodeShape)))
        self.assertFalse(any(self.ontology.subjects(RDF.type, SH.PropertyShape)))

    def test_core_domains_remain_available_but_extensions_are_allowed(self):
        core = {H.environmental, H.humanTrafficking, H.humanitarian, H.humanRightsAbuse,
                H.migration, H.military, H.political, H.sexualViolence}
        concepts = set(self.ontology.subjects(SKOS.inScheme, H.incidentDomainScheme))
        top = set(self.ontology.objects(H.incidentDomainScheme, SKOS.hasTopConcept))
        self.assertTrue(core <= concepts)
        self.assertTrue(core <= top)
        self.assertTrue(top <= concepts)
        self.assertIn((H.incidentDomain, RDFS.seeAlso, H.incidentDomainScheme), self.ontology)
        legacy = 'https://vodan-development.github.io/HDS-Centralized-Common-Data-Model/incident-domains.ttl#'
        self.assertFalse(any(str(t).startswith(legacy) for triple in self.ontology for t in triple))

    def test_location_domain_links(self):
        expected = {(H.MigrationRoute, H.humanTrafficking), (H.MigrationRoute, H.migration),
                    (H.Camp, H.humanRightsAbuse), (H.Camp, H.humanitarian)}
        actual = {(s, o) for s, o in self.ontology.subject_objects(SCHEMA.location)
                  if s in (H.Camp, H.MigrationRoute)}
        self.assertTrue(expected <= actual)
        for kind in (H.Camp, H.MigrationRoute):
            self.assertNotIn((kind, RDFS.subClassOf, DCTERMS.Location), self.ontology)

    def test_metadata_and_consent_boundaries(self):
        for kind in (DCAT.Catalog, DCAT.Dataset):
            self.assertIn(DCTERMS.license, self.paths_for(kind))
        self.assertNotIn(DCTERMS.license, self.paths_for(DCAT.Distribution))
        consent = self.paths_for(DPV.Consent)
        self.assertTrue({DCTERMS.accessRights, DPV.hasPurpose, DCTERMS.publisher, ODRL.assignee} <= consent)
        self.assertNotIn(DCTERMS.license, consent)
        self.assertNotIn(DCTERMS.subject, self.paths_for(H.Report))

    def test_retired_terms_have_not_been_reintroduced(self):
        removed = {DCAT.DataService, DCAT.service, DCAT.accessService, DCAT.servesDataset,
                   DCAT.endpointURL, DCAT.contactPoint, H.hasDataOwner, H.hasDataUser,
                   H.hasRestriction, H.applicableLocationType}
        for graph in (self.ontology, self.shapes):
            self.assertFalse(any(t in removed or str(t).startswith('http://www.w3.org/2006/vcard/ns#')
                                 for triple in graph for t in triple))
        odrl = {t for graph in (self.ontology, self.shapes) for triple in graph
                for t in triple if str(t).startswith(str(ODRL))}
        self.assertEqual(odrl, {ODRL.assignee})
