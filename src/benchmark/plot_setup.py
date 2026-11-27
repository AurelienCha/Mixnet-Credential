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


def mean_times(frame, names, x_column, time_column, scale, source):
    """Return sorted means in seconds for the specified function name(s)."""
    selected = frame.loc[frame["function"].isin(names), [x_column, time_column]].copy()
    if selected.empty:
        print(
            f"Warning: {source}: no rows for {' or '.join(names)}; skipping this curve.",
            file=sys.stderr,
        )
        return pd.Series(dtype=float)

    for column in (x_column, time_column):
        try:
            selected[column] = pd.to_numeric(selected[column], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{source}: nonnumeric value in {column!r} for {names}.") from exc
        if selected[column].isna().any() or not selected[column].map(math.isfinite).all():
            raise ValueError(f"{source}: missing or nonfinite value in {column!r} for {names}.")
    if (selected[time_column] < 0).any():
        raise ValueError(f"{source}: negative execution time for {names}.")

    selected[time_column] *= scale
    return selected.groupby(x_column, sort=True)[time_column].mean()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=Path, default=Path("benchmark/data/hthreshold.csv"), help="Threshold CSV path")
    parser.add_argument("--zk", type=Path, default=Path("benchmark/data/zk_cpu_times.csv"), help="ZK timing CSV path")
    parser.add_argument("-o", "--output", type=Path, default=Path("benchmark/results/setup.png"), help="Output image (e.g. .png, .pdf, .svg)")
    parser.add_argument("--show", action="store_true", help="Also display the plot in a window")
    args = parser.parse_args()

    try:
        threshold = read_timings(args.threshold, "THRESHOLD", "CPU_time_ms")
        zk = read_timings(args.zk, "t", "cpu_time_s")
        curves = [
            ("tau", mean_times(zk, ["tau"], "t", "cpu_time_s", 1.0, args.zk), "o", "#0072B2"),
            ("crs", mean_times(zk, ["crs"], "t", "cpu_time_s", 1.0, args.zk), "s", "#D55E00"),
            ("setup", mean_times(threshold, ["setup"], "THRESHOLD", "CPU_time_ms", 0.001, args.threshold), "^", "#009E73"),
        ]
        if all(series.empty for _, series, _, _ in curves):
            raise ValueError("No measurements found for any of the three requested functions.")

        import matplotlib
        if not args.show:
            matplotlib.use("Agg")  # Save files on machines without a graphical display.
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
        for label, series, marker, color in curves:
            if not series.empty:
                ax.plot(series.index, series.values, marker=marker, color=color, label=label, linewidth=1.8)
        ax.set_xlabel("Threshold (THRESHOLD / t)")
        ax.set_ylabel("Mean execution time (seconds)")
        ax.set_title("Execution time vs. threshold")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.25)
        ax.legend()
        # Show the measured thresholds exactly when the axis has room for them.
        thresholds = sorted({value for _, series, _, _ in curves for value in series.index})
        if len(thresholds) <= 15:
            ax.set_xticks(thresholds)

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
