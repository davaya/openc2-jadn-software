# An Information-centric OSCAL Information Model

The NIST Open Security Controls Assessment Language ([OSCAL](https://pages.nist.gov/OSCAL/))
is defined using NIST [Metaschema](https://pages.nist.gov/metaschema/),
a data-centric information modeling framework.

Information-centric information modeling methods are also available, including
* Abstract Syntax Notation number One ([ASN.1](https://www.itu.int/en/ITU-T/asn1/Pages/introduction.aspx)),
* Financial Information Exchange ([FIX](https://www.fixtrading.org/standards/)), and
* OASIS JSON Abstract Data Notation ([JADN](https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.1.md))

This note describes information modeling approaches and contrasts them using OSCAL as a non-trivial
example and JADN as an IM to illustrate their differences in a practical application.

## 1 Background

ASN.1 describes the difference between data-centric and information-centric approaches:

>ASN.1 definition can be contrasted to the concept in ABNF of "valid syntax", or in XSD of a "valid document",
where the focus is entirely on what are valid encodings of data, without concern with any meaning that
might be attached to such encodings. That is, without any of the necessary semantic linkages.

Metaschema is focused on data syntax:

> Metaschema is a framework for consistently organizing information into machine-readable data formats.  
>
>The Metaschema Information Modeling Framework provides a means to represent an information model
for a given information domain, consisting of many related information elements, in a data format
neutral form. By abstracting information modeling away from data format specific forms,
the Metaschema Information Modeling Framework provides a means to consistently and sustainably
maintain an information model, while avoiding the need to maintain each derivative data format individually.

JADN is focused on abstract syntax, modeling logical information values as defined in information theory,
i.e., the amount of "news" in a message quantified as bits of entropy.

> An Information Model defines the *essential content* of messages used in computing,
independently of how those messages are represented (i.e., serialized) for communication or storage.
>
> The core purpose of an IM is to define information equivalence. This allows the essential content
of data values to be compared for equality regardless of format, and enables hub-and-spoke
lossless translation across formats. 

Quantifying entropy is not an end goal of information modeling, but it is the key to defining significance
vs. insignificance. No data value can be smaller than the information content of a message,
therefore any data in excess of the smallest possible serialized value is insignificant.
Whitespace is a common example of insignificant data; the meaning of a message is unaffected by
inserting or deleting it.
Information modeling defines significance at the logical level: any data that does not affect a logical
value (isn't included the abstract type definition) is insignificant and can be discarded from any
data format without losing information. Or phrased the other way, if it is a problem for data in one format
to not be preserved when translated to another format, then the definition of significant needs to be
expanded to include that information.

### 1.1 Ontologies and Semantics

Ontologies are concerned with semantics - the meaning of and relationships among resources.
[Datatypes](https://www.w3.org/TR/rdf12-concepts/#section-Datatypes) define
logical (information) and lexical (data) values and the lexical-to-(logical)-value (L2V)
mapping between them, but today's ontologies support only primitive datatypes such as strings and numbers.
An abstract syntax defines the L2V mapping for all logical values including data structures, messages and
documents, and in an information-centric ontology every digital resource could be modeled as a datatype
with an L2V mapping.

Data modeling has a history beginning long before the advent of ontologies, with semantics defined
by conceptual and logical data models illustrated using entity relationship diagrams, and physical
data models for specific storage formats. But the ontology terminology of datatypes performing L2V
mapping is a particularly precise way of explaining the logical/lexical relationship.

![ERD](../../Images/erd-template.png)

As described by ASN.1, abstract syntaxes define the semantics of logical values,
with the translation from logical to physical/lexical defined in encoding specifications separate
from the logical type definitions. References from instances of one type to another are included
in that semantics, and an information model graph has only two kinds of edge: *contain* and *reference*.

### 1.2 Common Platform Enumeration

Before getting to OSCAL, the Common Platform Enumeration
([CPE](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf))
is a clear illustration of logical vs. lexical values. CPE is a compound datatype with an L2V mapping
between logical values (well-formed names) and lexical values (the result of a binding).
A JADN CPE type would define the logical value in terms of requirements:
* A CPE instance is a set of 12 defined fields
* The model designer can define CPE as either a Record type if field names are normative and optionally
included in some data formats, or an Array type if field names are annotations that can never appear
in lexical data, supporting natural language agnostic documents and protocols (I18N).
* The designer can designate Record and Array semantics as sets or ordered sets, which
determines which serializations are possible. An ordered set cannot have an L2V mapping to a JSON object
using just a data model because objects do not preserve order. If messages are processed at runtime
by an information model, object properties can be reordered as needed to conform to the logical type definition.
Any set can have an L2V mapping to a JSON array because the
array preserves positioning and the L2V mapping assigns logical names to lexical positions.
* An L2V mapping from the 12-field logical WFN to a single-string lexical value would be defined using
format options such as /cpe-22 or /cpe-23.

Defining CPE using Metaschema would illustrate the issues information-centric information models are
designed to address.

## 2 Metaschema and JADN Comparison

Information models

Significant (essential) vs. insignificant - communicating a WFN

12 JADN elements - 5 primitive, 5 collection, 2 union

UUID

Character and byte sequences, hex and base64 strings

### Conceptual modeling
No data required

Class instances exist without being serialized

### Every type is a Datatype
Data-centric approaches treat datatype as a synonym for primitive.  UUIDDatatype and EmailAddressDatatype are
redundant; UUID and EmailAddress are sufficient.

### No Properties or Flags
Primitives and Collections

### Packages and Bundles
Metaschema defines "combined" schemas and "unified model of models".

* JADN schemas are organized using packages
* **Package** has two fields
  * package context (package namespace, referenced namespaces, name, constraints, ...)
  * types defined within a package, all type names are qualified by the package namespace
  * a type definition can reference types from other packages
  * blank namespace prefixes allow types to be merged from multiple packages into a single package if contexts are compatible
* **Bundle** is a set of packages serialized together for transmission or storage
  * has no logical value: no id, no nesting, no association among packages, no persistent group after parsing

### Data-centric

Metaschema models are defined as XML data.

### Information-centric
Because a JADN IM is a logical value, it can be serialized in any data format, but does not need to be
serialized in any data format. This is useful when doing conceptual design; it allows an IM to be created
and documented in a domain-specific language (DSL) without using XML or other serialized data. JADN DSLs are
neither normative nor exclusive:
* The normative structure of a JADN IM is application state that exhibits the required behavior.
An IM can be instantiated within applications as, for example, a
[single variable](../../Images/oscal-concept-schema.jpg) or set of class variables.
* JADN Information Definition Language (IDL) is a DSL used to represent JADN information models.
Other hypothetical DSLs, such as one that mimics the syntax of ASN.1 or the terse grammar of
[CDDL](https://datatracker.ietf.org/doc/html/rfc8610),
could represent the identical application state.
*  The small number and regular structure of JADN elements facilitates design of both DSLs and serialized data formats.

A conceptual OSCAL IM can be defined in JADN IDL from the OSCAL top-level description:

![concept](../../Images/OSCAL-JADN-Notes.png)

This conceptual JADN design minimizes duplication - the overall model structure is defined once
as opposed to the OSCAL designer's approach of repeating the same Metaschema structure in each of the models.
A goal of any information modeling language is not to impose a design philosophy but to provide the
expressive power to allow model designers to communicate their intent unambiguously, clearly and succinctly.

The actual JADN information model for OSCAL matches the published OSCAL specification, which does not require
content to appear in any particular order. Back-matter could appear at the front of an OSCAL document,
or Metadata after the Body, because Metaschema Assembly definitions do not impose a serialization order.
A JADN IM can define field ordering if that is the designer's intent.

```
       title: "OSCAL"
     package: "https://example.gov/ns/oscal/0.0.1/"
 description: "OSCAL - Open Security Controls Assessment Language concept"
  namespaces: [["", "https://example.gov/ns/oscal/0.0.1/metadata/"],
               ["", "https://example.gov/ns/oscal/0.0.1/catalog/"],
               ["", "https://example.gov/ns/oscal/0.0.1/profile/"],
               ["", "https://example.gov/ns/oscal/0.0.1/component/"],
               ["", "https://example.gov/ns/oscal/0.0.1/ssp/"],
               ["", "https://example.gov/ns/oscal/0.0.1/assessment-plan/"],
               ["", "https://example.gov/ns/oscal/0.0.1/assessment-results/"],
               ["", "https://example.gov/ns/oscal/0.0.1/poam/"],
               ["", "https://example.gov/ns/oscal/0.0.1/back-matter/"]]
       roots: ["OSCAL"]

OSCAL = Record sequence                              // OSCAL document - seq option requires content to appear in defined order
   1 model            Enumerated(Enum[Model])        // OSCAL model identifier
   2 uuid             UUID                           // Document instance unique identifier
   3 metadata         Metadata                       // Identifying info, roles, parties and locations
   4 body             Model(Tag[model])              // Model-specific body
   5 back_matter      Back-matter optional           // Linked and attached resources

Model = Choice                                       // Model-specific content
   1 catalog          Catalog                        // Control layer: catalog of controls
   2 profile          Profile                        // Control layer: selecting, organizing and tailoring a set of controls
   3 component        Component                      // Implementation layer: component definition and configuration
   4 ssp              System-security-plan           // Implementation layer: security implementation of an information system
   5 ap               Assessment-plan                // Assessment layer: scope and activities
   6 ar               Assessment-results             // Assessment layer: information produced from assessment activities
   7 poam             Plan-of-action-and-milestones  // Assessment layer: Plan of action and milestones: findings to be addressed by system owner
```


## 4 Summary
| Feature           | JADN                                            | Metaschema                              |
|-------------------|-------------------------------------------------|-----------------------------------------|
| Model definition  | IDL or serialized as data in any format         | XML data                                |
| Model instance    | Logical value: state in an application          | Data value: XML                         | 
| Data translation  | Hub/spoke (data->logical->data): N translations | Star (data->data): N^2 translations     |
| Information       | Logical model defines significant content       | Insignificant content is undefined      |
| Datatypes         | Every type is a datatype                        | Only primitives (flags) are Datatypes   |
| Type names        | Every type has a name                           | Anonymous (nested) types are allowed    |
| Type references   | Single id format: ns:Type.field                 | Multiple id formats                     |
| Fields/Properties | Assembly binds local id/name to type            | Field names are bound globally to types |
| Field names       | Enumerated (numeric id and text name/label)     | Text name only                          |
| Field order       | Assemblies are ordered or unordered set         | Assemblies are only unordered set       |
| Data formats      | Character sequence (text) or byte sequence      | Character sequence only                 |
| Packaging         | Models can be grouped in non-semantic bundles   | Types from multiple models can be mixed |
| Documentation     | Short comments, external docs incorporate types | Type definitions include documentation  |