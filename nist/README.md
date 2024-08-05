# NIST Fundamental Constants

Information in this section is based on publications from the U.S. National Institute of Standards and Technology (NIST) surrounding fudemantal physical constants.
NIST is the source of truth when it comes to the constant values. See https://pml.nist.gov/cuu/Constants/index.html for more information.

## Modernizing NIST publications

Beyond consulting the NIST website, the values for the constants are available for download in ASCII files, holding the quantity name, value, along with uncertainty and units when applicable. Suuplemental documentation files are available in PDF. Copies of these files can be found in directory. The ASCII data files are more intended for a human audience and not out of the box machine processable. No API is currently available. 

### ASCII data

The latest values for the constants can be found [here](https://pml.nist.gov/cuu/Constants/Table/allascii.txt), with previous versions available in archived sections: [2018](https://pml.nist.gov/cuu/Constants/archive2018.html),[2014](https://pml.nist.gov/cuu/Constants/archive2014.html), [2010](https://pml.nist.gov/cuu/Constants/archive2010.html), [2006](https://pml.nist.gov/cuu/Constants/archive2006.html), [2002](https://pml.nist.gov/cuu/Constants/archive2002.html), and [1998](https://pml.nist.gov/cuu/Constants/archive1998.html).Note that a formatting change occured in 2010 (separating value and uncertainty). Only PDFs are avaible for [1986](https://pml.nist.gov/cuu/Constants/archive1986.html)),[1973](https://pml.nist.gov/cuu/Constants/archive1973.html)), and [1969](https://pml.nist.gov/cuu/Constants/archive1969.html)) 

As previously mentionned, the primary ASCII file is formatted for a human reader. Notably:
- It starts with a few lines documenting its content
- Constant's values are string with groups of 3-4 decimal digits separeted by spaces (e.g. `5.971 919 67 e-10`)
- Prior to 2010, the uncertainty is blended in the value (e.g. `1.000 014 98(90) e-10`)
- Three dots (...) appear in the value when it has been truncated (e.g. `1.054 571 817... e-34`)
- When the constant is precisely determined, its uncertainty numeric value is the string `(exact)`
- The records are in fixed ASCII columns (after the multiline header)

Note also that, while NIST has internal identifiers associated with each constant, these are no present in the main ASCII file. We must therefore map the quantities' names, whose value may have changed over time, to persistent global identifiers (see below).

All these aspects make it impossible for machines to use the NIST publised infornation as is. It must therefore be transformed for further use by applications, databases, APIs, LLMS, and other digital processing purposes. Utilities to do so are provided in this section.

The `nist_to_json.py` script takes care of this to generate a new JSON file for the ASCII files, performing various cleansing, conversions, and derivation. These files can be found in the version sub-directories.

### NIST identifiers

NIST uses its own unique indentifiers for the fundemantal constants (a few letters and numbers), which you can be seen in the web pages URL and other places (e.g. `alpha particle mass` is `mal`). 
These identifiers are unfortunately not formally maintained and published, nor present in the published allascii files.
They also do not have documented crosswalks to other widely used ontologies such as QUDT .

The web page showing the [list of all constants](https://physics.nist.gov/cgi-bin/cuu/Category?vie) can be used to scrape the identifiers and generic names. This however does not work 
across all quantities or versions as names in the ASCII files may be abbreviated (e.g. ) or have changed over time, and some quantities have been addede/dropped.

Interestingly, the quantity names and their identifiers are present in the correlation coefficient ascii files (e.g. [2018](https://pml.nist.gov/cuu/Constants/ArchiveASCII/corrcoef2018)), and therefore can be extracted with a little parsing. For some reason this ASCII file does not seem to be available for the latest/current version (only archived years).

We have implemented helper methods to produce a consolidated [nist_ids.json](nist_ids.json) file holding the identifier and the quantiy names (in occasional cases more than one).
This is used during the allascii file processing to assign identifiers to the quantities.
These may need adjustments when future versions are released.

Note that the indentifers are case sensitive as two entries share a similar identifier (`Ae` and `ae`). This is normal behaviour anyway.
