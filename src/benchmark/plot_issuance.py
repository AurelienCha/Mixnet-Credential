import argparse
import math
from pathlib import Path
import sys

import pandas as pd


def read_timings(path, x_column, time_column):
    """Read and normalize one CSV, preserving case-sensitive column names."""
    frame = pd.read_csv(path, skipinitialspace=True, encoding="utf-8-sig")
    frame.columns = frame.columns.str.strip()
    required = {"function", x_column, time_column}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(sorted(missing))}")
    frame["function"] = frame["function"].astype("string").str.strip()
    return frame


def numeric_column(frame, column, source):
    """Return a numeric column, rejecting missing, infinite, or invalid values."""
    try:
        values = pd.to_numeric(frame[column], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{source}: nonnumeric value in {column!r}.") from exc
    if values.isna().any() or not values.map(math.isfinite).all():
        raise ValueError(f"{source}: missing or nonfinite value in {column!r}.")
    return values


def mean_times(frame, names, x_column, time_column, scale, source):
    """Return sorted means in milliseconds for the specified function name(s)."""
    selected = frame.loc[frame["function"].isin(names), [x_column, time_column]].copy()
    if selected.empty:
        print(
            f"Warning: {source}: no rows for {' or '.join(names)}; skipping this curve.",
            file=sys.stderr,
        )
        return pd.Series(dtype=float)

    for column in (x_column, time_column):
        selected[column] = numeric_column(selected, column, source)
    if (selected[time_column] < 0).any():
        raise ValueError(f"{source}: negative execution time for {names}.")

    selected[time_column] *= scale
    return selected.groupby(x_column, sort=True)[time_column].mean()


def batched_mean_times(frame, names, thresholds, source):
    """Assign consecutive ZK batches to sorted thresholds, ignoring t entirely.

    Aliases in names identify the same operation. Filtering preserves their
    original row order even when different operations are interleaved in the CSV.
    Every selected row is used exactly once. Missing operations retain the usual
    warning/skip behavior; a present operation needs at least one row per threshold.
    """
    selected = frame.loc[frame["function"].isin(names)].copy()
    if not len(thresholds):
        raise ValueError("No THRESHOLD values found in the threshold CSV.")
    thresholds = sorted(thresholds)
    row_count = len(selected)
    threshold_count = len(thresholds)
    if 0 < row_count < threshold_count:
        raise ValueError(
            f"{source}: {' or '.join(names)} has {row_count} measurements for "
            f"{threshold_count} thresholds; at least one measurement per threshold "
            "is required."
        )

    batch_size, extra_rows = divmod(row_count, threshold_count)
    # For example: 8 rows and 3 thresholds produce consecutive batches of 3, 3, 2.
    selected["THRESHOLD"] = [
        threshold
        for index, threshold in enumerate(thresholds)
        for _ in range(batch_size + (index < extra_rows))
    ]
    # ZK measurements are recorded in seconds; display them in milliseconds.
    return mean_times(selected, names, "THRESHOLD", "cpu_time_s", 1000.0, source)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=Path, default=Path("benchmark/data/threshold.csv"), help="Threshold CSV path")
    parser.add_argument("--zk", type=Path, default=Path("benchmark/data/zk_cpu_times.csv"), help="ZK timing CSV path")
    parser.add_argument("-o", "--output", type=Path, default=Path("benchmark/results/credential_issuance.png"),  help="Output image (e.g. .png, .pdf, .svg)")
    parser.add_argument("--show", action="store_true", help="Also display the plot in a window")
    args = parser.parse_args()

    try:
        threshold = read_timings(args.threshold, "THRESHOLD", "CPU_time_ms")
        zk = read_timings(args.zk, "t", "cpu_time_s")
        # Use thresholds from the whole CSV, including other functions' rows.
        thresholds = sorted(numeric_column(threshold, "THRESHOLD", args.threshold).unique())
        if not thresholds:
            raise ValueError(f"{args.threshold}: no THRESHOLD values found.")
        curves = [
            (
                "Verify proof",
                batched_mean_times(zk, ["verify", "verify_proof"], thresholds, args.zk),
                "v", "#CC79A7",  # Magenta downward triangles.
            ),
            (
                "Generate proof",
                batched_mean_times(zk, ["proof", "proof_generation"], thresholds, args.zk),
                "*", "#B59B00",  # Gold stars.
            ),
            (
                "DSphinx protocol",
                mean_times(
                    threshold, ["get_credential", "get_credentials"],
                    "THRESHOLD", "CPU_time_ms", 1.0, args.threshold,
                ),
                "h", "#595959",  # Dark gray hexagons.
            ),
        ]
        if all(series.empty for _, series, _, _ in curves):
            raise ValueError("No measurements found for any of the three requested functions.")

        import matplotlib
        if not args.show:
            matplotlib.use("Agg")  # Save files on machines without a graphical display.
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator, StrMethodFormatter

        fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
        for label, series, marker, color in curves:
            if not series.empty:
                ax.plot(
                    series.index, series.values, marker=marker, color=color,
                    label=label, linewidth=1.8, linestyle="-",
                    markersize=8 if marker == "*" else 6,
                    markeredgecolor="white", markeredgewidth=0.8,
                )
        ax.set_xlabel(r"Reconstruction threshold $t$")
        ax.set_ylabel("Computation time (ms)")
        ax.set_ylim(0, max(1, ax.get_ylim()[1]))
        ax.set_axisbelow(True)
        ax.grid(False, axis="both", which="both")
        ax.grid(True, axis="y", which="major", color="#EAEAEA", linewidth=0.8)
        ax.legend(loc="best", framealpha=1)
        # Show the measured thresholds exactly when the axis has room for them.
        if len(thresholds) <= 15 and all(float(value).is_integer() for value in thresholds):
            ax.set_xticks(thresholds)
        else:
            ax.xaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=1))
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6, integer=True, min_n_ticks=1))
        ax.xaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

        args.output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.output, dpi=300)
        print(f"Saved {args.output.resolve()}")
        if args.show:
            plt.show()
        plt.close(fig)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
