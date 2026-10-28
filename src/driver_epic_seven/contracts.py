"""Transport-independent requests and execution outcomes for the local core."""
from copy import deepcopy
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, Any
from uuid import uuid4


class Status(StrEnum):
    INVALID = 'invalid_request'
    BLOCKED = 'precondition_blocked'
    OBSERVED = 'observed'
    PREPARED = 'prepared'
    RESERVED = 'reserved'
    ATTEMPTED = 'dispatch_attempted'
    ACCEPTED = 'dispatch_accepted'
    EFFECT = 'effect_verified'
    RESULT = 'result_verified'
    RETURNED = 'return_verified'
    COMPLETED = 'completed'
    DEFEAT = 'defeat'
    CANCELLED = 'cancelled'
    UNCERTAIN = 'uncertain'


@dataclass(frozen=True)
class Identity:
    objective_id: str = field(default_factory=lambda: str(uuid4()))
    plan_id: str = field(default_factory=lambda: str(uuid4()))
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    attempt_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if any(not isinstance(v, str) or not v.strip() for v in vars(self).values()):
            raise ValueError('Identidades de execução devem ser strings não vazias.')

    def as_dict(self):
        return dict(vars(self))


@dataclass(frozen=True)
class Request:
    operation: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    identity: Identity = field(default_factory=Identity)

    def __post_init__(self):
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError('Operação ausente do pedido.')
        if not isinstance(self.parameters, Mapping) or not isinstance(self.identity, Identity):
            raise ValueError('Parâmetros ou identidade do pedido inválidos.')
        object.__setattr__(self, 'parameters', MappingProxyType(deepcopy(dict(self.parameters))))


@dataclass(frozen=True)
class Outcome:
    identity: Identity
    status: Status
    proof: Mapping[str, Any] = field(default_factory=dict)
    error: str | None = None

    def as_dict(self):
        return {'identity': self.identity.as_dict(), 'status': self.status.value,
                'proof': deepcopy(dict(self.proof)), 'error': self.error}


class ApplicationError(ValueError):
    def __init__(self, message, status=Status.INVALID, identity=None):
        super().__init__(message)
        self.status, self.identity = status, identity
