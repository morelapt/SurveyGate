from typing import Any

ALLOWED_FIELDS = {"city", "age", "has_children", "device", "service"}
ALLOWED_GROUP_OPS = {"AND", "OR"}

ALLOWED_RULE_OPS_BY_FIELD = {
    "city": {"EQ", "IN"},
    "age": {"EQ", "BETWEEN"},
    "has_children": {"EQ"},
    "device": {"ANY"},
    "service": {"ANY"},
}


def validate_segment_tree(node: Any) -> None:
    """
    Валидирует структуру фильтра сегмента.
    Бросает ValueError с понятным текстом, если что-то не так.
    """
    if not isinstance(node, dict):
        raise ValueError("Segment must be an object")

    # group node: {"op": "AND|OR", "rules":[...]}
    if "op" in node and "rules" in node and "field" not in node:
        op = node["op"]
        rules = node["rules"]

        if op not in ALLOWED_GROUP_OPS:
            raise ValueError(f"Invalid group op: {op}")

        if not isinstance(rules, list) or len(rules) == 0:
            raise ValueError("rules must be a non-empty array")

        for child in rules:
            validate_segment_tree(child)

        return

    # rule node: {"field": "...", "op": "...", "value": ...}
    field = node.get("field")
    op = node.get("op")
    value = node.get("value")

    if field not in ALLOWED_FIELDS:
        raise ValueError(f"Invalid field: {field}")

    allowed_ops = ALLOWED_RULE_OPS_BY_FIELD[field]
    if op not in allowed_ops:
        raise ValueError(f"Invalid op {op} for field {field}")

    # минимальные проверки value по типам
    if field == "age" and op == "BETWEEN":
        if not (isinstance(value, list) and len(value) == 2 and all(isinstance(x, int) for x in value)):
            raise ValueError("age BETWEEN value must be [int, int]")

    if op in {"IN", "ANY"}:
        if not (isinstance(value, list) and len(value) > 0):
            raise ValueError(f"{field} {op} value must be non-empty list")

    if field == "has_children" and op == "EQ":
        if not isinstance(value, bool):
            raise ValueError("has_children EQ value must be boolean")
