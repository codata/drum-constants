"""

This script converts the NIST physical constants ASCII data files to JSON.

Author: 
- Pascal Heus (https://github.com/kulnor)

This work is licensed under the terms of the MIT license.
For a copy, see <https://opensource.org/licenses/MIT>.

"""

from dataclasses import dataclass, asdict, field
import re
from typing import List, Optional
import json
import argparse
import os

@dataclass
class PhysicalConstant:
    year: int
    quantity: str
    nist_value: str
    nist_uncertainty: Optional[str]
    unit: Optional[str]
    exponent: Optional[str] = field(init=False, default=None)
    is_exact: bool = field(init=False, default=False)
    is_truncated: bool = field(init=False, default=False)
    str_value: str = field(init=False, default=None)
    str_uncertainty: Optional[str] = field(init=False, default=None)
    numeric_value: float = field(init=False, default=None)
    numeric_uncertainty: Optional[float] = field(init=False, default=None)

    def __post_init__(self):
        # truncated flag
        if '...' in self.nist_value:
            self.is_truncated = True
            # clean the string value
            self.nist_value = self.nist_value.replace('...', '')
        # uncertainty flag
        if self.year >= 2010:
            if '(exact)' in self.nist_uncertainty:
                self.is_exact = True
        else:
            self.is_exact = not bool(re.search(r'\(\d+\)', self.nist_value))
        # exponent
        m = re.search(r'e([-\d]+)$', self.nist_value)
        if m:
            self.exponent = m.group()

        if self.year < 2010 and not self.is_exact:
            #p Prior to 2010, the uncertainty was blended in the value. For examples:
            # - 1.000 014 98(90) e-10
            # - 6.644 656 20(33) e-27
            # - 931.494 028(23)
            # - 376.730 313 461...
            # - 8.617 343(15) e-5
            # - 2.187 691 2541(15) e6
            #
            # Extract uncertainty from the value
            match = re.search(r'([0-9. ]+)\((\d+)\)\s*(e[-+]?\d+)?', self.nist_value)
            if match:
                # Remove spaces from the main number and count the number of digits after the decimal point
                main_number = match.group(1).replace(' ', '')
                uncertainty_digits = len(main_number.split('.')[1]) if '.' in main_number else 0
                uncertainty_value = match.group(2)
                
                # Create the uncertainty string with the correct number of zeros
                uncertainty = '0.' + '0' * (uncertainty_digits - len(uncertainty_value)) + uncertainty_value

                # Format the NIST way (with space separators every 3 decimal digits)
                parts = uncertainty.split('.')
                integer_part, decimal_part = parts
                decimal_part = ' '.join([decimal_part[i:i+3] for i in range(0, len(decimal_part), 3)])
                decimal_part = re.sub(r' (\d)$', r'\1', decimal_part) # if there is only one digit at the end, merge it with previous group. For example .000 000 007 9 --> .000 000 0079

                # Append the exponent if present
                exponent = match.group(3)

                # set uncertaintly string value
                self.nist_uncertainty = f"{integer_part}.{decimal_part}"
                if exponent:
                    self.nist_uncertainty += ' '+exponent

            # remove the uncertainty from the string value
            self.nist_value = re.sub(r'\(\d+\)', '', self.nist_value)
        else:
            pass
        # initializes computed properties
        self.str_value = self.nist_value.replace(' ', '').replace('...', '')
        self.numeric_value = float(self.str_value)
        if not self.is_exact:
            self.str_uncertainty = self.nist_uncertainty.replace(' ', '')
            self.numeric_uncertainty = float(self.str_uncertainty)

class PhysicalConstantEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, PhysicalConstant):
            result = asdict(obj)
            return result
        return super().default(obj)

def read_allascii_file(filename: str, year: int) -> List[PhysicalConstant]:
    constants = []
    with open(filename, 'r') as file:
        # Skip initial lines until we reach the ----------
        for line in file:
            if line.strip().startswith("----------"):
                break
        
        # Process the rest of the file
        for line in file:
            if year >= 2010:
                constant = PhysicalConstant(
                    year=year,
                    quantity=line[0:60].strip(),
                    nist_value=line[60:85].strip(),
                    nist_uncertainty=line[85:110].strip(),
                    unit=line[110:].strip()
                )
            else:
                # prior to 2010, the uncertainly is blended in the value
                # and the column positions are different
                constant = PhysicalConstant(
                    year=year,
                    quantity=line[0:62].strip(),
                    nist_value=line[62:96].strip(),
                    nist_uncertainty=None,
                    unit=line[96:].strip()
                )
            constants.append(constant)
    
    return constants

def allascii_to_json(constants: List[PhysicalConstant], filename: str):
    with open(filename, 'w') as f:
        json.dump(constants, f, cls=PhysicalConstantEncoder, indent=2)

def main():
    if not args.year:
        years = [1998,2002,2006,2010,2014,2018,2022]
    else:
        years = args.year
    for year in years:
        input_filename = f'allascii_{year}.txt'
        input_file = os.path.join(script_dir, str(year), input_filename)

        output_filename =   f'{os.path.splitext(input_filename)[0]}.json'
        output_file = os.path.join(script_dir, str(year), output_filename)

        constants = read_allascii_file(input_file, year)

        # Save to JSON
        allascii_to_json(constants, output_file)

        print(f"Data has been saved to {output_file}")

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)

    parser = argparse.ArgumentParser(description='Process physical constants from a text file and save to JSON.')
    parser.add_argument('year', nargs='*', type=int, help='The year(s) to process')
    
    args = parser.parse_args()

    main()