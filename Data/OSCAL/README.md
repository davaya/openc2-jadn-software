# JADN / Metaschema Comparison, OSCAL Catalog Information Model

## Components

> A definition in a Metaschema module declares a reusable information element within an information model.
> The 3 types of definitions are `<define-flag>`, `<define-field>`, and `<define-assembly>`.

A definition in a JADN module declares a reusable information element within an information model.
The two types of definitions are `primitive` and `compound`.

> The names of flags, fields, and assemblies are expected to be maintained as separate identifier sets.
> This allows a flag definition, a field definition, and an assembly definition to each have the same name
> in a given Metaschema module.

The names of primitive and compound types are maintained in a single identifier set.
This allows each type definition to be uniquely identified by its name within a given JADN module,
reducing potential for confusion.

### Flag

> The flag's value is strongly typed using one of the built in simple data types identified by
> the @as-type attribute, including: four numeric values, six temporal values, two binary values, and
> nine character-based values.

A JADN primitive value is strongly typed using one of the five JADN built-in simple data types:
Binary, Boolean, Integer, Number, String.

### Field

> A field definition is an edge node in a Metaschema-based model.
> Fields are typically used to provide supporting information for a containing assembly definition.

There are no standalone field definitions in a JADN-based model.
Fields are defined as components of a compound type.

### Assembly

> An assembly definition is a compositional node in a Metaschema-based model.
> Assemblies are typically used to represent complex data objects, combining multiple
> information elements together into a composite object representing a larger semantic concept.
> An assembly's flag instances will typically characterize or identify this composite object,
> while its model instances represent the information being composed.

A `compound` type definition is the compositional node in a JADN-based model.
Each compound type is a container of fields that assign a local identifier to each field type.
JADN defines five compound types based on multiplicity characteristics of its fields:
ordered/unordered, unique/non-unique, named/unnamed, and heterogeneous/homogeneous value type:
* **Array** - ordered, non-unique, unnamed individually-typed value
* **ArrayOf** - ordered or unordered, unique or non-unique, unnamed same-typed values
* **Map** - unordered, non-unique value, unique enumerated name
* **MapOf** - unordered, non-unique same-typed values, unique typed name
* **Record** - ordered, non-unique value, unique enumerated name

Each field within a compound type can be any type, primitive or compound.

## Comparison Process

* Using OSCAL Catalog JSON schema, define a JADN IM equivalent to the Metaschema Catalog IM
* Validate the JADN IM against the Catalog example JSON data
* Compare JSON Schema from JADN against JSON Schema from Metaschema
* Validate the JADN IM against the Catalog example XML data
* Compare XSD from JADN against XSD from Metaschema

Repeat the above steps for the other six more complex OSCAL layers

Compare the JADN and Metaschema OSCAL IMs for complexity/usability/readability and other -ilities.

## Observations
### Type Names
The Metaschema-generated JSON Schema uses two different ways of naming type definitions:
1) Directly as the definition name:
```
    "Base64Datatype": {
      "description": "Binary data encoded using the Base 64 encoding algorithm as defined by RFC4648.",
      "type": "string",
      "pattern": "^[0-9A-Za-z+/]+={0,2}$",
      "contentEncoding": "base64"
    },
```
2) As definition name suffix:
```
    "oscal-catalog-oscal-catalog:catalog": {
      "title": "Catalog",
      "description": "A structured, organized collection of control information.",
      "$id": "#assembly_oscal-catalog_catalog",
      "type": "object",
```
### Contrasts
* A significant distinction between JADN and Metaschema is the definition of fields only as members
of an assembly, bringing the ability to define the multiplicity characteristics of fields within the
assembly.

* The work-in-progress (many errors to be fixed) module [out.jidl](out.jidl) illustrates what a JADN IM
would look like. It is currently ~200 lines, vs. 1451 lines for the
[JSON Schema](../../Projects/Metaschema/oscal_catalog_schema_1.1.0.json) from which it was generated.

## Recommendations

1. Investigate organizing Metaschema into "Framework" and "Data Model" layers as described in [ADM](AbstractDataModel.md).
2. Assign a referencable name (e.g., "Catalog") to each defined Metaschema type, uniform in format
and within a single identifier set.  This would allow fields to uniformly reference both flags and assemblies
by name.
3. Adopt naming conventions for assembly/flag names (e.g. PascalCase, Train-Case) and field names
(e.g., camelCase, snake_case) for each specific Information Model (e.g. OSCAL)

## References

### JSON Examples:
* [Basic Catalog](https://github.com/usnistgov/oscal-content/blob/main/examples/catalog/json/basic-catalog.json)
* [Example Component Definition, Example Component](https://github.com/usnistgov/oscal-content/tree/main/examples/component-definition/json)
* [SSP Example, OSCAL Leveraged Example, OSCAL Leveraging Example](https://github.com/usnistgov/oscal-content/tree/main/examples/ssp/json)

### JSON Schema from Metaschema:
* [Catalog Release 1.1.0](https://github.com/usnistgov/OSCAL/releases/download/v1.1.0/oscal_catalog_schema.json),
from [Assets](https://github.com/usnistgov/OSCAL/releases/)

### Metaschema
* [Catalog Release 1.1.0](https://github.com/usnistgov/OSCAL/blob/main/src/metaschema/oscal_catalog_metaschema.xml)

### Abstract Data Model
* [Abstract Data Model](AbstractDataModel.md)