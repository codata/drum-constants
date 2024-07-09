# NIST Fundamental Constants

Information in this section is based on publications from the U.S. National Institute of Standards and Technology (NIST) surrounding fudemantal physical constants.
NIST is the source of truth when it comes to the constant values. See https://pml.nist.gov/cuu/Constants/index.html for more information.

## Modernizing NIST publications

Beyond consulting the NIST website, the values for the constants are available for download in ASCII files, holding the quantity name, value, along with uncertainty and units when applicable. Suuplemental documentation files are available in PDF. Copies of these files can be found in directory. The ASCII data files are more intended for a human audience and not out of the box machine processable. No API is currently available. 

### ASCII data

The latest values for the constants can be found [here]( https://pml.nist.gov/cuu/Constants/Table/allascii.txt), with previous versions available in archived sections: [2018](https://pml.nist.gov/cuu/Constants/archive2018.html),[2014](https://pml.nist.gov/cuu/Constants/archive2014.html), [2010](https://pml.nist.gov/cuu/Constants/archive2010.html), [2006](https://pml.nist.gov/cuu/Constants/archive2006.html), [2002](https://pml.nist.gov/cuu/Constants/archive2002.html), and [1998](https://pml.nist.gov/cuu/Constants/archive1998.html).Note that a formatting change occured in 2010 (separating value and uncertainty). Only PDFs are avaible for [1986](https://pml.nist.gov/cuu/Constants/archive1986.html)),[1973](https://pml.nist.gov/cuu/Constants/archive1973.html)), and [1969](https://pml.nist.gov/cuu/Constants/archive1969.html)) 

As previously mentionned, the primary ASCII file is formatted for a human reader. Notably:
- It starts with a few lines documenting its content
- Constant's values are string with groups of 3-4 decimal digits separeted by spaces (e.g. `5.971 919 67 e-10`)
- Prior to 2010, the uncertainty is blended in the value (e.g. `1.000 014 98(90) e-10`)
- Three dots (...) appear in the value when it has been truncated (e.g. `1.054 571 817... e-34`)
- When the constant is precisely determined, its uncertainty numeric value is the string `(exact)`
- The records are in fixed ASCII columns (after the multiline header)

Note also that, while NIST has internal identifiers associated with each constant, these are no present in the main ASCII file. We must therefore map the quantities' names, whose value may have changed over time, to persistent global identifiers.

All these aspects make it impossible for machines to use the NIST publised infornation as is. It must therefore be transformed for further use by applications, databases, APIs, LLMS, and other digital processing purposes. Utilities to do so are provided in this section.


