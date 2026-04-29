from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from app.models import Device, Service, User, user_devices, user_services


def compile_segment_query(filters: dict[str, Any]) -> Select:
    """
    Компилирует filters (JSON дерево) в SQLAlchemy Select(User).
    Возвращает готовый select(User), который можно дальше .limit()/.offset() и т.д.

    Важно:
    - для device/service нужны JOIN-ы через M2M таблицы
    - при JOIN-ах используем DISTINCT, чтобы не получать дублей User из-за связей M2M
    """
    stmt = select(User)

    expr, join_plan, needs_distinct = _compile_node(filters)

    # применяем join-ы (если нужны)
    for target, onclause in join_plan:
        stmt = stmt.join(target, onclause)

    stmt = stmt.where(expr)

    if needs_distinct:
        stmt = stmt.distinct(User.id)

    return stmt


def _compile_node(node: dict[str, Any]) -> tuple[ColumnElement[bool], list[tuple[Any, Any]], bool]:
    """
    Возвращает:
    - bool expression (WHERE)
    - join_plan: список (target, onclause) для stmt.join(...)
    - needs_distinct: True если были join-ы по M2M
    """
    # group node: {"op":"AND|OR","rules":[...]}
    if "op" in node and "rules" in node and "field" not in node:
        op = node["op"]
        rules = node["rules"]

        compiled = [_compile_node(r) for r in rules]
        exprs = [c[0] for c in compiled]

        join_plan: list[tuple[Any, Any]] = []
        needs_distinct = False
        for _, joins, nd in compiled:
            join_plan.extend(joins)
            needs_distinct = needs_distinct or nd

        if op == "AND":
            return and_(*exprs), join_plan, needs_distinct
        if op == "OR":
            return or_(*exprs), join_plan, needs_distinct

        raise ValueError(f"Unknown group op: {op}")

    # rule node: {"field":"...", "op":"...", "value": ...}
    field = node["field"]
    op = node["op"]
    value = node["value"]

    if field == "city":
        if op == "EQ":
            return (User.city == value), [], False
        if op == "IN":
            return User.city.in_(value), [], False

    if field == "age":
        if op == "EQ":
            return (User.age == int(value)), [], False
        if op == "BETWEEN":
            a, b = value
            return User.age.between(int(a), int(b)), [], False

    if field == "has_children":
        if op == "EQ":
            return (User.has_children == bool(value)), [], False

    if field == "device":
        if op == "ANY":
            # join users -> user_devices -> devices
            joins = [
                (user_devices, user_devices.c.user_id == User.id),
                (Device, Device.id == user_devices.c.device_id),
            ]
            expr = Device.code.in_(value)
            return expr, joins, True

    if field == "service":
        if op == "ANY":
            joins = [
                (user_services, user_services.c.user_id == User.id),
                (Service, Service.id == user_services.c.service_id),
            ]
            expr = Service.code.in_(value)
            return expr, joins, True

    raise ValueError(f"Unsupported rule: field={field} op={op}")
