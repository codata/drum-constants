"""Safe mathematical formula parser, arbitrary-precision evaluator, and IEEE 754 precision helpers."""

from __future__ import annotations

import ast
import math
import struct
from decimal import ROUND_DOWN, Decimal, localcontext
from fractions import Fraction
from functools import cache
from typing import Literal

_ALLOWED_MATH_CONSTANTS = {"pi", "wien_x_wavelength", "wien_x_frequency"}
_ALLOWED_FUNCTIONS = {"sqrt", "ln", "abs"}
_FLOAT32_MIN_NORMAL = 1.1754943508222875e-38
_FLOAT64_MIN_NORMAL = 2.2250738585072014e-308


@cache
def _compute_pi_70() -> Decimal:
    """Compute pi to 70+ digits via Machin's formula: pi/4 = 4*atan(1/5) - atan(1/239)."""
    with localcontext() as ctx:
        ctx.prec = 90

        def _atan_inv(m: int) -> Decimal:
            m2 = m * m
            term = Decimal(1) / Decimal(m)
            total = term
            k = 1
            sign = -1
            while True:
                term /= Decimal(m2)
                delta = term / Decimal(2 * k + 1)
                if delta == 0:
                    break
                total += sign * delta
                sign = -sign
                k += 1
            return total

        pi_val = Decimal(4) * (Decimal(4) * _atan_inv(5) - _atan_inv(239))
        return +pi_val


@cache
def _solve_wien_root(coeff: int, initial_guess: str) -> Decimal:
    """Solve x - coeff * (1 - exp(-x)) = 0 to 80+ digits using Newton-Raphson."""
    with localcontext() as ctx:
        ctx.prec = 90
        x = Decimal(initial_guess)
        c = Decimal(coeff)
        for _ in range(30):
            ex = (-x).exp()
            fx = x - c * (Decimal(1) - ex)
            dfx = Decimal(1) - c * ex
            step = fx / dfx
            x -= step
            if abs(step) < Decimal("1e-85"):
                break
        return +x


def get_math_constants(prec: int = 80) -> dict[str, Decimal]:
    """Return high-precision Decimal mathematical constants used in CODATA formulas."""
    with localcontext() as ctx:
        ctx.prec = prec
        return {
            "pi": +_compute_pi_70(),
            "wien_x_wavelength": +_solve_wien_root(5, "4.9651142317442763"),
            "wien_x_frequency": +_solve_wien_root(3, "2.8214393721220789"),
        }


def _parse_ast(formula: str) -> ast.Expression:
    """Parse a formula string into a validated AST expression."""
    if not formula or not formula.strip():
        raise ValueError("Formula cannot be empty")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula syntax: {exc.msg}") from exc
    _validate_ast_node(tree.body)
    return tree


def _validate_ast_node(node: ast.AST) -> None:
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            raise ValueError(f"Unsupported binary operator in formula: {type(node.op).__name__}")
        _validate_ast_node(node.left)
        _validate_ast_node(node.right)
        return
    if isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, (ast.UAdd, ast.USub)):
            raise ValueError(f"Unsupported unary operator in formula: {type(node.op).__name__}")
        _validate_ast_node(node.operand)
        return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
            func_name = node.func.id if isinstance(node.func, ast.Name) else type(node.func).__name__
            raise ValueError(f"Unsupported function in formula: {func_name!r}")
        if node.keywords or len(node.args) != 1:
            raise ValueError(f"Function {node.func.id!r} requires exactly 1 positional argument")
        _validate_ast_node(node.args[0])
        return
    if isinstance(node, ast.Name):
        if node.id.startswith("_"):
            raise ValueError(f"Invalid identifier in formula: {node.id!r}")
        return
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError(f"Unsupported constant literal in formula: {node.value!r}")
        return
    raise ValueError(f"Unsupported expression construct in formula: {type(node).__name__}")


def validate_formula_syntax(formula: str) -> None:
    """Validate that a formula conforms to the safe CODATA algebraic grammar."""
    _parse_ast(formula)


