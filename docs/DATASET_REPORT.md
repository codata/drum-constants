# CODATA DRUM Constants — Dataset & Validation Report

> **Validation Status**: ⚠️ PASS WITH WARNINGS (0 errors, 8 warnings)  
> **Latest CODATA Release**: `2022`  
> **Schema Version**: `0.3.0`

## 1. Executive Summary

| Metric | Count |
|---|---:|
| CODATA Release Versions | 7 |
| Physical Constants (Total) | 359 |
| Physical Constants (Active in `2022`) | 355 |
| Physical Constants (Deprecated / Historical) | 4 |
| Versioned Constant Values | 2313 |
| Physical Quantities | 306 |
| Taxonomic Concepts | 442 |
| Measurement Units | 84 |
| NIST Values Cross-Checked | 2313 |
| Validation Errors | 0 |
| Validation Warnings | 8 |

## 2. CODATA Release Coverage Matrix

| Release | Published | Constants | Exact | Measured | Truncated | Added vs Prev | Retired vs Prev |
|---|---|---:|---:|---:|---:|---:|---:|
| `2022` | 2024-05-09 | 355 | 81 | 274 | 62 | 1 | 0 |
| `2018` | 2019-05-20 | 354 | 81 | 273 | 62 | 21 | 2 |
| `2014` | 2015-06-15 | 335 | 17 | 318 | 7 | 0 | 0 |
| `2010` | 2011-06-02 | 335 | 17 | 318 | 7 | 14 | 3 |
| `2006` | 2007-03-07 | 324 | 16 | 308 | 7 | 17 | 0 |
| `2002` | 2003-12-09 | 307 | 16 | 291 | 7 | 4 | 0 |
| `1998` | 1999-07-23 | 303 | 16 | 287 | 4 | — | — |

## 3. External Vocabulary & Curation Coverage

| Alignment / Field | Entity Scope | Mapped | Total | Coverage | Progress |
|---|---|---:|---:|---:|---|
| NIST Identifiers | Constants | 359 | 359 | 100.0% | `████████████` |
| QUDT Constants (`qudt_id`) | Constants | 325 | 359 | 90.5% | `███████████░` |
| SI Digital Framework (`si_id`) | Constants | 7 | 359 | 1.9% | `░░░░░░░░░░░░` |
| UCUM Constant Codes (`ucum_id`) | Constants | 11 | 359 | 3.1% | `░░░░░░░░░░░░` |
| French Labels (`name_fr`) | Constants | 359 | 359 | 100.0% | `████████████` |
| SI Digital Framework (`si_id`) | Units | 75 | 84 | 89.3% | `███████████░` |
| UCUM Unit Codes (`ucum_id`) | Units | 75 | 84 | 89.3% | `███████████░` |
| Wikidata (`wikidata_id`) | Units | 1 | 84 | 1.2% | `░░░░░░░░░░░░` |
| Wikidata (`wikidata_id`) | Concepts | 14 | 442 | 3.2% | `░░░░░░░░░░░░` |
| Definitions (`definition`) | Concepts | 14 | 442 | 3.2% | `░░░░░░░░░░░░` |

<details><summary>Constants without QUDT mapping (34)</summary>

