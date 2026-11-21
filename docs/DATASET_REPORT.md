# CODATA DRUM Constants — Dataset & Validation Report

> **Validation Status**: ⚠️ PASS WITH WARNINGS (0 errors, 8 warnings)  
> **Latest CODATA Release**: `2022`  
> **Schema Version**: `0.4.0`

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
| Formula DAG Checks Passed | 380 / 380 |
| Computed-Exact Upgrades (`value_source=computed`) | 124 (62 in `2022`) |
| Terminating Exact Rationals Recovered | 20 (10 in `2022`) |
| Validation Errors | 0 |
| Validation Warnings | 8 |

## 2. CODATA Release Coverage Matrix

| Release | Published | Constants | Exact | Measured | Truncated (DRUM) | NIST Truncated | Computed Upgrades | Added vs Prev | Retired vs Prev |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `2022` | 2024-05-09 | 355 | 81 | 274 | 52 | 62 | 62 | 1 | 0 |
| `2018` | 2019-05-20 | 354 | 81 | 273 | 52 | 62 | 62 | 21 | 2 |
| `2014` | 2015-06-15 | 335 | 17 | 318 | 7 | 7 | 0 | 0 | 0 |
| `2010` | 2011-06-02 | 335 | 17 | 318 | 7 | 7 | 0 | 14 | 3 |
| `2006` | 2007-03-07 | 324 | 16 | 308 | 7 | 7 | 0 | 17 | 0 |
| `2002` | 2003-12-09 | 307 | 16 | 291 | 7 | 7 | 0 | 4 | 0 |
| `1998` | 1999-07-23 | 303 | 16 | 287 | 4 | 4 | 0 | — | — |

## 3. Determination Role Breakdown (`2022`)

| Role (`adjustment_role`) | Active Count | Share | Exact (`is_exact`) | Semantic Description |
|---|---:|---:|:---:|---|
| `defining` | 12 | 3.4% | Yes | Exact SI defining & conventional baseline constants (`u = 0`, independent) |
| `computed_exact` | 69 | 19.4% | Yes | Exact algebraic functions of SI defining constants & π / Wien roots (`u = 0` since May 2019) |
| `adjusted` | 32 | 9.0% | No | Independent CODATA least-squares adjustment (LSA) & theoretical input variables (`u > 0`) |
| `computed_derived` | 242 | 68.2% | No | Algebraically derived from defining + adjusted constants (`u > 0`) |
| *Deprecated (absent in `2022`)* | 4 | — | Historical | Retired in or before `2022` (`adjustment_role: null`) |

### Historical Shift Across SI Regimes (2014 Pre-2019 vs 2022 Current SI)

Because `adjustment_role` and `is_computed` are scoped to `ConstantValue` per release rather than static on `Constant`, the 2019 SI redefinition is represented with historical fidelity across CODATA adjustments:

| Role (`adjustment_role`) | 2014 (Pre-2019 SI) | 2022 (Current SI) | Net Change | Key Metrological Transitions |
|---|---:|---:|---:|---|
| `defining` | 9 | 12 | +3 | $h, e, k, N_{\text{A}}$ became defining; $\mu_0, M(^{12}\text{C}), M_{\text{u}}$ lost defining status |
| `computed_exact` | 8 | 69 | +61 | $F, R, \hbar, K_{\text{J}}, R_{\text{K}}, c_1, c_2, \sigma$ gained exactness; $\varepsilon_0, Z_0, 4\pi\varepsilon_0$ lost exactness |
| `adjusted` | 23 | 32 | +9 | Primary experimental least-squares adjustment inputs |
| `computed_derived` | 295 | 242 | -53 | Quantities derived from adjusted inputs with propagated uncertainty |

## 4. Two-Source Precision Upgrades & IEEE 754 Storage Sufficiency

When NIST SP 961 / SRD 121 truncates an exact constant (`is_nist_truncated: true`) with `...`, `drum-constants` retains the verbatim NIST string in `value_nist` and elevates `value` to either its complete terminating rational expansion (`is_truncated: false`, **10** constants in `2022`) or its 34-significant-digit IEEE 754 `decimal128` truncation (`is_truncated: true`, **52** constants in `2022`).

| Recommended Numeric Type | `2022` Values | Share (`2022`) | All Releases | Storage Precision Requirement |
|---|---:|---:|---:|---|
| `float32` | 36 | 10.1% | 294 | IEEE 754 binary32 (`24`-bit significand, ~6-7 exact decimal digits) |
| `float64` | 258 | 72.7% | 1865 | IEEE 754 binary64 (`53`-bit significand, ~15-17 exact decimal digits) |
| `decimal` | 61 | 17.2% | 154 | Arbitrary-precision Decimal / BigDecimal (`> float64` precision or infinite expansion) |

