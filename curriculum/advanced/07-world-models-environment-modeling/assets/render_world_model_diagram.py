"""Validate and deterministically render the Course 07 diagram specification."""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "world-model-control-loop-spec.json"


def port_point(node: dict, port_name: str) -> tuple[float, float]:
    bounds = node["bounds"]
    port = node["ports"][port_name]
    offset = port["offset"]
    if port["side"] == "left":
        return bounds["x"], bounds["y"] + bounds["height"] * offset
    if port["side"] == "right":
        return bounds["x"] + bounds["width"], bounds["y"] + bounds["height"] * offset
    if port["side"] == "top":
        return bounds["x"] + bounds["width"] * offset, bounds["y"]
    if port["side"] == "bottom":
        return bounds["x"] + bounds["width"] * offset, bounds["y"] + bounds["height"]
    raise ValueError(f"unknown port side: {port['side']}")


def overlaps(a: dict, b: dict) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def validate(spec: dict) -> None:
    width = spec["canvas"]["width"]
    height = spec["canvas"]["height"]
    margin = spec["canvas"]["margin"]
    groups = {item["id"]: item for item in spec["groups"]}
    nodes = {item["id"]: item for item in spec["nodes"]}
    edges = {item["id"]: item for item in spec["edges"]}
    if len(groups) != len(spec["groups"]):
        raise ValueError("duplicate group ID")
    if len(nodes) != len(spec["nodes"]):
        raise ValueError("duplicate node ID")
    if len(edges) != len(spec["edges"]):
        raise ValueError("duplicate edge ID")

    for node in nodes.values():
        bounds = node["bounds"]
        if bounds["x"] < margin or bounds["y"] < 120:
            raise ValueError(f"node outside top/left margin: {node['id']}")
        if bounds["x"] + bounds["width"] > width - margin:
            raise ValueError(f"node outside right margin: {node['id']}")
        if bounds["y"] + bounds["height"] > height - margin:
            raise ValueError(f"node outside bottom margin: {node['id']}")
        group = groups[node["group"]]["bounds"]
        if not (
            group["x"] <= bounds["x"]
            and group["y"] <= bounds["y"]
            and group["x"] + group["width"] >= bounds["x"] + bounds["width"]
            and group["y"] + group["height"] >= bounds["y"] + bounds["height"]
        ):
            raise ValueError(f"group does not contain node: {node['id']}")

    values = list(nodes.values())
    for index, first in enumerate(values):
        for second in values[index + 1 :]:
            if overlaps(first["bounds"], second["bounds"]):
                raise ValueError(f"node overlap: {first['id']} and {second['id']}")

    for edge in edges.values():
        source = nodes[edge["from"]["node"]]
        target = nodes[edge["to"]["node"]]
        expected_start = port_point(source, edge["from"]["port"])
        expected_end = port_point(target, edge["to"]["port"])
        if tuple(edge["route"][0]) != expected_start:
            raise ValueError(f"edge start detached: {edge['id']}")
        if tuple(edge["route"][-1]) != expected_end:
            raise ValueError(f"edge end detached: {edge['id']}")
        for x, y in edge["route"]:
            if not (margin <= x <= width - margin and 120 <= y <= height - margin):
                raise ValueError(f"edge route outside canvas: {edge['id']}")


def text_lines(text: str, max_words: int = 3) -> list[str]:
    words = text.split()
    return [" ".join(words[i : i + max_words]) for i in range(0, len(words), max_words)]