| Constant ID | Name | NIST ID |
|---|---|---|
| `AlphaParticleRelativeAtomicMass` | Alpha Particle Relative Atomic Mass | `aral` |
| `AlphaParticleRmsChargeRadius` | Alpha Particle Rms Charge Radius | `ral` |
| `ConventionalValueOfAmpere90` | Conventional Value Of Ampere-90 | `ampere90` |
| `ConventionalValueOfCoulomb90` | Conventional Value Of Coulomb-90 | `charge90` |
| `ConventionalValueOfFarad90` | Conventional Value Of Farad-90 | `capacitance90` |
| `ConventionalValueOfHenry90` | Conventional Value Of Henry-90 | `inductance90` |
| `ConventionalValueOfOhm90` | Conventional Value Of Ohm-90 | `ohm90` |
| `ConventionalValueOfVolt90` | Conventional Value Of Volt-90 | `volt90` |
| `ConventionalValueOfWatt90` | Conventional Value Of Watt-90 | `power90` |
| `DeuteronRelativeAtomicMass` | Deuteron Relative Atomic Mass | `ard` |
| `ElectronHelionMassRatio` | Electron - Helion Mass Ratio | `mesmh` |
| `ElectronRelativeAtomicMass` | Electron Relative Atomic Mass | `are` |
| `ElectronTritonMassRatio` | Electron - Triton Mass Ratio | `mesmt` |
| `ElectronVolt` | Electronvolt | `tevj` |
| `FaradayConstantConventionalElectricCurrent` | Faraday Constant For Conventional Electric Current | `f90` |
| `HelionGFactor` | Helion G Factor | `ghn` |
| `HelionMagneticMoment` | Helion Magnetic Moment | `muh` |
| `HelionMagneticMomentToBohrMagnetonRatio` | Helion Magnetic Moment To Bohr Magneton Ratio | `muhsmub` |
| `HelionMagneticMomentToNuclearMagnetonRatio` | Helion Magnetic Moment To Nuclear Magneton Ratio | `muhsmun` |
| `HelionRelativeAtomicMass` | Helion Relative Atomic Mass | `arh` |
| `HelionShieldingShift` | Helion Shielding Shift | `sigmah` |
| `HyperfineTransitionFrequencyOfCs133` | Hyperfine Transition Frequency Of Cs-133 | `nucs` |
| `NeutronProtonMassDifference` | Neutron - Proton Mass Difference | `mnmmp` |
| `NeutronProtonMassDifferenceEnergyEquivalent` | Neutron - Proton Mass Difference Energy Equivalent | `mnmmpc2` |
| `NeutronProtonMassDifferenceEnergyEquivalentInMeV` | Neutron - Proton Mass Difference Energy Equivalent In MeV | `mnmmpc2mev` |
| `NeutronProtonMassDifferenceInU` | Neutron - Proton Mass Difference In U | `mnmmpu` |
| `NeutronRelativeAtomicMass` | Neutron Relative Atomic Mass | `arn` |
| `NewtonianConstantOfGravitationOverHBarC` | Newtonian Constant Of Gravitation Over H-Bar C | `bgspu` |
| `ProtonRelativeAtomicMass` | Proton Relative Atomic Mass | `arp` |
| `ShieldingDifferenceOfDAndP` | Shielding Difference Of D And P In Hd | `sdp` |
| `ShieldingDifferenceOfTAndP` | Shielding Difference Of T And P In Ht | `stp` |
| `StandardStatePressure` | Standard-State Pressure | `stdspr` |
| `TritonRelativeAtomicMass` | Triton Relative Atomic Mass | `art` |
| `WToZMassRatio` | W To Z Mass Ratio | `rmwmz` |

</details>

<details><summary>Units without UCUM code (9)</summary>

| Unit ID | Name | Parts |
|---|---|---|
| `AXC` | ampere-90 | — |
| `CXC` | coulomb-90 | — |
| `CXC_mol-1` | — | CXC, mol |
| `FXC` | farad-90 | — |
| `HXC` | henry-90 | — |
| `Hz_VXC-1` | hertz per volt-90 | Hz, VXC |
| `VXC` | volt-90 | — |
| `WXC` | watt-90 | — |
| `ohmXC` | ohm-90 | — |

</details>

## 4. Deprecated Constants (Absent in `2022`)

