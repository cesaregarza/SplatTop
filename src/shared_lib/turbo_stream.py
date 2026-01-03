"""Decoder for React Router's turbo-stream format.

Turbo-stream is a compact serialization format where:
- Data is stored as a JSON array
- Objects with underscore-prefixed keys (e.g., "_5") are references
- The key index points to the actual key name in the array
- The value is either a literal or an index to resolve
- Special values: -5 = null, -7 = undefined (omitted)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

# Special sentinel values in turbo-stream format
_NULL_SENTINEL = -5
_UNDEFINED_SENTINEL = -7


class TurboStreamDecoder:
    """Decodes turbo-stream format into plain Python objects."""

    def __init__(self, data: List[Any]) -> None:
        self._data = data
        self._cache: Dict[int, Any] = {}

    def _resolve(self, index: int) -> Any:
        """Resolve a value at the given index, with caching."""
        if index in self._cache:
            return self._cache[index]

        if index < 0 or index >= len(self._data):
            return None

        value = self._data[index]
        resolved = self._decode_value(value)
        self._cache[index] = resolved
        return resolved

    def _decode_value(self, value: Any, resolve_index: bool = False) -> Any:
        """Decode a single value, resolving references as needed.

        Args:
            value: The value to decode.
            resolve_index: If True and value is a non-negative int, treat as index.
        """
        if isinstance(value, dict):
            return self._decode_object(value)
        elif isinstance(value, list):
            return self._decode_array(value)
        elif resolve_index and isinstance(value, int) and value >= 0:
            # Array elements are indices to resolve
            return self._resolve(value)
        else:
            # Primitive value (string, number, bool, null)
            return value

    def _decode_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Decode an object, resolving underscore-prefixed reference keys."""
        result: Dict[str, Any] = {}

        for key, val in obj.items():
            if key.startswith("_"):
                # Reference key - resolve the actual key name
                try:
                    key_index = int(key[1:])
                    actual_key = self._data[key_index]
                    if not isinstance(actual_key, str):
                        # Key should be a string
                        continue
                except (ValueError, IndexError):
                    continue

                # Resolve the value
                if isinstance(val, int):
                    if val == _NULL_SENTINEL:
                        result[actual_key] = None
                    elif val == _UNDEFINED_SENTINEL:
                        # Undefined - skip this key entirely
                        continue
                    elif val >= 0:
                        # Positive index - resolve reference
                        result[actual_key] = self._resolve(val)
                    else:
                        # Other negative values - treat as literal
                        result[actual_key] = val
                else:
                    # Non-integer value - decode directly
                    result[actual_key] = self._decode_value(val)
            else:
                # Regular key - decode value directly
                result[key] = self._decode_value(val)

        return result

    def _decode_array(self, arr: List[Any]) -> List[Any]:
        """Decode an array, resolving each element as an index reference."""
        return [self._decode_value(item, resolve_index=True) for item in arr]

    def decode(self) -> Dict[str, Any]:
        """Decode the turbo-stream data into a plain object.

        Returns the decoded data organized by route keys.
        """
        if not self._data:
            return {}

        # The first element defines the root structure
        root_ref = self._data[0]
        if not isinstance(root_ref, dict):
            return {}

        return self._decode_object(root_ref)

    def get_route_data(self, route_key: str) -> Optional[Dict[str, Any]]:
        """Extract data for a specific route key.

        Args:
            route_key: The route identifier, e.g.,
                "features/tournament-bracket/routes/to.$id.matches.$mid"

        Returns:
            The decoded data for that route, or None if not found.
        """
        decoded = self.decode()

        # Look for the route key in the decoded structure
        if route_key in decoded:
            route_data = decoded[route_key]
            if isinstance(route_data, dict):
                return route_data

        return None


def decode_turbo_stream(data: Union[str, bytes, List[Any]]) -> Dict[str, Any]:
    """Convenience function to decode turbo-stream data.

    Args:
        data: Either raw JSON string/bytes or already-parsed list.

    Returns:
        Decoded data as a plain dictionary.
    """
    import orjson

    if isinstance(data, (str, bytes)):
        parsed = orjson.loads(data)
    else:
        parsed = data

    if not isinstance(parsed, list):
        raise ValueError("Turbo-stream data must be a JSON array")

    decoder = TurboStreamDecoder(parsed)
    return decoder.decode()


def extract_route_data(
    data: Union[str, bytes, List[Any]],
    route_key: str,
) -> Optional[Dict[str, Any]]:
    """Extract data for a specific route from turbo-stream format.

    Args:
        data: Raw turbo-stream data (JSON string/bytes or parsed list).
        route_key: The route identifier to extract.

    Returns:
        The decoded data for that route, or None if not found.
    """
    import orjson

    if isinstance(data, (str, bytes)):
        parsed = orjson.loads(data)
    else:
        parsed = data

    if not isinstance(parsed, list):
        raise ValueError("Turbo-stream data must be a JSON array")

    decoder = TurboStreamDecoder(parsed)
    return decoder.get_route_data(route_key)
