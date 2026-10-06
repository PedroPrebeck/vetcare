"""Datas operacionais da clínica em America/Sao_Paulo, independentes do host."""

from datetime import datetime
from zoneinfo import ZoneInfo


def today():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()
