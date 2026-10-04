import json
from collections import namedtuple
from typing import Any, Union, get_args, get_origin

from lsprotocol import converters

from pygls.protocol.json_rpc import (
    JsonRPCNotification,
    JsonRPCProtocol,
    JsonRPCRequestMessage,
    JsonRPCResponseMessage,
)
from pygls.protocol.language_server import LanguageServerProtocol, lsp_method


def _dict_to_object(d: Any):
    """Create nested objects (namedtuple) from dict."""

    if d is None:
        return None

    if not isinstance(d, dict):
        return d

    type_name = d.pop("type_name", "Object")
    return json.loads(
        json.dumps(d),
        object_hook=lambda p: namedtuple(type_name, p.keys(), rename=True)(*p.values()),
    )


def _params_field_structure_hook(obj, cls):
    if "params" in obj:
        obj["params"] = _dict_to_object(obj["params"])

    return cls(**obj)


def _result_field_structure_hook(obj, cls):
    if "result" in obj:
        obj["result"] = _dict_to_object(obj["result"])

    return cls(**obj)


def _is_multi_member_union(typ: Any) -> bool:
    """Unions of several concrete members, the shapes cattrs leaves
    without a hook (e.g. lsprotocol's notebook selector unions, which
    break structuring a server's initialize result). Single-member
    unions like Optional keep their existing path."""
    return get_origin(typ) is Union and (
        sum(member is not type(None) for member in get_args(typ)) > 1
    )


def _union_structure_hook_factory(typ: Any, converter):
    """Structure a multi-member union by trying its members: exact
    primitives by type, attrs classes through the converter."""

    def _structure_union(object_: Any, _: Any):
        for member in get_args(typ):
            if member is None or member is type(None):
                if object_ is None:
                    return None
            elif member is str:
                if isinstance(object_, str):
                    return object_
            elif member is bool:
                if isinstance(object_, bool):
                    return object_
            elif member in (int, float):
                if isinstance(object_, (int, float)) and not isinstance(
                    object_, bool
                ):
                    return object_
            elif isinstance(member, type):
                try:
                    return converter.structure(object_, member)
                except Exception:
                    continue
        raise ValueError(f"cannot structure {object_!r} as {typ}")

    return _structure_union


def default_converter():
    """Default converter factory function."""

    converter = converters.get_converter()
    converter.register_structure_hook_factory(
        _is_multi_member_union, _union_structure_hook_factory
    )
    converter.register_structure_hook(
        JsonRPCRequestMessage, _params_field_structure_hook
    )

    converter.register_structure_hook(
        JsonRPCResponseMessage, _result_field_structure_hook
    )

    converter.register_structure_hook(JsonRPCNotification, _params_field_structure_hook)

    return converter


__all__ = (
    "JsonRPCProtocol",
    "LanguageServerProtocol",
    "JsonRPCRequestMessage",
    "JsonRPCResponseMessage",
    "JsonRPCNotification",
    "_dict_to_object",
    "_params_field_structure_hook",
    "_result_field_structure_hook",
    "default_converter",
    "lsp_method",
)
