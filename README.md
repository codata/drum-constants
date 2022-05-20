# CODATA DRUM: Constants

***This work is in early development stage***

## Overview

This project focuses on the documentation and publication of fundamental physical constants in machine actionable formats. 

Our objectives are to convert information that currently exists in human readable documents (html, pdf, office documents) or loosely structured files (ascii text) into robust machine readable formats (e.g. JSON, XML, RDF), and make this information accessible over an consumer friendly, easy to use, industry standard web service (e.g. REST).

This work is taking place under the umbrella of the [CODATA Digital Representation of Units of Measure (DRUM)](https://codata.org/initiatives/task-groups/drum/) task group, an ongoing effort towards the digitization of the SI units of measure. 

## Approach

We are using the existing CODATA dataset on fundamental constants as published on the [NIST web site](https://physics.nist.gov/cuu/Constants/) as a starting point, and combine with outputs from other initiatives, such as QUDT and UCUM, to produce a as comprehensive and harmonized knowledge base as possible.

A simple model is being defined to represent the constant concept and their units of measures, and to capture their values (including changes over time).

The content is currently maintained in a public [Google sheet](https://docs.google.com/spreadsheets/d/1m5Hm3uRsgDVXIarp7-AQqt2mYSvdk0Bvzgx3bvdMT6s/edit#gid=122207678). We use a python script to download as an Excel Spreadsheet, which we then parse to generate the outputs.

### Model

The minimalist model used to produced the JSON version of the constants is based on the following hierarchy of resources:

- Constant: defines a base constant (the same constant can in some cases be expressed using different units)
- ConstantInstance: a Constant associated with a Unit, the latter being described using different expressions such as SI, UCUM, UOM. Available identifiers are also included (CODATA, QUDT).
- ConstantValue: a value of a ConstantInstance for a particular version. This includes additional properties such as the version year, value uncertainty and exponent, and the name.

The model is work in progress and expects to change over time. Adding Concepts (associated with a Constant) are on the roadmap.

## In progress
- QA and peer review of current outputs
- Capture name/definition at the Constant level (from BIPM?)
- Refine JSON model
- Produce other serialization for users (e.g. HTML) or in other formats/models (JSON, RDF, XML)
- Start looking into indexing and API

## Pending
- n/a

## Roadmap
- Coordinate with QUDT project to add constant identifiers/values to their existing collection in order to use a common set.  
- Coordinate with UCUM
- Explore the development of Concepts to further document and refines the Constant's meaning and facilitate search/discovery
- Considewr adding relationship of units with the 7 base defining constants
- Research how units are being used across constants. Which are popular? Where do the live in the ISO 7-dimensional space? 
- Setup search engine to support API
- Define web service specifications (OpenAPI / Postman)
- Implement API (e.g. WS Lambda)

## Findings / Progress

### June 2022
- Added 2006, 2002, and 1998 values following NIST release in ASCII format
- Initial implementation of API with UI demo

### November 2021
- Update the JSON format to facilitate parsing (using arrays instead of hash)
- Implemented simple static HTML site from JSON (using (Eleventy)<https://www.11ty.dev/>)

### October 2021
- Added units expressions in [UCUM](https://ucum.org) formats and URL from the [Units of Measurements](https://github.com/units-of-measurement) project

### August/September 2021
- A python utility was developed to parse the google sheet and generate a initial JSON output
- We refined the model to be able to capture information for three nested entities: Constant, Constant Units, and the Constant Unit Value for a particular version
- The sheet was updated to reflect the model changes and capture entities relationships for the current data (2010 / 2014 / 2018). At this time, the Constant entities is just an identifier (no additional properties)- For earlier years, documentation may seem to exists in text/ascii formats. We've put the PDF conversion on hold until we hear back fro NIST.
- We performed some initial research around the development of concepts describing the constants. This will be useful down the road but we set this task aside for now as first want to focus on generating outputs for all versions

### July 2021
- Initiated project
- Transferred constant definitions from the 2017, 2014, and 2010 versions available in ASCII text format on NIST website into spreadsheet. Information for the previous versions are in PDF and need to be converted.
- Added some basic conversion and QA formulas to the spreadsheet
- The constants, as documented on the NIST website, do not come with unique identifiers. Rather than create or own set, we have adopted the identifiers used by the QUDT project. We will further coordinate with the group to add identifiers for constant not currently covered by QUDT
- Constant names currently use various abbreviations (e.g. atomic unit of electric dipole *mom.*). We are considering both expending these and/or harmonizing with the BIPM names/definitions (both in English and French). Our model should in any case allow for name variations (based on context or languages)
- Constant values in the NIST published files are text string intended to be human readable. They can be a number or in scientific notation, and typically contains space separating groups of three digits (e.g. ` 1.000 014 95 e-10`). The digital version will convert these to both clean strings (no spaces) and numeric values (for convenience). The preferred exponent will also be captured as an attribute (so the uncertainty can be express in the same exponent as the value).
- Some constant values were fond to end with ellipses `...`, and have no uncertainty (exact. An example is `  8.617 333 262... e-5` for the Boltzmann constant in eV/K, or ` 25 812.807 45...` for the von Klitzing constant. This typically occurs when the constant value involves a ratio of irrational numbers such as Pi or the  elementary charge `e`. These ellipsis makes it challenging to convert to a numeric value using common string parsers. We therefore will move this out of the string value, and add an attribute flag to indicate this condition. Including an explanatory text is also being considered.

## References
- [NIST Fundamental Constants](https://physics.nist.gov/cuu/Constants/)
- [BIPM: SI Brochure](https://www.bipm.org/en/publications/si-brochure)

## Licensing

This work is licensed under a [Creative Commons Attribution 4.0 International License](http://creativecommons.org/licenses/by/4.0/).

Software and source code are released under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt) license.


## About / Support
This container is maintained by Pascal Heus (CODATA DRUM member). Use GitHub issue tracker for questions, suggestions, or if you need assistance.