### Terminating Exact Rationals Recovered in `2022` (10 constants)

| Constant ID | Formula | NIST Truncated (`value_nist`) | Exact Value (`value`) | Digits |
|---|---|---|---|---:|
| `ConventionalValueOfAmpere90` | `(ConventionalValueOfJosephsonConstant * ConventionalValueOfVonKlitzingConstant) / (JosephsonConstant * VonKlitzingConstant)` | `1.00000008887` | `1.00000008887143810491801` | 24 |
| `ConventionalValueOfCoulomb90` | `(ConventionalValueOfJosephsonConstant * ConventionalValueOfVonKlitzingConstant) / (JosephsonConstant * VonKlitzingConstant)` | `1.00000008887` | `1.00000008887143810491801` | 24 |
| `ConventionalValueOfWatt90` | `(ConventionalValueOfJosephsonConstant**2 * ConventionalValueOfVonKlitzingConstant) / (JosephsonConstant**2 * VonKlitzingConstant)` | `1.00000019553` | `1.0000001955365548349899359182625` | 32 |
| `FaradayConstant` | `AvogadroConstant * ElementaryCharge` | `96485.33212` | `96485.3321233100184` | 18 |
| `FirstRadiationConstantForSpectralRadiance` | `2 * PlanckConstant * SpeedOfLight**2` | `1.191042972e-16` | `1.1910429723971884140794892e-16` | 26 |
| `InverseMeterJouleRelationship` | `PlanckConstant * SpeedOfLight` | `1.986445857e-25` | `1.9864458571489287e-25` | 17 |
| `KilogramJouleRelationship` | `SpeedOfLight**2` | `8.987551787e16` | `8.9875517873681764e16` | 17 |
| `MolarGasConstant` | `AvogadroConstant * BoltzmannConstant` | `8.314462618` | `8.31446261815324` | 15 |
| `MolarPlanckConstant` | `AvogadroConstant * PlanckConstant` | `3.990312712e-10` | `3.9903127128934314e-10` | 17 |
| `MolarVolumeOfIdealGas` | `MolarGasConstant * 273.15 / StandardStatePressure` | `22.71095464e-3` | `2.271095464148557506e-2` | 19 |

<details><summary>All 62 computed-exact precision upgrades in 2022</summary>

