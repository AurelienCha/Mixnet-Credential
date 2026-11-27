#!/usr/bin/env python3
"""Compare packet construction and processing in two separate column-sized figures.

Both input files store times in MILLISECONDS; no unit conversion is applied.
Repeated measurements are averaged separately for each path length and curve.
The case-sensitive CREDENTIAL column selects 0/1, not the credential column.

Client: original Sphinx package_time and build_packet with CREDENTIAL=1 and 0.
Mixnode: original Sphinx process_time and process with CREDENTIAL=1 and 0.
Only path lengths >= 3 are included, and both x-axes start at 3.

Install:
    python -m pip install pandas matplotlib

Run from the project directory (uses benchmark/data and benchmark/results):
    python plot_path_length_comparison.py

Or supply paths explicitly:
    python plot_path_length_comparison.py --path-length pathLength.csv \\
        --sphinx original_sphinx_time.csv --output packet_time.pdf

The output filename is a base name. For example, --output packet_time.pdf
saves packet_time_client.pdf and packet_time_mixnode.pdf. The default outputs
are benchmark/results/packet_time_client.png and packet_time_mixnode.png.
"""

import argparse
import math
from pathlib import Path
import sys

import pandas as pd


def read_csv(path, required_columns):
    """Ignore blank lines and surrounding whitespace, retaining column case."""
    frame = pd.read_csv(path, skipinitialspace=True, encoding="utf-8-sig")
    frame.columns = frame.columns.str.strip()
    missing = set(required_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
    if not frame.columns.is_unique:
        raise ValueError(f"{path}: duplicate column names after trimming spaces.")
    if "function" in frame.columns:
        frame["function"] = frame["function"].astype("string").str.strip()
    return frame


def numeric_column(frame, column, source):
    """Require finite numeric values, without silently dropping measurements."""
    try:
        values = pd.to_numeric(frame[column], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{source}: nonnumeric value in {column!r}.") from exc
    if values.isna().any() or not values.map(math.isfinite).all():
        raise ValueError(f"{source}: missing or nonfinite value in {column!r}.")
    return values


def mean_times(frame, path_column, time_column, source, label):
    """Return means in milliseconds, sorted by numeric path length."""
    if frame.empty:
        print(f"Warning: {source}: no rows for {label}; skipping curve.", file=sys.stderr)
        return pd.Series(dtype=float)
    selected = frame[[path_column, time_column]].copy()
    for column in (path_column, time_column):
        selected[column] = numeric_column(selected, column, source)
    if (selected[time_column] < 0).any():
        raise ValueError(f"{source}: negative execution time for {label}.")
    return selected.groupby(path_column, sort=True)[time_column].mean()


def panel_curves(sphinx, measurements, sphinx_column, function, sphinx_path, data_path):
    """Build one baseline curve and the two requested credential curves."""
    label = f"Original Sphinx ({sphinx_column})"
    baseline = mean_times(sphinx, "path_length", sphinx_column, sphinx_path, label)
    curves = [(label, baseline, "o", "#0072B2")]
    for credential, marker, color in ((1, "s", "#D55E00"), (0, "^", "#009E73")):
        selected = measurements.loc[
            (measurements["function"] == function)
            & (measurements["CREDENTIAL"] == credential)
        ]
        label = f"{function} (CREDENTIAL={credential})"
        series = mean_times(selected, "PATH_LENGTH", "CPU_time_ms", data_path, label)
        curves.append((label, series, marker, color))
    return curves


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--path-length", type=Path, default=Path("benchmark/data/pathLength.csv"),
        help="CSV containing PATH_LENGTH, CREDENTIAL, function, and CPU_time_ms",
    )
    parser.add_argument(
        "--sphinx", type=Path, default=Path("benchmark/data/original_sphinx_time.csv"),
        help="Original Sphinx CSV (package_time and process_time in milliseconds)",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        default=Path("benchmark/results/packet_time.png"),
        help="Output base filename; adds _client and _mixnode before the extension",
    )
    parser.add_argument("--show", action="store_true", help="Also display both figures")
    args = parser.parse_args()

    try:
        measurements = read_csv(
            args.path_length, ["function", "PATH_LENGTH", "CREDENTIAL", "CPU_time_ms"]
        )
        sphinx = read_csv(args.sphinx, ["path_length", "package_time", "process_time"])
        measurements = measurements.loc[
            measurements["function"].isin(["build_packet", "process"])
        ].copy()
        measurements["CREDENTIAL"] = numeric_column(
            measurements, "CREDENTIAL", args.path_length
        )
        # Exclude shorter routes before aggregation and axis scaling.
        min_path_length = 3
        measurements["PATH_LENGTH"] = numeric_column(
            measurements, "PATH_LENGTH", args.path_length
        )
        sphinx["path_length"] = numeric_column(sphinx, "path_length", args.sphinx)
        measurements = measurements.loc[measurements["PATH_LENGTH"] >= min_path_length]
        sphinx = sphinx.loc[sphinx["path_length"] >= min_path_length]

        panels = [
            ("Client computation", "package_time", "build_packet", "client"),
            ("Packet processing", "process_time", "process", "mixnode"),
        ]
        prepared_panels = []
        for title, sphinx_column, function, output_suffix in panels:
            curves = panel_curves(
                sphinx, measurements, sphinx_column, function,
                args.sphinx, args.path_length,
            )
            if all(series.empty for _, series, _, _ in curves):
                raise ValueError(
                    f"No measurements with path length >= {min_path_length} "
                    f"available for {title}."
                )
            output = args.output.with_name(
                f"{args.output.stem}_{output_suffix}{args.output.suffix or '.png'}"
            )
            prepared_panels.append((title, curves, output))

        import matplotlib
        if not args.show:
            matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator

        args.output.parent.mkdir(parents=True, exist_ok=True)
        figures = []
        for title, curves, output in prepared_panels:
            # Dimensions and text sizes suit a single column in a two-column paper.
            fig, ax = plt.subplots(figsize=(3.35, 2.6), layout="constrained")
            figures.append(fig)
            path_lengths = {min_path_length}
            for label, series, marker, color in curves:
                if not series.empty:
                    ax.plot(
                        series.index, series.values, label=label,
                        marker=marker, color=color, linewidth=1.4, markersize=3.5,
                    )
                    path_lengths.update(series.index)
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("Path length", fontsize=8)
            ax.set_ylabel("Mean execution time (ms)", fontsize=8)
            ax.tick_params(labelsize=8)
            # Reserve room above the data for the three-line legend.
            max_time = max(float(series.max()) for _, series, _, _ in curves if not series.empty)
            ax.set_ylim(0, 1.4 * max_time if max_time > 0 else 1)
            ax.grid(True, alpha=0.25)
            ax.legend(loc="upper left", fontsize=7, framealpha=1)
            if len(path_lengths) <= 15:
                ax.set_xticks(sorted(path_lengths))
            else:
                ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_xlim(left=min_path_length)

            fig.savefig(output, dpi=300)
            print(f"Saved {output.resolve()}")
        if args.show:
            plt.show()
        for fig in figures:
            plt.close(fig)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
