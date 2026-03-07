import json
import re
from xml.etree.ElementTree import Element, SubElement, tostring

_INVALID_TAG_CHARS = re.compile(r'[^a-zA-Z0-9_\-\.]')


def _sanitize_tag(tag: str) -> str:
	"""Create an XML-safe tag name from an arbitrary key."""
	tag_str = str(tag)
	if not tag_str:
		return "item"
		
	safe = _INVALID_TAG_CHARS.sub("_", tag_str)
	if not safe:
		safe = "item"
	if safe[0].isdigit():
		safe = f"n_{safe}"
	return safe


def _append_value(parent: Element, key: str, value: object) -> None:
	"""Recursively append Python values into XML nodes."""
	tag = _sanitize_tag(key)

	if isinstance(value, dict):
		node = SubElement(parent, tag)
		for child_key, child_value in value.items():
			_append_value(node, str(child_key), child_value)
		return

	if isinstance(value, list):
		node = SubElement(parent, tag)
		for item in value:
			_append_value(node, "item", item)
		return

	node = SubElement(parent, tag)
	node.text = "" if value is None else str(value)


def json_to_xml_payload(payload: str, root_tag: str = "post_payload") -> str:
	"""
	Convert JSON string payload to XML string.

	The payload is expected to contain both `config` and `data` sections.
	This function is the entry point for downstream XML/post generation.
	"""
	parsed = json.loads(payload)

	root = Element(_sanitize_tag(root_tag))
	if isinstance(parsed, dict):
		for key, value in parsed.items():
			_append_value(root, key, value)
	elif isinstance(parsed, list):
		for item in parsed:
			_append_value(root, "item", item)
	else:
		_append_value(root, "value", parsed)

	return tostring(root, encoding="unicode")


if __name__ == "__main__":
	sample = {
		"config": {
			"success": True,
			"source": "database",
		},
		"data": [
			{"id": 1, "name": "Item A"},
			{"id": 2, "name": "Item B"},
		],
	}
	print(json_to_xml_payload(json.dumps(sample)))