| Constant ID | Source | NIST (`value_nist`) | Primary (`value`) | Sig. Digits | NIST Trunc. | DRUM Trunc. | Storage |
|---|---|---|---|---:|:---:|:---:|---|
| `AtomicUnitOfAction` | `computed` | `1.054571817e-34` | `1.05457181764615639126242800330228e-34` | 33 | True | True | `decimal` |
| `BoltzmannConstantInEVPerK` | `computed` | `8.617333262e-5` | `8.617333262145177433663659334080639e-5` | 34 | True | True | `decimal` |
| `BoltzmannConstantInHzPerK` | `computed` | `2.083661912e10` | `2.083661912332757298079616618607637e10` | 34 | True | True | `decimal` |
| `BoltzmannConstantInInverseMetersPerKelvin` | `computed` | `69.50348004` | `69.50348004861274055398740613440106` | 34 | True | True | `decimal` |
| `ConductanceQuantum` | `computed` | `7.748091729e-5` | `7.748091729863650646680823323308763e-5` | 34 | True | True | `decimal` |
| `ConventionalValueOfAmpere90` | `computed` | `1.00000008887` | `1.00000008887143810491801` | 24 | True | False | `decimal` |
| `ConventionalValueOfCoulomb90` | `computed` | `1.00000008887` | `1.00000008887143810491801` | 24 | True | False | `decimal` |
| `ConventionalValueOfFarad90` | `computed` | `0.99999998220` | `0.9999999822063327522909864152283386` | 34 | True | True | `decimal` |
| `ConventionalValueOfHenry90` | `computed` | `1.00000001779` | `1.000000017793667564323613340698957` | 34 | True | True | `decimal` |
| `ConventionalValueOfOhm90` | `computed` | `1.00000001779` | `1.000000017793667564323613340698957` | 34 | True | True | `decimal` |
| `ConventionalValueOfVolt90` | `computed` | `1.00000010666` | `1.000000106665107250590448942972164` | 34 | True | True | `decimal` |
| `ConventionalValueOfWatt90` | `computed` | `1.00000019553` | `1.0000001955365548349899359182625` | 32 | True | False | `decimal` |
| `ElectronVoltHertzRelationship` | `computed` | `2.417989242e14` | `2.41798924208491816223829142527264e14` | 33 | True | True | `decimal` |
| `ElectronVoltInverseMeterRelationship` | `computed` | `8.065543937e5` | `8.065543937349211641069007230570959e5` | 34 | True | True | `decimal` |
| `ElectronVoltKelvinRelationship` | `computed` | `1.160451812e4` | `11604.51812155008260607873543529166` | 34 | True | True | `decimal` |
| `ElectronVoltKilogramRelationship` | `computed` | `1.782661921e-36` | `1.782661921627897703181040761893362e-36` | 34 | True | True | `decimal` |
| `ElementaryChargeOverH` | `computed` | `1.519267447e15` | `1.519267447878626201250234970894513e15` | 34 | True | True | `decimal` |
| `FaradayConstant` | `computed` | `96485.33212` | `96485.3321233100184` | 18 | True | False | `decimal` |
| `FirstRadiationConstant` | `computed` | `3.741771852e-16` | `3.741771852192758011367155555929985e-16` | 34 | True | True | `decimal` |
| `FirstRadiationConstantForSpectralRadiance` | `computed` | `1.191042972e-16` | `1.1910429723971884140794892e-16` | 26 | True | False | `decimal` |
| `HertzElectronVoltRelationship` | `computed` | `4.135667696e-15` | `4.135667696923858646162230824294994e-15` | 34 | True | True | `decimal` |
| `HertzInverseMeterRelationship` | `computed` | `3.335640951e-9` | `3.335640951981520495755767144749185e-9` | 34 | True | True | `decimal` |
| `HertzKelvinRelationship` | `computed` | `4.799243073e-11` | `4.799243073366221248123165265031155e-11` | 34 | True | True | `decimal` |
| `HertzKilogramRelationship` | `computed` | `7.372497323e-51` | `7.372497323812707892918537119493948e-51` | 34 | True | True | `decimal` |
| `InverseMeterElectronVoltRelationship` | `computed` | `1.239841984e-6` | `1.239841984332002622377527445578762e-6` | 34 | True | True | `decimal` |
| `InverseMeterJouleRelationship` | `computed` | `1.986445857e-25` | `1.9864458571489287e-25` | 17 | True | False | `decimal` |
| `InverseMeterKelvinRelationship` | `computed` | `1.438776877e-2` | `1.438776877503933802146671601543911e-2` | 34 | True | True | `decimal` |
| `InverseMeterKilogramRelationship` | `computed` | `2.210219094e-42` | `2.21021909430423363085404903681733e-42` | 33 | True | True | `decimal` |
| `InverseOfConductanceQuantum` | `computed` | `12906.40372` | `12906.40372965225333002275835304372` | 34 | True | True | `decimal` |
| `JosephsonConstant` | `computed` | `483597.8484e9` | `4.835978484169836324476582850545281e14` | 34 | True | True | `decimal` |
| `JouleElectronVoltRelationship` | `computed` | `6.241509074e18` | `6.241509074460762607776240980930445e18` | 34 | True | True | `decimal` |
| `JouleHertzRelationship` | `computed` | `1.509190179e33` | `1.50919017964215184169156434300654e33` | 33 | True | True | `decimal` |
| `JouleInverseMeterRelationship` | `computed` | `5.034116567e24` | `5.034116567542709302218551285257952e24` | 34 | True | True | `decimal` |
| `JouleKelvinRelationship` | `computed` | `7.242970516e22` | `7.242970516039920356296205625035762e22` | 34 | True | True | `decimal` |
| `JouleKilogramRelationship` | `computed` | `1.112650056e-17` | `1.112650056053618432174089964848009e-17` | 34 | True | True | `decimal` |
| `KelvinElectronVoltRelationship` | `computed` | `8.617333262e-5` | `8.617333262145177433663659334080639e-5` | 34 | True | True | `decimal` |
| `KelvinHertzRelationship` | `computed` | `2.083661912e10` | `2.083661912332757298079616618607637e10` | 34 | True | True | `decimal` |
| `KelvinInverseMeterRelationship` | `computed` | `69.50348004` | `69.50348004861274055398740613440106` | 34 | True | True | `decimal` |
| `KelvinKilogramRelationship` | `computed` | `1.536179187e-40` | `1.53617918724037223476272513587744e-40` | 33 | True | True | `decimal` |
| `KilogramElectronVoltRelationship` | `computed` | `5.609588603e35` | `5.609588603804451937850443024248973e35` | 34 | True | True | `decimal` |
| `KilogramHertzRelationship` | `computed` | `1.356392489e50` | `1.356392489652132101257636096714128e50` | 34 | True | True | `decimal` |
| `KilogramInverseMeterRelationship` | `computed` | `4.524438335e41` | `4.524438335443822610299409522550859e41` | 34 | True | True | `decimal` |
| `KilogramJouleRelationship` | `computed` | `8.987551787e16` | `8.9875517873681764e16` | 17 | True | False | `decimal` |
| `KilogramKelvinRelationship` | `computed` | `6.509657260e39` | `6.509657260728958917146935969967747e39` | 34 | True | True | `decimal` |
| `LoschmidtConstant` | `computed` | `2.651645804e25` | `2.651645804883734342411204695235497e25` | 34 | True | True | `decimal` |
| `LoschmidtConstant273K101KPa` | `computed` | `2.686780111e25` | `2.686780111798443822448153157447368e25` | 34 | True | True | `decimal` |
| `MagneticFluxQuantum` | `computed` | `2.067833848e-15` | `2.067833848461929323081115412147497e-15` | 34 | True | True | `decimal` |
| `MolarGasConstant` | `computed` | `8.314462618` | `8.31446261815324` | 15 | True | False | `float64` |
| `MolarPlanckConstant` | `computed` | `3.990312712e-10` | `3.9903127128934314e-10` | 17 | True | False | `decimal` |
| `MolarVolumeOfIdealGas` | `computed` | `22.71095464e-3` | `2.271095464148557506e-2` | 19 | True | False | `decimal` |
| `MolarVolumeOfIdealGas273K101KPa` | `computed` | `22.41396954e-3` | `2.241396954501413773501110288675055e-2` | 34 | True | True | `decimal` |
| `NaturalUnitOfAction` | `computed` | `1.054571817e-34` | `1.05457181764615639126242800330228e-34` | 33 | True | True | `decimal` |
| `NaturalUnitOfActionInEVS` | `computed` | `6.582119569e-16` | `6.582119569509065698073512182441931e-16` | 34 | True | True | `decimal` |
| `PlanckConstantInEVS` | `computed` | `4.135667696e-15` | `4.135667696923858646162230824294994e-15` | 34 | True | True | `decimal` |
| `ReducedPlanckConstant` | `computed` | `1.054571817e-34` | `1.05457181764615639126242800330228e-34` | 33 | True | True | `decimal` |
| `ReducedPlanckConstantInEVS` | `computed` | `6.582119569e-16` | `6.582119569509065698073512182441931e-16` | 34 | True | True | `decimal` |
| `ReducedPlanckConstantTimesCInMeVFm` | `computed` | `197.3269804` | `197.3269804593024658908944081867211` | 34 | True | True | `decimal` |
| `SecondRadiationConstant` | `computed` | `1.438776877e-2` | `1.438776877503933802146671601543911e-2` | 34 | True | True | `decimal` |
| `StefanBoltzmannConstant` | `computed` | `5.670374419e-8` | `5.67037441918442945397099673188923e-8` | 33 | True | True | `decimal` |
| `VonKlitzingConstant` | `computed` | `25812.80745` | `25812.80745930450666004551670608744` | 34 | True | True | `decimal` |
| `WienFrequencyDisplacementLawConstant` | `computed` | `5.878925757e10` | `5.878925757646824946606130795309721e10` | 34 | True | True | `decimal` |
| `WienWavelengthDisplacementLawConstant` | `computed` | `2.897771955e-3` | `2.897771955185172661478605448092884e-3` | 34 | True | True | `decimal` |

