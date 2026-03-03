"""Generate a visual graph of a pipeline as PNG."""

from __future__ import annotations

import os
import platform
import subprocess

import graphviz

from pilot.config import load_config


def build_graph(config_path: str, output: str | None = None) -> str:
    """Build a PNG graph from a pipeline config. Returns output file path."""
    config = load_config(config_path)

    dot = graphviz.Digraph(
        name="pipeline",
        format="png",
        graph_attr={
            "rankdir": "LR",
            "fontname": "Helvetica",
            "bgcolor": "white",
            "pad": "0.5",
            "dpi": "150",
        },
        node_attr={
            "shape": "box",
            "style": "rounded,filled",
            "fontname": "Helvetica",
            "fontsize": "11",
        },
        edge_attr={
            "fontname": "Helvetica",
            "fontsize": "9",
        },
    )

    # Start marker
    dot.node("__start__", "", shape="point", width="0.2")
    dot.edge("__start__", config.start_stage)

    # Exit node
    dot.node("__exit__", "EXIT", shape="doubleoctagon",
             fillcolor="#ffcccc", style="filled", fontsize="10")

    # Stage nodes
    for name, stage in config.stages.items():
        runner = stage.runner
        runner_info = (f"{runner.executor}/{runner.model}"
                       if runner.model else runner.executor)

        parts = [name, runner_info]
        if stage.fallback_runner:
            fb = stage.fallback_runner
            fb_info = (f"{fb.executor}/{fb.model}"
                       if fb.model else fb.executor)
            parts.append(f"fb: {fb_info}")

        label = "\n".join(parts)

        attrs: dict[str, str] = {}
        if stage.prompt:
            attrs["fillcolor"] = "#ddeeff"   # AI stages — blue
        else:
            attrs["fillcolor"] = "#ddffdd"   # shell stages — green
        if name == config.start_stage:
            attrs["penwidth"] = "2"

        dot.node(name, label, **attrs)

    # Signal edges
    for name, stage in config.stages.items():
        for signal, trans in stage.on_signal.items():
            target = trans.to or "__exit__"

            edge_attrs: dict[str, str] = {}
            if signal == "default":
                edge_attrs["style"] = "dashed"
                edge_attrs["color"] = "#999999"
                edge_attrs["fontcolor"] = "#999999"
            elif target == "__exit__":
                edge_attrs["color"] = "#cc0000"
                edge_attrs["fontcolor"] = "#cc0000"

            dot.edge(name, target, label=signal, **edge_attrs)

    # Output path — default to pipeline basename
    if output is None:
        output = os.path.splitext(os.path.basename(config_path))[0]

    path = dot.render(output, cleanup=True)
    return path


def open_file(path: str) -> None:
    """Open a file with the system viewer (no-op in Docker)."""
    if os.environ.get("PILOT_DOCKER"):
        return
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["open", path])
        elif system == "Linux":
            subprocess.Popen(["xdg-open", path])
    except FileNotFoundError:
        pass
