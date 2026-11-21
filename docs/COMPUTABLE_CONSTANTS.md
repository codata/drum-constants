# Computable Physical Constants, Determination Roles, and Precision Model

> **Scope**: Documents the CODATA 2018–2022 determination taxonomy (`adjustment_role`), safe algebraic formulas (`formula`, `formula_tex`, `symbol_tex`, `derived_from`), the two-source precision model (`value` vs. `value_nist`, `is_truncated` vs. `is_nist_truncated`), IEEE 754 numeric storage guidance (`significant_digits`, `fits_float32`, `fits_float64`, `recommended_numeric_type`), and the historical transition from the artifact-based SI to the revised 2019 SI.

---

## 1. Historical Story: From Artifact Standards to Computable Constants

Prior to May 20, 2019, the International System of Units (SI) anchored electrical, thermal, and chemical metrology to macroscopic artifact and medium definitions alongside selected exact conventions:

- The kilogram was defined by the mass of the International Prototype of the Kilogram (IPK), forcing Planck's constant $h$ and Avogadro's constant $N_{\text{A}}$ to be determined experimentally.
- The ampere was defined via the hypothetical infinite-wire Ampère force law, fixing the vacuum magnetic permeability exactly at $\mu_0 = 4\pi \times 10^{-7}\ \text{N A}^{-2}$, and making $\varepsilon_0 = 1/(\mu_0 c^2)$ and $Z_0 = \mu_0 c$ exact while forcing the elementary charge $e$, Josephson constant $K_{\text{J}}$, and von Klitzing constant $R_{\text{K}}$ to carry measurement uncertainties.
- The kelvin was defined by the triple point of water, leaving Boltzmann's constant $k$ and the molar gas constant $R$ with experimental uncertainties.
- The mole was defined by the mass of $^{12}\text{C}$, fixing $M(^{12}\text{C}) = 12\times 10^{-3}\ \text{kg mol}^{-1}$ and $M_{\text{u}} = 10^{-3}\ \text{kg mol}^{-1}$ exactly.

In the **CODATA 2014** release ([`data/constants.yaml`](../data/constants.yaml)), only **17** of **335** constants were exact ($c$, $\mu_0$, $\varepsilon_0$, $Z_0$, $4\pi\varepsilon_0$, $M(^{12}\text{C})$, $M_{\text{u}}$, $g_n$, standard atmosphere, standard-state pressure, conventional electrical constants $K_{\text{J-90}}$ and $R_{\text{K-90}}$, and speed-based unit conversion factors).

### The 2017 Special Adjustment and May 2019 SI Redefinition

To enable the 26th General Conference on Weights and Measures (CGPM, November 2018) to redefine the SI base units, the CODATA Task Group on Fundamental Constants carried out the **CODATA 2017 Special Adjustment** (Mohr et al., 2018; Newell et al., 2018), determining the exact numerical values of $h$, $e$, $k$, and $N_{\text{A}}$ adopted by BIPM's **9th SI Brochure** effective **May 20, 2019**:

| Defining Quantity | Symbol | Fixed Exact Numerical Value | Role Transition (2014 → 2018+) |
|---|---|---|---|
| Caesium-133 hyperfine splitting | $\Delta\nu_{\text{Cs}}$ | `9192631770` Hz | Defined the second since 1967 (newly tabulated in NIST CODATA 2018+) |
| Speed of light in vacuum | $c$ | `299792458` m s$^{-1}$ | Exact since 1983 (unchanged) |
| Planck constant | $h$ | `6.62607015e-34` J s | Measured ($u_r = 1.2\times 10^{-8}$ in 2014) → **Exact defining** |
| Elementary charge | $e$ | `1.602176634e-19` C | Measured ($u_r = 6.1\times 10^{-9}$ in 2014) → **Exact defining** |
| Boltzmann constant | $k$ | `1.380649e-23` J K$^{-1}$ | Measured ($u_r = 5.7\times 10^{-7}$ in 2014) → **Exact defining** |
| Avogadro constant | $N_{\text{A}}$ | `6.02214076e23` mol$^{-1}$ | Measured ($u_r = 1.2\times 10^{-8}$ in 2014) → **Exact defining** |
| Luminous efficacy ($540\ \text{THz}$) | $K_{\text{cd}}$ | `683` lm W$^{-1}$ | Exact since 1979 (newly tabulated in NIST CODATA 2018+) |