</details>

## 5. External Vocabulary & Curation Coverage

| Alignment / Field | Entity Scope | Mapped | Total | Coverage | Progress |
|---|---|---:|---:|---:|---|
| NIST Identifiers | Constants | 359 | 359 | 100.0% | `████████████` |
| QUDT Constants (`qudt_id`) | Constants | 325 | 359 | 90.5% | `███████████░` |
| SI Digital Framework (`si_id`) | Constants | 7 | 359 | 1.9% | `░░░░░░░░░░░░` |
| UCUM Constant Codes (`ucum_id`) | Constants | 11 | 359 | 3.1% | `░░░░░░░░░░░░` |
| French Labels (`name_fr`) | Constants | 359 | 359 | 100.0% | `████████████` |
| LaTeX Symbols (`symbol_tex`) | Constants | 359 | 359 | 100.0% | `████████████` |
| Computable Formulas (`formula`) | Constants | 315 | 359 | 87.7% | `███████████░` |
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

## 6. Deprecated Constants (Absent in `2022`)

| Constant ID | Name | NIST ID | Active Releases | Last Release |
|---|---|---|---|---|
| `FaradayConstantConventionalElectricCurrent` | Faraday Constant For Conventional Electric Current | `f90` | 1998, 2002, 2006, 2010, 2014 | `2014` |
| `MolarPlanckConstantTimesC` | Molar Planck Constant Times C | `nahc` | 1998, 2002, 2006, 2010, 2014 | `2014` |
| `TritonElectronMagneticMomentRatio` | Triton - Electron Magnetic Moment Ratio | `mutsmuem` | 2006 | `2006` |
| `TritonNeutronMagneticMomentRatio` | Triton - Neutron Magnetic Moment Ratio | `mutsmunn` | 2006 | `2006` |

