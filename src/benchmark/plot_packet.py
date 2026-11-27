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


def combined_client_times(measurements, credential, source):
    """Add matching linkage means only for CREDENTIAL=1, then average builds."""
    selected = measurements.loc[measurements["CREDENTIAL"] == credential]
    build = selected.loc[selected["function"] == "build_packet"].copy()
    label = f"build_packet (CREDENTIAL={credential})"
    if credential != 1 or build.empty:
        return mean_times(build, "PATH_LENGTH", "CPU_time_ms", source, label)

    link = selected.loc[selected["function"] == "link_credential"].copy()
    if link.empty:
        print(
            f"Warning: {source}: no link_credential rows for CREDENTIAL=1; "
            "skipping the combined client curve.",
            file=sys.stderr,
        )
        return pd.Series(dtype=float)

    keys = [
        column for column in ("credential", "THRESHOLD", "PATH_LENGTH", "CREDENTIAL")
        if column in measurements.columns
    ]
    for frame in (build, link):
        for column in keys + ["CPU_time_ms"]:
            frame[column] = numeric_column(frame, column, source)
        if (frame["CPU_time_ms"] < 0).any():
            raise ValueError(f"{source}: negative client execution time for CREDENTIAL=1.")

    link_means = (
        link.groupby(keys, as_index=False, dropna=False)["CPU_time_ms"].mean()
        .rename(columns={"CPU_time_ms": "_link_time_ms"})
    )
    combined = build.merge(
        link_means, on=keys, how="left", sort=False, validate="many_to_one"
    )
    missing = combined["_link_time_ms"].isna()
    if missing.any():
        print(
            f"Warning: {source}: {int(missing.sum())} build_packet measurement(s) "
            "with CREDENTIAL=1 have no link_credential timing with matching "
            "parameters; omitting these incomplete totals.",
            file=sys.stderr,
        )
        combined = combined.loc[~missing].copy()
    if combined.empty:
        return pd.Series(dtype=float)

    combined["CPU_time_ms"] = combined["CPU_time_ms"] + combined["_link_time_ms"]
    return mean_times(
        combined, "PATH_LENGTH", "CPU_time_ms", source,
        "build_packet + link_credential (CREDENTIAL=1)",
    )


def panel_curves(sphinx, measurements, sphinx_column, function, sphinx_path, data_path):
    """Build curves in the reference legend order, with matching colors and markers."""
    baseline = mean_times(sphinx, "path_length", sphinx_column, sphinx_path, "Sphinx")
    curves = []
    for credential, label, marker, color in (
        (1, "DSphinx + Credentials", "o", "#DD8452"),
        (0, "DSphinx", "X", "#4C72B0"),
    ):
        if function == "build_packet":
            series = combined_client_times(measurements, credential, data_path)
        else:
            selected = measurements.loc[
                (measurements["function"] == function)
                & (measurements["CREDENTIAL"] == credential)
            ]
            series = mean_times(selected, "PATH_LENGTH", "CPU_time_ms", data_path, label)
        curves.append((label, series, marker, color))
    curves.append(("Sphinx", baseline, "s", "#55A868"))
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
            measurements["function"].isin(["build_packet", "link_credential", "process"])
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
        from matplotlib.ticker import MaxNLocator, StrMethodFormatter

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
                        marker=marker, color=color, linewidth=1.4,
                        markersize=3.5 if marker == "s" else 5,
                        linestyle="-", markeredgecolor="white", markeredgewidth=0.5,
                    )
                    path_lengths.update(series.index)
            ax.set_xlabel("Path length (number of hops)", fontsize=8)
            ax.set_ylabel("Computation time (ms)", fontsize=8)
            ax.tick_params(labelsize=8)
            # Reserve room above the data for the three-line legend.
            max_time = max(float(series.max()) for _, series, _, _ in curves if not series.empty)
            ax.set_ylim(0, max(1, 1.4 * max_time))
            ax.set_axisbelow(True)
            ax.grid(False, axis="both", which="both")
            ax.grid(True, axis="y", which="major", color="#EAEAEA", linewidth=0.6)
            ax.legend(
                title="Protocol", loc="upper left", fontsize=7,
                title_fontsize=7, framealpha=1,
            )
            if len(path_lengths) <= 15 and all(
                float(length).is_integer() for length in path_lengths
            ):
                ax.set_xticks(sorted(path_lengths))
            else:
                ax.xaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=1))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True, min_n_ticks=1))
            ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
            ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
            # Keep the first markers fully visible, as in the reference image.
            x_padding = 0.05 * max(1, max(path_lengths) - min_path_length)
            ax.set_xlim(left=min_path_length - x_padding)

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
