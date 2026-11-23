# HDS-Centralized-Common-Data-Model
CDM used by HDS applications

## Domain-specific incident fields

`incident-domains.ttl` records the additional fields using `hds:applicableProperty`:

| Domain | Additional incident properties |
| --- | --- |
| Military | `hds:weaponsUsed`, `hds:casualties` |
| Human rights abuse | `hds:casualties` |
| Humanitarian | `hds:casualties` |
| Human trafficking | `hds:casualties` |
| Migration | `hds:casualties` |
| Political | `hds:outcome` |
| Environmental | No additional field listed |
| Sexual violence | Not shown in the green section |

These are property references, not subdomain concepts or values of the
properties. Actual values go on incident records.

## Validate the incident-domain vocabulary

`incident-domains-shapes.ttl` validates `incident-domains.ttl` together with
the property declarations in `hds-cdm.ttl`. It checks the
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

The command also checks both shapes graphs against SHACL's own shapes. Successful validation
reports `Conforms: True`; violations produce a validation report and a nonzero
exit code.

These vocabulary checks are separate from the incident-data constraints in
`hds-cdm-shapes.ttl`. When validating incident data with that file, include
`incident-domains.ttl` in the data graph for concept type and scheme checks.

## Validate CDM instance data

`hds-cdm.ttl` defines ontology classes and properties. Validation rules live in
`hds-cdm-shapes.ttl`. 

Incident records can be checked against the SHACL shapes.
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
data.parse("incident-domains.ttl", format="turtle")
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

From the  repository root:

```powershell
python -m pip install -r requirements-validation.txt
python -m unittest discover -s tests -v
```

Install dependencies once per Python environment. The `-v` option displays
each test's name and result. A successful run currently ends with:

```text
Ran 8 tests ...

OK
```

