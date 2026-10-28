"""Enums compartilhados pelos contratos do domínio."""

from enum import StrEnum


class EvidenceKind(StrEnum):
    OBSERVED = "observed"
    ESTIMATED = "estimated"
    HYPOTHETICAL = "hypothetical"
    UNAVAILABLE = "unavailable"


class InstitutionType(StrEnum):
    SCHOOL = "school"
    HEALTH_UNIT = "health_unit"
    OTHER_PUBLIC = "other_public"


class ConnectivityStatus(StrEnum):
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    UNCONNECTED = "unconnected"


class Decision(StrEnum):
    INVEST = "INVESTIR"
    PILOT = "PILOTAR"
    WAIT = "AGUARDAR"
    HUMAN_REVIEW = "REVISAO_HUMANA"
