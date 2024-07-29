# An Abstract OSCAL Information Model

The NIST Open Security Controls Assessment Language ([OSCAL](https://pages.nist.gov/OSCAL/))
is defined using NIST [Metaschema](https://pages.nist.gov/metaschema/),
a data-centric information modeling framework.

Abstract information modeling methods are also available, including
* Abstract Syntax Notation number One ([ASN.1](https://www.itu.int/en/ITU-T/asn1/Pages/introduction.aspx)),
* Financial Information Exchange ([FIX](https://www.fixtrading.org/standards/)), and
* OASIS JSON Abstract Data Notation ([JADN](https://github.com/oasis-tcs/openc2-jadn/blob/working/jadn-v1.1.md))

This note describes information modeling approaches and contrasts them using OSCAL as a non-trivial
example and JADN as an IM to illustrate their differences in a practical application.

## 1 Background

ASN.1 describes the difference between data-centric and abstract modeling approaches:

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
i.e., the amount of "news" or "essential information" contained in a message.

> An Information Model defines the *essential content* of messages used in computing,
independently of how those messages are represented (i.e., serialized) for communication or storage.
>
> The core purpose of an IM is to define information equivalence. This allows the essential content
of data values to be compared for equality regardless of format, and enables hub-and-spoke
lossless translation across formats. 

Information defines significant vs. insignificant in lexical values. Just as whitespace
is often insignificant at the data level, an information model defines significance at the logical
level: any data that is not included in a logical value is insignificant and has been ignored
in the lexical to logical conversion.

Information theory uses the word "entropy" to refer to the quantity of information carried in a
message. The more restrictions that are placed on a value, the less data is required to
carry its information regardless of how much data is actually used. Strings with no restrictions
are least efficient; strings with restricted length, character set, or patterns are more efficient,
and enumerations such as field names, enumerated map keys, and vocabularies are by far the most
efficient.  The string "mitigation" is always the same at the data level, but when it represents
one of only five possible observation types
("ssp-statement-issue", "control-objective", "mitigation", "finding", "historic") it carries
less than 3 bits of information in 80 bits of lexical data.
The other 77 bits are not essential content and are not included in the logical value.
If an information model allows generic strings (for example, "Purina-cat-chow" or
"Four score and seven years ago our fathers brought forth on this continent a new nation,
from the 🏔️ to the 🌾 to the 🏖️.") where restricted or enumerated values are appropriate,
it requires both users and applications to deal with inappropriate content and presents a
larger attack surface to adversaries.
Designing information models to correctly distinguish between essential content and
insignificant data is not just theoretical trivia, it's an operational and security benefit.
Allowing a tokenized Gettysburg address as a telephone number type is an anti-pattern that
can be tested for in the release pipeline.

### 1.1 Ontologies and Semantics

Ontologies are concerned with semantics - the meaning of and relationships among resources.
[Datatypes](https://www.w3.org/TR/rdf12-concepts/#section-Datatypes) define
logical (information) and lexical (data) values and the lexical-to-(logical)-value (L2V)
mapping between them, but today's ontologies support only primitive datatypes such as strings and numbers.
An abstract information model defines the L2V mapping for all logical values including data structure,
messages and documents, and an ontology that supports abstract information models would be able
to define an L2V mapping for all messages and documents.

Data modeling has a history beginning long before the advent of ontologies, with semantics defined
by conceptual and logical data models separated from physical data models for storage formats.
But the ontology terminology of datatypes performing L2V mapping is a novel and precise way of
explaining the relationship between logical and lexical values.

![Entity Relationship Diagram](../../Images/erd-template.png)

### 1.2 Common Platform Enumeration

Before getting to OSCAL, the Common Platform Enumeration
([CPE](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir7695.pdf))
is a clear illustration of the difference between logical and lexical values.
CPE is a compound datatype with an L2V mapping between well-formed names and lexical representations.
An abstract information model would define the CPE logical value in semantic terms:
* A CPE instance is a set of 12 defined fields
* The model designer can define CPE as either a Record type if field names are normative and optionally
included in some data formats, or an Array type if field names are annotations that can never appear
in lexical data, supporting natural language agnostic documents and protocols (I18N).
* The designer can designate Record, Map and Array semantics as sets or ordered sets, which
determines which serializations are possible.
* An L2V mapping from the 12-field logical WFN to a single-string lexical value would be defined using
format options such as /cpe-22 or /cpe-23.

Defining CPE using Metaschema would illustrate the significance of logical values in information modeling.

## 2 Metaschema and JADN Comparison

Information models

Significant (essential) vs. insignificant - communicating a WFN

12 JADN elements - 5 primitive, 5 collection, 2 union

UUID

Character and byte sequences, hex and base64 strings

### Conceptual modeling

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

### Abstract
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
A JADN IM can define field ordering if that is the designer's intent, but implementing it in JSON Schema
would require a change to the serialization format.

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
## 3 Modeling OSCAL in JADN
After understanding the differences in approach and demonstrating JADN's ability to validate existing OSCAL data,
the question remains: what advantages does it have in this application?  
A minimal set of logical types is easier to describe, understand, and edit.
Logical types are essential content -> bare HTML, encoding rules add implementation detail -> css

Example: Assessment plan unique constraint on component and user (uses key).  Logical: is_unique, has_key. Lexical: serialized as map or list.

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