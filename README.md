# CODATA DRUM: Constants

***This work is in early development stage***

## Overview

This project focuses on the documentation and publication of fundamental physical constants in machine actionable formats. 

Our objectives are to convert information that currently exists in human readable documents (html, pdf, office documents) or loosely structured files (ascii text) into robust machine readable formats (e.g. JSON, XML, RDF), and make this information accessible over an consumer friendly, easy to use, industry standard web service (e.g. REST).

This work is taking place under the umbrella of the [CODATA Digital Representation of Units of Measure (DRUM)](https://codata.org/initiatives/task-groups/drum/) task group, an ongoing effort towards the digitization of the SI units of measure. 

## Approach

We are using the existing CODATA dataset on fundamental constants as published on the [NIST web site](https://physics.nist.gov/cuu/Constants/) as a starting point, and combine with outputs from other initiatives, such as QUDT and UCUM, to produce a as comprehensive and harmonized knowledge base as possible.

A simple model is being defined to represent the constant concept and their units of measures, and to capture their values (including changes over time).

The content is currently maintained in a public [Google sheet](https://docs.google.com/spreadsheets/d/1m5Hm3uRsgDVXIarp7-AQqt2mYSvdk0Bvzgx3bvdMT6s/edit#gid=122207678). We use a python script to download as an excel Spreadsheet, which we then parse to generate the outputs.

## In progress
- Create GitHUB repository
- Developing base model / serialization. In particular investigate the idea of constant concept (definition) vs their values (associated with a unit). 
- Implement tools to parse sheet and generate prototype outputs
- Convert the PDF files for the 2006, 2002, 1998, 1986, 1973 and 1969 versions
- Match / assign identifiers for the 2014 and 2010 versions
- Coordinate with QUDT project to add constant identifiers/values to their existing collection in order to use a common set

## Roadmap
- Coordinate with UCUM
- Setup search engine to support API
- Define web service specifications (OpenAPI / Postman)
- Implement API (e.g. WS Lambda)

## Findings

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