### What Gained Exactness, What Lost Exactness, and What Collapsed in Uncertainty

Comparing **CODATA 2014** against **CODATA 2018** (Tiesinga et al., 2021) and **CODATA 2022** (Mohr et al., 2025) across [`data/constants.yaml`](../data/constants.yaml):

1. **81 exact constants (`2018` and `2022`)**:
   - **11 constants remained exact** across `2014 → 2018` (`SpeedOfLight`, `StandardAccelerationOfGravity`, `StandardAtmosphere`, `StandardStatePressure`, `ConventionalValueOfJosephsonConstant`, `ConventionalValueOfVonKlitzingConstant`, `HertzInverseMeterRelationship`, `InverseMeterHertzRelationship`, `JouleKilogramRelationship`, `KilogramJouleRelationship`, `NaturalUnitOfVelocity`).
   - **61 previously measured constants became exact** in `2018`, including `PlanckConstant`, `ElementaryCharge`, `BoltzmannConstant`, `AvogadroConstant`, `ReducedPlanckConstant` ($\hbar = h/(2\pi)$), `JosephsonConstant` ($K_{\text{J}} = 2e/h$), `VonKlitzingConstant` ($R_{\text{K}} = h/e^2$), `MagneticFluxQuantum` ($\Phi_0 = h/(2e)$), `ConductanceQuantum` ($G_0 = 2e^2/h$), `FaradayConstant` ($F = N_{\text{A}} e$), `MolarGasConstant` ($R = N_{\text{A}} k$), `MolarPlanckConstant` ($N_{\text{A}} h$), `StefanBoltzmannConstant` ($\sigma = \pi^2 k^4 / (60 \hbar^3 c^2)$), `WienWavelengthDisplacementLawConstant` ($b$), `WienFrequencyDisplacementLawConstant` ($b'$), `LoschmidtConstant`, `SackurTetrodeConstant`, and all eV/Hz/m$^{-1}$/K/kg/J energy equivalents.
   - **9 newly added constants in `2018` are exact**: `HyperfineTransitionFrequencyOfCs133`, `LuminousEfficacy`, and the 7 conventional 1990 electrical unit ratios (`ConventionalValueOfVolt90`, `Ohm90`, `Ampere90`, `Coulomb90`, `Farad90`, `Henry90`, `Watt90`). Together, $11 + 61 + 9 = 81$ exact constants in `2018` and `2022` (with **70** gaining exactness or entering as exact).

2. **6 constants lost exactness on May 20, 2019**:
   Removing the Ampère force definition of $\mu_0$ and the $^{12}\text{C}$ definition of the mole shifted 6 previously exact quantities into experimentally determined (`computed_derived`) quantities proportional to $\alpha$ or $R_\infty A_{\text{r}}(\text{e})/\alpha^2$:
   - `ElectromagneticPermeabilityOfVacuum` ($\mu_0 = 2 \alpha h / (c e^2)$)
   - `PermittivityOfVacuum` ($\varepsilon_0 = e^2 / (2 \alpha h c)$)
   - `CharacteristicImpedanceOfVacuum` ($Z_0 = 2 \alpha h / e^2$)
   - `AtomicUnitOfPermittivity` ($4\pi \varepsilon_0 = 2\pi e^2 / (\alpha h c)$)
   - `MolarMassConstant` ($M_{\text{u}} = 2 h N_{\text{A}} R_\infty A_{\text{r}}(\text{e}) / (c \alpha^2)$)
   - `MolarMassOfCarbon12` ($M(^{12}\text{C}) = 12 M_{\text{u}}$)

3. **Major uncertainty collapses & 1990 electrical units**:
   - Eliminating $h$'s experimental uncertainty collapsed the relative uncertainty of derived particle masses: for example, `ElectronMass` ($m_{\text{e}} = 2 h R_\infty / (c \alpha^2)$) improved from $u_r = 1.2 \times 10^{-8}$ (`2014`) to $u_r = 3.1 \times 10^{-10}$ (`2018`), a nearly **40-fold** reduction.
   - In 1988 (effective January 1, 1990), CIPM introduced exact conventional values $K_{\text{J-90}} = 483597.9\ \text{GHz V}^{-1}$ and $R_{\text{K-90}} = 25812.807\ \Omega$ so electrical laboratories did not depend on volatile measurements of $K_{\text{J}}$ and $R_{\text{K}}$. Because the 2019 SI fixed $K_{\text{J}} = 2e/h$ and $R_{\text{K}} = h/e^2$ exactly, the 1990 realization ratios (`V_90`, `Omega_90`, `A_90`, `C_90`, `F_90`, `H_90`, `W_90`) became exact computable constants, while pre-2019 `FaradayConstantConventionalElectricCurrent` was retired after `2014`.

---

## 2. Four-Role Adjustment Taxonomy (`adjustment_role` & `is_computed`)

Determination roles are scoped per release to `ConstantValueModel` (`codata:adjustmentRole` and `codata:isComputed` in RDF) rather than static on `ConstantModel`. This guarantees historical fidelity across the 2019 SI redefinition without anachronism:

- Constants like $h, e, k, N_{\text{A}}$ are correctly recorded as `adjusted` ($u_r > 0$) in 1998–2014 and transition to `defining` ($u_r = 0$) in 2018–2022.
- Quantities derived from them (like $F, R, \hbar, K_{\text{J}}, R_{\text{K}}$) are `computed_derived` in 1998–2014 and transition to `computed_exact` in 2018–2022.
- Conversely, former defining standards like $\mu_0$ and $M(^{12}\text{C})$ are `defining` in 1998–2014 and transition to `computed_derived` in 2018–2022, while $\varepsilon_0$ and $Z_0$ transition from `computed_exact` to `computed_derived`.

Physical laws and algebraic relationships (`symbol_tex`, `formula`, `formula_tex`, `derived_from`) remain invariant on `ConstantModel` (`codata:Constant`).

| Role (`adjustment_role`) | Active (`2022`) | Historical (`2014`) | Exact (`is_exact`) | Has Formula? | Metrological Meaning |
|---|---:|---:|:---:|:---:|---|
| `defining` | 12 | 9 | `true` | `false` | Independent exact SI defining constants (7), exact conventional CIPM values ($K_{\text{J-90}}, R_{\text{K-90}}$), and exact reference standards ($g_n$, atm, 100 kPa). |
| `computed_exact` | 69 | 8 | `true` | `true` | Exact algebraic functions of `defining` constants (and $\pi$ or Wien roots $x_\lambda, x_\nu$); zero uncertainty since May 20, 2019. |
| `adjusted` | 32 | 23 | `false` | `false` | Independent CODATA least-squares adjustment (LSA) variables and PDG/theoretical inputs ($\alpha$, $R_\infty$, $A_{\text{r}}(X)$, $m_W/m_Z$, $G$, $G_{\text{F}}$, $r_{\text{p}}$, $\mu_\mu/\mu_{\text{p}}$, etc.). In pre-2019, included $h, e, k, N_{\text{A}}$. |
| `computed_derived` | 242 | 295 | `false` | `true` | Algebraically derived from `defining` + `adjusted` constants (e.g., $m_{\text{e}}$, $a_0$, $E_{\text{h}}$, $\mu_0$, $\mu_{\text{B}}$, $M_{\text{u}}$); carries propagated uncertainty $u > 0$. |
| *Deprecated (`null`)* | 4 (absent) | Historical | Historical | Optional | Retired in or before `2022` (`FaradayConstantConventionalElectricCurrent`, `MolarPlanckConstantTimesC`, `TritonElectronMagneticMomentRatio`, `TritonNeutronMagneticMomentRatio`). |

### Algebraic Formula Representation & Safe AST Grammar

Each constant (`defining`/`adjusted`/`computed_*`) documents optional metadata on `ConstantModel`:

- `symbol_tex` (`codata:hasSymbol`): Standard LaTeX symbol (e.g., `\hbar`, `K_{\text{J}}`, `\alpha`).
- `formula` (`codata:formula`): Safe Python/SymPy-compatible algebraic expression referencing canonical `Constant.id` identifiers (evaluated without `eval()` via AST traversal in [`utils/formulas.py`](../utils/formulas.py)). Allowed operators are `+`, `-`, `*`, `/`, `**`, unary `+`/`-`, functions `sqrt()`, `ln()`, `abs()`, and math constants `pi`, `wien_x_wavelength` ($x_5$ solving $x = 5(1 - e^{-x})$), and `wien_x_frequency` ($x_3$ solving $x = 3(1 - e^{-x})$).
- `formula_tex` (`codata:formulaLatex`): Display LaTeX formula.
- `derived_from` (`codata:derivedFrom`): Dynamically extracted sorted list of input `Constant.id` dependencies (`computed_field`), validated acyclic across the entire 359-constant graph by Layer 2 validation.

---

## 3. Two-Source Precision Model (`value` vs. `value_nist`)

NIST ASCII tables (SP 961 / SP 959 / SRD 121) print exact computable constants (`computed_exact`) to ~10–12 digits followed by an ellipsis (`...`), using strict truncation (`ROUND_DOWN`) even when the rational expansion is exact and terminating—or when IEEE 754 `decimal128` (34 digits) provides substantially more digits.

To preserve **100% NIST traceability** while giving consumers the **highest mathematically valid precision**, `drum-constants` (`schema_version: "0.4.0"`) uses a two-source model on `ConstantValueModel`:

| Field | RDF Property | Role |
|---|---|---|
| `value` | `codata:value`, `codata:valueDecimal`, `codata:valueFloat` | Primary highest mathematically valid canonical string (`34` sig. digits for non-terminating exact constants; complete decimal expansion for terminating exact rationals; verbatim NIST string otherwise). |
| `value_nist` | `codata:nistValue` | Preserves the exact original NIST ASCII table string (with spaces stripped) whenever `value_source == "computed"`; omitted when `value_source == "nist"`. |
| `value_source` | `codata:valueSource` | `"computed"` (`124` entries across `2018` + `2022`: `62` per release) or `"nist"` (`2,189` entries). |
| `is_truncated` | `codata:isTruncated` | `true` only if `value` itself remains truncated (irrational or infinite repeating rational); `false` once a terminating rational expansion is recovered in full. |
| `is_nist_truncated` | `codata:isNistTruncated` | Tracks faithfully whether the original NIST source line ended in `...` (audited 1:1 against raw `nist/<year>/allascii_<year>.json` in Layer 4 validation). |
| `nist_exponent` | `codata:nistExponent` | Renamed from `exponent` to clarify that it reflects NIST's display table grouping scale factor (`codata:nistExponent`). |

### Exact Rational Cancellation: 10 Terminating Rationals Recovered (`20` Across `2018` + `2022`)

Using topological exact `fractions.Fraction` propagation (`evaluate_exact_dag` in [`utils/formulas.py`](../utils/formulas.py)), pure-rational formulas whose reduced denominator is of the form $2^a \cdot 5^b$ yield **complete, un-truncated terminating decimals** (`is_truncated: false`, `is_nist_truncated: true`):

- Notably, `JosephsonConstant` ($K_{\text{J}} = 2e/h$) and `VonKlitzingConstant` ($R_{\text{K}} = h/e^2$) individually have infinite repeating decimal expansions, yet in `ConventionalValueOfAmpere90` and `ConventionalValueOfCoulomb90` the product $K_{\text{J}} R_{\text{K}} = 2/e$ cancels $h$, and $1/e = 10^{19}/1.602176634$ cancels cleanly with $(K_{\text{J-90}} R_{\text{K-90}})$ to yield the exact 24-digit decimal `1.00000008887143810491801` (`ConventionalValueOfWatt90` similarly recovers its exact 32-digit expansion `1.0000001955365548349899359182625` via $K_{\text{J}}^2 R_{\text{K}} = 4/h$).
- In total, **10 constants per release (`2018` and `2022`)**—`ConventionalValueOfAmpere90`, `ConventionalValueOfCoulomb90`, `ConventionalValueOfWatt90`, `FaradayConstant`, `FirstRadiationConstantForSpectralRadiance`, `InverseMeterJouleRelationship`, `KilogramJouleRelationship`, `MolarGasConstant`, `MolarPlanckConstant`, and `MolarVolumeOfIdealGas`—recover their complete exact decimal expansions, while the remaining **52 constants per release (`2018` and `2022`)** are truncated (`ROUND_DOWN`) to **34 significant digits** (IEEE 754 `decimal128`).

> **Arbitrary-Precision `Decimal` Trap**: Python's default `decimal` context precision is `28`. Any arithmetic or `.normalize()` / `.scaleb()` call on 34-digit constants must use `decimal.localcontext()` with `prec >= 100`. Both `utils/formulas.py` and `utils/package.py` enforce this rule.

---

## 4. Significant Digits & IEEE 754 Numeric Storage Sufficiency

Every `ConstantValueModel` exposes four read-only computed helpers (exported to JSON, CSV, and RDF, omitted from YAML):

- `significant_digits` (`codata:significantDigits`, `xsd:integer`): Significant decimal digits in `value` preserving significant trailing zeros (leading zeros excluded).
- `fits_float32` (`codata:fitsFloat32`, `xsd:boolean`): `True` only when `not is_truncated`, finite within IEEE 754 binary32 normal range ($1.17549435\ldots\times 10^{-38} \le |x| \le \text{FLT\_MAX}$), and uniquely recoverable from `float32` at the value's decimal precision (checked in [`utils/formulas.py`](../utils/formulas.py) via big-endian IEEE 754 packing `struct.pack(">f", float(d))` and verifying `f32` distinguishes `d` from `d ± step` and quantizes back to `d`).
- `fits_float64` (`codata:fitsFloat64`, `xsd:boolean`): `True` only when `not is_truncated`, finite within IEEE 754 binary64 normal range ($2.22507385\ldots\times 10^{-308} \le |x| \le \text{DBL\_MAX}$), and round-tripping shortest decimal string (`Decimal(str(float(d))) == d`).
- `recommended_numeric_type` (`codata:recommendedNumericType`, `xsd:string`): `"float32"`, `"float64"`, or `"decimal"`.

In CODATA `2022` (355 values), **36** values (`10.1%`) fit cleanly in `float32`, **258** values (`72.7%`) require `float64`, and **61** values (`17.2%`) require arbitrary-precision `decimal` (**52** truncated exact expansions plus **9** terminating exact rationals with 17–32 digits; only 15-digit `MolarGasConstant` among the 10 recovered terminating exact constants fits in `float64`). Converting any of those 61 constants via IEEE 754 `double` silently introduces rounding error.

---

## 5. Primary Bibliographic References

1. **CODATA 2022 Adjustment**: Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2025). *"CODATA recommended values of the fundamental physical constants: 2022."* Reviews of Modern Physics, 97(2), 025002. DOI: `10.1103/RevModPhys.97.025002`.
2. **CODATA 2018 Adjustment**: Tiesinga, E., Mohr, P. J., Newell, D. B., & Taylor, B. N. (2021). *"CODATA recommended values of the fundamental physical constants: 2018."* Reviews of Modern Physics, 93(2), 025010; Journal of Physical and Chemical Reference Data, 50(3), 033105. DOI: `10.1103/RevModPhys.93.025010`.
3. **NIST Fundamental Physical Constants Publications**: NIST Special Publication 961 (May 2024), NIST Special Publication 959 (May 2024), and NIST Standard Reference Database 121 (`https://physics.nist.gov/cuu/Constants/`).
4. **SI Redefinition & 9th SI Brochure**: BIPM (2019). *The International System of Units (SI)*, 9th Edition (`https://www.bipm.org/en/publications/si-brochure`).
5. **CODATA 2017 Special Adjustment**:
   - Mohr, P. J., Newell, D. B., Taylor, B. N., & Tiesinga, E. (2018). *"Data and analysis for the CODATA 2017 special fundamental constants adjustment."* Metrologia, 55(1), 125–146.
   - Newell, D. B., Cabiati, F., Fischer, J., Fujii, K., Karshenboim, S. G., Margolis, H. S., de Mirandés, E., Mohr, P. J., Nez, F., Pachucki, K., Quinn, T. J., Taylor, B. N., Wang, M., Wood, B. M., & Zhang, Z. (2018). *"The CODATA 2017 values of h, e, k, and N_A for the revision of the SI."* Metrologia, 55(1), L13–L16.