## 7. Formula DAG & Metrological Identity Verification (`2022`)

All **380 / 380** formula evaluations across exact (`evaluate_exact_dag`) and derived (`evaluate_formula_decimal`) constants passed Layer 4 consistency checks, alongside key metrological identity anchors:

| Check | Formula | CODATA Value | Computed | Rel. Error | Tolerance | Status |
|---|---|---:|---:|---:|---:|---|
| Speed of Light (exact) | `c == 299792458` | `299792458` | `299792458` | `0.00e+00` | `1e-15` | ✅ PASS |
| Planck Constant (exact) | `h == 6.62607015e-34` | `6.62607015e-34` | `6.62607015e-34` | `0.00e+00` | `1e-15` | ✅ PASS |
| Elementary Charge (exact) | `e == 1.602176634e-19` | `1.602176634e-19` | `1.602176634e-19` | `0.00e+00` | `1e-15` | ✅ PASS |
| Boltzmann Constant (exact) | `k == 1.380649e-23` | `1.380649e-23` | `1.380649e-23` | `0.00e+00` | `1e-15` | ✅ PASS |
| Avogadro Constant (exact) | `N_A == 6.02214076e23` | `6.02214076e+23` | `6.02214076e+23` | `0.00e+00` | `1e-15` | ✅ PASS |
| Molar Gas Constant | `R = k * N_A` | `8.31446261815` | `8.31446261815` | `0.00e+00` | `1e-09` | ✅ PASS |
| Faraday Constant | `F = N_A * e` | `96485.3321233` | `96485.3321233` | `0.00e+00` | `1e-09` | ✅ PASS |
| Hartree Energy (Rydberg) | `E_h = 2 * R_inf * h * c` | `4.35974472221e-18` | `4.35974472221e-18` | `5.12e-15` | `1e-09` | ✅ PASS |
| Hartree Energy (Fine Structure) | `E_h = alpha^2 * m_e * c^2` | `4.35974472221e-18` | `4.35974472216e-18` | `1.08e-11` | `1e-09` | ✅ PASS |

## 8. Validation Audit

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

## 9. Primary Bibliographic References

- **CODATA 2022 Adjustment**: Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2025). "CODATA recommended values of the fundamental physical constants: 2022." *Reviews of Modern Physics*, 97(2), 025002. DOI: `10.1103/RevModPhys.97.025002`
- **CODATA 2018 Adjustment**: Tiesinga, E., Mohr, P. J., Newell, D. B., & Taylor, B. N. (2021). "CODATA recommended values of the fundamental physical constants: 2018." *Reviews of Modern Physics*, 93(2), 025010 / *Journal of Physical and Chemical Reference Data*, 50(3), 033105. DOI: `10.1103/RevModPhys.93.025010`
- **NIST 2022 Reference Publications**: NIST Special Publication 961 (May 2024), NIST Special Publication 959 (May 2024), and NIST Standard Reference Database 121 (`https://physics.nist.gov/cuu/Constants/`).
- **SI Redefinition & BIPM 9th Brochure**: BIPM (2019). *The International System of Units (SI)*, 9th ed.; Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2018). "Data and analysis for the CODATA 2017 special fundamental constants adjustment." *Metrologia*, 55(1), 125; Newell, D. B., et al. (2018). "The CODATA 2017 values of h, e, k, and N_A for the revision of the SI." *Metrologia*, 55(1), L13.
