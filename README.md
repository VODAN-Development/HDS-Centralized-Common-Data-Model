# HDS-Centralized-Common-Data-Model
CDM used by HDS applications


## Centralised model

`hds-cdm.ttl` contains the HDS ontology. All SHACL validation lives in
`hds-cdm-shapes.ttl`.

## Incident domains

Incident records can be categorised by incident domains. The domain concepts in `hds-cdm.ttl` record additional fields using `hds:applicableProperty`:

| Domain | Additional incident properties |
| --- | --- |
| Military | `hds:weaponsUsed`, `hds:casualties` |
| Human rights abuse | `hds:casualties` |
| Humanitarian | `hds:casualties` |
| Human trafficking | `hds:casualties` |
| Migration | `hds:casualties` |
| Political | `hds:outcome` |
| Environmental | No additional field listed |
| Sexual violence | No additional field listed |

These are property references, as the actual properties are recorded under the `hds:Incident` class. When adding new properties related to incidents, add them to the `hds:Incident` class, then map the properties, if applicable, to any of the incident domains using `hds:applicableProperty`.

## Validate the incident-domain vocabulary

`hds-cdm.ttl` contains the domain vocabulary and property declarations.
`hds-cdm-shapes.ttl` provides the domain and instance validation shapes. It checks the
vocabulary: scheme type and title, top-concept consistency, concept IRIs and
types, scheme membership, and language-tagged preferred labels with at most
one label per language. Descriptions are optional language-tagged strings,
with at most one per language. Applicable-property links must identify declared
RDF or OWL properties. Additional domains and translations are allowed.


Install the validator and run from the repository root:

```powershell
python -m pip install -r requirements-validation.txt
python validate.py
```

The command also checks the shapes graph against SHACL's own shapes. Successful validation reports `Conforms: True`; violations produce a validation report and a nonzero exit code.

Vocabulary checks and incident-data constraints are both in
`hds-cdm-shapes.ttl`. When validating incident data with that file, include
`hds-cdm.ttl` in the data graph for concept type, scheme and class checks.

To validate the model and domain vocabulary directly:

```powershell
python -m pyshacl -s hds-cdm-shapes.ttl -m hds-cdm.ttl
```

## Validate CDM instance data

Created incident records can be checked against the SHACL shapes.
For example, from the repository root:

```powershell
python validate.py incidents.ttl
```

The equivalent instance-validation API call is:

```python
from rdflib import Graph
from pyshacl import validate

data = Graph().parse("incidents.ttl", format="turtle")
data.parse("hds-cdm.ttl", format="turtle")
shapes = Graph().parse("hds-cdm-shapes.ttl", format="turtle")
conforms, report_graph, report_text = validate(
    data, shacl_graph=shapes, meta_shacl=True
)
print(report_text)
```

Replace `incidents.ttl` with your instance-data file. Loading the ontology into
the data graph makes its class hierarchy available for class checks.

## Run the regression tests

The tests check that the validation rules accept valid examples and reject
invalid ones.
They do not validate your own `incidents.ttl`; use `validate.py` for that.

| Test file | What it protects |
| --- | --- |
| `tests/test_validation.py` | Current instance-data behaviour: field types, optional/repeatable properties, agent roles, locations, consent and licenses |
| `tests/test_validation_edges.py` | Missing/invalid vocabulary values, translations, optional descriptions, additional domains, metadata types and relationship targets |
| `tests/test_model_contract.py` | Deliberate HDS choices: core domains, class-to-domain location links, metadata boundaries and removed terms |
| `tests/test_validator_cli.py` | Running `validate.py`, example files, working-directory independence and failure exit codes |

Tests compare RDF meaning rather than Turtle formatting, triple order, prefixes
or blank-node identifiers. Editing descriptions or labels, adding translations,
adding valid domains or adding optional unconstrained metadata normally needs no
test changes. 

From the CDM repository root:

```powershell
python -m pip install -r requirements-validation.txt
python -m unittest discover -s tests -v
```

Install dependencies once per Python environment. The `-v` option displays
each test's name and result. A successful run currently ends with:

```text
Ran X tests ...

OK
```