def extract_dependencies(formula: str | None) -> list[str]:
    """Return sorted unique Constant.id names referenced in a formula expression."""
    if not formula or not formula.strip():
        return []
    tree = _parse_ast(formula)
    deps: set[str] = set()

    def _walk(node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            if node.id not in _ALLOWED_MATH_CONSTANTS and node.id not in _ALLOWED_FUNCTIONS:
                deps.add(node.id)
        elif isinstance(node, ast.Call):
            for arg in node.args:
                _walk(arg)
        else:
            for child in ast.iter_child_nodes(node):
                _walk(child)

    _walk(tree.body)
    return sorted(deps)


def _is_pure_rational_ast(node: ast.AST, rational_ids: set[str] | None = None) -> bool:
    """Return True if an AST contains only rational arithmetic on rational constants and integer powers."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float)) and not isinstance(node.value, bool)
    if isinstance(node, ast.Name):
        if node.id in _ALLOWED_MATH_CONSTANTS:
            return False
        return rational_ids is None or node.id in rational_ids
    if isinstance(node, ast.UnaryOp):
        return _is_pure_rational_ast(node.operand, rational_ids)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "abs":
            return _is_pure_rational_ast(node.args[0], rational_ids)
        return False
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            return (
                _is_pure_rational_ast(node.left, rational_ids)
                and isinstance(node.right, ast.Constant)
                and isinstance(node.right.value, int)
                and not isinstance(node.right.value, bool)
            )
        return _is_pure_rational_ast(node.left, rational_ids) and _is_pure_rational_ast(node.right, rational_ids)
    return False


def _eval_fraction_node(node: ast.AST, values_by_id: dict[str, str | Fraction]) -> Fraction:
    if isinstance(node, ast.Constant):
        return Fraction(Decimal(str(node.value)))
    if isinstance(node, ast.Name):
        if node.id not in values_by_id:
            raise KeyError(f"Missing constant value for {node.id!r}")
        raw = values_by_id[node.id]
        return raw if isinstance(raw, Fraction) else Fraction(Decimal(raw))
    if isinstance(node, ast.UnaryOp):
        operand = _eval_fraction_node(node.operand, values_by_id)
        return -operand if isinstance(node.op, ast.USub) else operand
    if isinstance(node, ast.Call):
        assert isinstance(node.func, ast.Name) and node.func.id == "abs"
        return abs(_eval_fraction_node(node.args[0], values_by_id))
    if isinstance(node, ast.BinOp):
        left = _eval_fraction_node(node.left, values_by_id)
        right = _eval_fraction_node(node.right, values_by_id)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            assert right.denominator == 1
            return left ** int(right.numerator)
    raise ValueError(f"Cannot evaluate node as exact Fraction: {type(node).__name__}")


def _fraction_to_exact_decimal(frac: Fraction) -> Decimal | None:
    """Convert a Fraction to an exact Decimal if its denominator is of form 2^a * 5^b."""
    num = frac.numerator
    den = frac.denominator
    p2 = 0
    while den % 2 == 0:
        den //= 2
        p2 += 1
    p5 = 0
    while den % 5 == 0:
        den //= 5
        p5 += 1
    if den != 1:
        return None
    k = max(p2, p5)
    scaled = num * (2 ** (k - p2)) * (5 ** (k - p5))
    with localcontext() as ctx:
        ctx.prec = max(120, len(str(abs(scaled))) + k + 20)
        return Decimal(scaled).scaleb(-k)


def format_canonical_decimal(dec: Decimal) -> str:
    """Format an exact finite Decimal cleanly matching CODATA/NIST canonical style."""
    if dec == 0:
        return "0"
    with localcontext() as ctx:
        ctx.prec = max(100, len(dec.as_tuple().digits) + 10)
        norm = dec.normalize()
        sign = "-" if norm.is_signed() else ""
        abs_d = abs(norm)
        digits = "".join(str(d) for d in abs_d.as_tuple().digits)
        exp = abs_d.as_tuple().exponent
        assert isinstance(exp, int)

        # Keep clean integers or values in [0.1, 100000) in fixed-point form
        if exp >= 0 and abs_d < Decimal("1e12"):
            return f"{sign}{digits}{'0' * exp}"
        if Decimal("0.1") <= abs_d < Decimal("100000"):
            plain = format(abs_d, "f")
            if "." in plain:
                plain = plain.rstrip("0").rstrip(".")
            return f"{sign}{plain}"

        # Normalized scientific notation: d.dddde±k
        sci_exp = exp + len(digits) - 1
        if len(digits) == 1:
            mant = digits
        else:
            mant = f"{digits[0]}.{digits[1:]}"
        if sci_exp == 0:
            return f"{sign}{mant}"
        return f"{sign}{mant}e{sci_exp}"


def evaluate_formula_decimal(
    formula: str,
    values_by_id: dict[str, Decimal | str],
    *,
    prec: int = 80,
) -> Decimal:
    """Evaluate a CODATA formula string to arbitrary precision Decimal."""
    tree = _parse_ast(formula)
    math_consts = get_math_constants(prec=prec + 10)

    def _eval(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Constant):
            return Decimal(str(node.value))
        if isinstance(node, ast.Name):
            if node.id in math_consts:
                return math_consts[node.id]
            if node.id not in values_by_id:
                raise KeyError(f"Missing constant value for {node.id!r}")
            raw = values_by_id[node.id]
            return raw if isinstance(raw, Decimal) else Decimal(raw)
        if isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            return -operand if isinstance(node.op, ast.USub) else +operand
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Name)
            arg = _eval(node.args[0])
            if node.func.id == "sqrt":
                return arg.sqrt()
            if node.func.id == "ln":
                return arg.ln()
            if node.func.id == "abs":
                return abs(arg)
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
            if isinstance(node.op, ast.Pow):
                if right == right.to_integral_value():
                    return left ** int(right)
                return (left.ln() * right).exp()
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")

    with localcontext() as ctx:
        ctx.prec = prec
        result = _eval(tree.body)
        return +result


def truncate_to_sig_digits(dec: Decimal, sig_digits: int = 34) -> Decimal:
    """Truncate (ROUND_DOWN) a high-precision Decimal to sig_digits significant digits."""
    if dec == 0:
        return Decimal(0)
    with localcontext() as ctx:
        ctx.prec = max(100, len(dec.as_tuple().digits) + 10)
        tup = dec.as_tuple()
        assert isinstance(tup.exponent, int)
        sci_exp = tup.exponent + len(tup.digits) - 1
        quant_exp = sci_exp - sig_digits + 1
        ctx.rounding = ROUND_DOWN
        return dec.quantize(Decimal(1).scaleb(quant_exp))


def evaluate_exact_formula(
    formula: str,
    values_by_id: dict[str, str],
    *,
    sig_digits: int = 34,
    rational_fractions: dict[str, Fraction] | None = None,
    high_prec_decimals: dict[str, Decimal] | None = None,
) -> tuple[str, bool, Fraction | None, Decimal]:
    """Evaluate an exact (computed_exact) formula and return (canonical_str, is_truncated, frac_or_none, dec_80).

    For rational formulas whose reduced denominator has only factors of 2 and 5, returns
    the complete terminating decimal expansion with is_truncated=False.
    For repeating rationals or irrationals, truncates (ROUND_DOWN) to `sig_digits`
    significant digits (default 34, IEEE 754 decimal128) with is_truncated=True.
    """
    tree = _parse_ast(formula)
    rational_ids = set(rational_fractions.keys()) if rational_fractions is not None else None
    if _is_pure_rational_ast(tree.body, rational_ids=rational_ids):
        frac_inputs: dict[str, str | Fraction] = {k: v for k, v in values_by_id.items()}
        if rational_fractions is not None:
            frac_inputs.update(rational_fractions)
        frac = _eval_fraction_node(tree.body, frac_inputs)
        exact_dec = _fraction_to_exact_decimal(frac)
        if exact_dec is not None:
            return format_canonical_decimal(exact_dec), False, frac, exact_dec
        # Repeating rational: compute 80-digit Decimal directly from exact Fraction
        with localcontext() as ctx:
            ctx.prec = max(80, sig_digits + 40)
            high_prec = Decimal(frac.numerator) / Decimal(frac.denominator)
        truncated_dec = truncate_to_sig_digits(high_prec, sig_digits=sig_digits)
        return format_canonical_decimal(truncated_dec), True, frac, high_prec

    dec_inputs: dict[str, Decimal | str] = dict(values_by_id)
    if high_prec_decimals is not None:
        dec_inputs.update(high_prec_decimals)
    high_prec = evaluate_formula_decimal(formula, dec_inputs, prec=max(80, sig_digits + 40))
    truncated_dec = truncate_to_sig_digits(high_prec, sig_digits=sig_digits)
    return format_canonical_decimal(truncated_dec), True, None, high_prec


def evaluate_exact_dag(
    exact_formulas: dict[str, str],
    defining_values: dict[str, str],
    *,
    sig_digits: int = 34,
) -> dict[str, tuple[str, bool, Decimal]]:
    """Topologically evaluate all `computed_exact` formulas from `defining` constants.

    Propagates exact `Fraction` values across pure-rational formulas and 80-digit `Decimal`
    values across irrational formulas so intermediate 34-digit truncations never degrade
    downstream exact constants.

    Returns mapping ``const_id -> (canonical_str, is_truncated, high_prec_decimal)``.
    """
    topo_order: list[str] = []
    visited: set[str] = set()
    stack: set[str] = set()

    def _visit(cid: str) -> None:
        if cid in visited:
            return
        if cid in stack:
            raise ValueError(f"Cycle detected in computed_exact formulas at {cid!r}")
        stack.add(cid)
        formula = exact_formulas[cid]
        for dep in extract_dependencies(formula):
            if dep in exact_formulas:
                _visit(dep)
        stack.remove(cid)
        visited.add(cid)
        topo_order.append(cid)

    for cid in sorted(exact_formulas):
        _visit(cid)

    rational_fracs: dict[str, Fraction] = {k: Fraction(Decimal(v)) for k, v in defining_values.items()}
    high_prec_decs: dict[str, Decimal] = {k: Decimal(v) for k, v in defining_values.items()}
    str_vals: dict[str, str] = dict(defining_values)
    results: dict[str, tuple[str, bool, Decimal]] = {}

    for cid in topo_order:
        val_str, is_trunc, frac_val, dec_val = evaluate_exact_formula(
            exact_formulas[cid],
            str_vals,
            sig_digits=sig_digits,
            rational_fractions=rational_fracs,
            high_prec_decimals=high_prec_decs,
        )
        str_vals[cid] = val_str
        high_prec_decs[cid] = dec_val
        if frac_val is not None:
            rational_fracs[cid] = frac_val
        results[cid] = (val_str, is_trunc, dec_val)

    return results


def count_significant_digits(val_str: str) -> int:
    """Count significant decimal digits in a canonical numeric string (preserving trailing zeros)."""
    mant = val_str.strip().lower().split("e")[0].lstrip("+-")
    digits_only = mant.replace(".", "").lstrip("0")
    return len(digits_only) if digits_only else 1


def check_fits_float32(val_str: str, *, is_truncated: bool = False) -> bool:
    """Return True if IEEE 754 binary32 (float) holds `val_str` without overflow, underflow, or rounding loss."""
    if is_truncated:
        return False
    with localcontext() as ctx:
        ctx.prec = 100
        d = Decimal(val_str)
        if d == 0:
            return True
        try:
            f64 = float(d)
            f32 = struct.unpack(">f", struct.pack(">f", f64))[0]
        except OverflowError:
            return False
        if not math.isfinite(f32) or abs(f32) < _FLOAT32_MIN_NORMAL:
            return False
        f32_dec = Decimal.from_float(f32)
        if f32_dec == d:
            return True
        norm = d.normalize()
        exp = norm.as_tuple().exponent
        assert isinstance(exp, int)
        step = Decimal(1).scaleb(exp)
        if f32_dec.quantize(step) != d:
            return False
        try:
            f32_minus = struct.unpack(">f", struct.pack(">f", float(d - step)))[0]
            f32_plus = struct.unpack(">f", struct.pack(">f", float(d + step)))[0]
        except OverflowError:
            return False
        return f32_minus != f32 and f32_plus != f32


def check_fits_float64(val_str: str, *, is_truncated: bool = False) -> bool:
    """Return True if IEEE 754 binary64 (double) holds `val_str` without overflow, underflow, or rounding loss."""
    if is_truncated:
        return False
    with localcontext() as ctx:
        ctx.prec = 100
        d = Decimal(val_str)
        if d == 0:
            return True
        f64 = float(d)
        if not math.isfinite(f64) or abs(f64) < _FLOAT64_MIN_NORMAL:
            return False
        return Decimal(str(f64)) == d


def get_recommended_numeric_type(
    val_str: str, *, is_truncated: bool = False
) -> Literal["float32", "float64", "decimal"]:
    """Return the smallest standard numeric type capable of holding the value losslessly."""
    if check_fits_float32(val_str, is_truncated=is_truncated):
        return "float32"
    if check_fits_float64(val_str, is_truncated=is_truncated):
        return "float64"
    return "decimal"