| Constant ID | Name | NIST ID | Active Releases | Last Release |
|---|---|---|---|---|
| `FaradayConstantConventionalElectricCurrent` | Faraday Constant For Conventional Electric Current | `f90` | 1998, 2002, 2006, 2010, 2014 | `2014` |
| `MolarPlanckConstantTimesC` | Molar Planck Constant Times C | `nahc` | 1998, 2002, 2006, 2010, 2014 | `2014` |
| `TritonElectronMagneticMomentRatio` | Triton - Electron Magnetic Moment Ratio | `mutsmuem` | 2006 | `2006` |
| `TritonNeutronMagneticMomentRatio` | Triton - Neutron Magnetic Moment Ratio | `mutsmunn` | 2006 | `2006` |

## 5. Metrological Identity Verification (`2022`)

| Check | Formula | CODATA Value | Computed | Rel. Error | Tolerance | Status |
|---|---|---:|---:|---:|---:|---|
| Speed of Light (exact) | `c == 299792458` | `299792458` | `299792458` | `0.00e+00` | `1e-15` | ✅ PASS |
| Planck Constant (exact) | `h == 6.62607015e-34` | `6.62607015e-34` | `6.62607015e-34` | `0.00e+00` | `1e-15` | ✅ PASS |
| Elementary Charge (exact) | `e == 1.602176634e-19` | `1.602176634e-19` | `1.602176634e-19` | `0.00e+00` | `1e-15` | ✅ PASS |
| Boltzmann Constant (exact) | `k == 1.380649e-23` | `1.380649e-23` | `1.380649e-23` | `0.00e+00` | `1e-15` | ✅ PASS |
| Avogadro Constant (exact) | `N_A == 6.02214076e23` | `6.02214076e+23` | `6.02214076e+23` | `0.00e+00` | `1e-15` | ✅ PASS |
| Molar Gas Constant | `R = k * N_A` | `8.314462618` | `8.31446261815` | `1.84e-11` | `1e-09` | ✅ PASS |
| Faraday Constant | `F = N_A * e` | `96485.33212` | `96485.3321233` | `3.43e-11` | `1e-09` | ✅ PASS |
| Hartree Energy (Rydberg) | `E_h = 2 * R_inf * h * c` | `4.35974472221e-18` | `4.35974472221e-18` | `5.12e-15` | `1e-09` | ✅ PASS |
| Hartree Energy (Fine Structure) | `E_h = alpha^2 * m_e * c^2` | `4.35974472221e-18` | `4.35974472216e-18` | `1.08e-11` | `1e-09` | ✅ PASS |

## 6. Validation Audit

- **Layer 1 (Schema & Precision)**: 0 issues
- **Layer 2 (Referential Integrity & Topology)**: 8 issues
- **Layer 3 (Domain, Labels & SI Hygiene)**: 0 issues
- **Layer 4 (NIST Cross-Check & Identities)**: 0 issues

| Layer | Severity | Entity | Code | Message |
|---:|---|---|---|---|
| L2 | ⚠️ WARNING | `Unit:F` | `ORPHAN_UNIT` | Unit is not referenced by any constant |
| L2 | ⚠️ WARNING | `Unit:H` | `ORPHAN_UNIT` | Unit is not referenced by any constant |
| L2 | ⚠️ WARNING | `Unit:W` | `ORPHAN_UNIT` | Unit is not referenced by any constant |
| L2 | ⚠️ WARNING | `Concept:BaseSIUnit` | `ORPHAN_CONCEPT` | Concept is neither a Quantity nor linked in concept relationships |
| L2 | ⚠️ WARNING | `Concept:Constant` | `ORPHAN_CONCEPT` | Concept is neither a Quantity nor linked in concept relationships |
| L2 | ⚠️ WARNING | `Concept:Meter` | `ORPHAN_CONCEPT` | Concept is neither a Quantity nor linked in concept relationships |
| L2 | ⚠️ WARNING | `Concept:RmsCharge` | `ORPHAN_CONCEPT` | Concept is neither a Quantity nor linked in concept relationships |
| L2 | ⚠️ WARNING | `Concept:ShieldingDifference` | `ORPHAN_CONCEPT` | Concept is neither a Quantity nor linked in concept relationships |
