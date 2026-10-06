"""Validação de entradas: tipos, limites, datas e conversão monetária exata."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re
from clock import today


class ValidationError(ValueError):
    pass


def text(data, key, label, minimum=0, maximum=4000):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ValidationError(f"{label}: informe um texto.")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise ValidationError(f"{label}: use entre {minimum} e {maximum} caracteres.")
    return value


def integer(data, key, label, low=1, high=2_147_483_647):
    value = data.get(key)
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value or "0")):
        raise ValidationError(f"{label}: informe um número inteiro.")
    value = int(value or 0)
    if not low <= value <= high:
        raise ValidationError(f"{label}: valor fora do intervalo permitido.")
    return value


def choice(data, key, allowed, label):
    value = data.get(key)
    if value not in allowed:
        raise ValidationError(f"{label}: opção inválida.")
    return value


def weight(data):
    value = data.get("weight_kg")
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        raise ValidationError("Peso: informe um número válido.")
    if not number.is_finite() or not Decimal("0") < number <= Decimal("1000"):
        raise ValidationError("Peso: informe um valor maior que zero e até 1.000 kg.")
    return float(number)


def money(data, key="amount", allow_zero=False):
    try:
        number = Decimal(str(data.get(key, "")).replace(",", "."))
        if not number.is_finite() or number != number.quantize(Decimal("0.01")):
            raise InvalidOperation
        if number < (
            Decimal("0") if allow_zero else Decimal("0.01")
        ) or number > Decimal("1000000"):
            raise InvalidOperation
        return int(number * 100)
    except (InvalidOperation, ValueError):
        raise ValidationError(
            "Valor: informe até duas casas decimais, sem separador de milhar."
        )


def day(value, label="Data", future=True):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError(f"{label}: data inválida.")
    if not future and result > today():
        raise ValidationError(f"{label}: não pode ser futura.")
    return value


def moment(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.strftime("%Y-%m-%dT%H:%M") != value:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError("Horário: informe data e hora válidas.")
    return value