def render(spec: dict) -> str:
    canvas = spec["canvas"]
    colors = spec["style"]["semantic_colors"]
    nodes = {item["id"]: item for item in spec["nodes"]}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas["width"]}" height="{canvas["height"]}" viewBox="0 0 {canvas["width"]} {canvas["height"]}" role="img" aria-labelledby="title description">',
        f'<title id="title">{html.escape(spec["title"])}</title>',
        f'<desc id="description">{html.escape(spec["output"]["alt_text"])}</desc>',
        "<defs>",
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#16324F" flood-opacity="0.10"/></filter>',
        '<marker id="arrow-primary" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2F6BFF"/></marker>',
        '<marker id="arrow-secondary" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#52606D"/></marker>',
        "</defs>",
        f'<rect width="100%" height="100%" fill="{canvas["background"]}"/>',
        f'<text x="60" y="66" font-family="{spec["style"]["font_family"]}" font-size="31" font-weight="700" fill="#16324F">{html.escape(spec["title"])}</text>',
        '<text x="60" y="105" font-family="Inter, Arial, sans-serif" font-size="20" fill="#52606D">Simulation supports a proposal. It never proves safety or grants execution authority.</text>',
    ]

    for group in spec["groups"]:
        b = group["bounds"]
        out.append(
            f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="18" fill="{group["fill"]}" stroke="{group["stroke"]}" stroke-width="2"/>'
        )
        out.append(
            f'<text x="{b["x"] + 24}" y="{b["y"] + 38}" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" fill="#16324F">{html.escape(group["label"])}</text>'
        )

    for edge in spec["edges"]:
        points = " ".join(f"{x},{y}" for x, y in edge["route"])
        primary = edge["kind"] == "primary"
        stroke = "#2F6BFF" if primary else "#52606D"
        marker = "arrow-primary" if primary else "arrow-secondary"
        dash = "" if primary else ' stroke-dasharray="8 7"'
        out.append(
            f'<polyline points="{points}" fill="none" stroke="{stroke}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" marker-end="url(#{marker})"{dash}/>'
        )
        if edge.get("label"):
            route = edge["route"]
            middle = route[len(route) // 2]
            label = html.escape(edge["label"])
            width = max(72, len(edge["label"]) * 9 + 20)
            out.append(
                f'<rect x="{middle[0] - width / 2}" y="{middle[1] - 29}" width="{width}" height="24" rx="7" fill="#F7F9FC" stroke="#D7DEE8"/>'
            )
            out.append(
                f'<text x="{middle[0]}" y="{middle[1] - 12}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="14" font-weight="600" fill="#52606D">{label}</text>'
            )

    for node in spec["nodes"]:
        b = node["bounds"]
        color = colors[node["type"]]
        out.append(
            f'<rect x="{b["x"]}" y="{b["y"]}" width="{b["width"]}" height="{b["height"]}" rx="14" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="2.5" filter="url(#shadow)"/>'
        )
        label_lines = text_lines(node["label"], 3)
        label_start = b["y"] + 37 - (len(label_lines) - 1) * 10
        for index, line in enumerate(label_lines):
            out.append(
                f'<text x="{b["x"] + b["width"] / 2}" y="{label_start + index * 22}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="17" font-weight="700" fill="#16324F">{html.escape(line)}</text>'
            )
        subtitle_lines = text_lines(node.get("subtitle", ""), 4)
        subtitle_start = b["y"] + b["height"] - 31 - (len(subtitle_lines) - 1) * 9
        for index, line in enumerate(subtitle_lines):
            out.append(
                f'<text x="{b["x"] + b["width"] / 2}" y="{subtitle_start + index * 18}" text-anchor="middle" font-family="Inter, Arial, sans-serif" font-size="13" fill="#52606D">{html.escape(line)}</text>'
            )

    out.extend(
        [
            '<rect x="60" y="955" width="1680" height="1" fill="#D7DEE8"/>',
            '<text x="60" y="982" font-family="Inter, Arial, sans-serif" font-size="14" fill="#52606D">Northstar credential-free teaching fixture · application-owned policy boundaries · zero production side effects</text>',
            "</svg>",
        ]
    )
    return "\n".join(out)


if __name__ == "__main__":
    spec = json.loads(SPEC_PATH.read_text())
    validate(spec)
    output = HERE / spec["output"]["svg"]
    output.write_text(render(spec))
    print(f"validated and rendered {output}")
