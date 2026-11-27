import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Save figures without requiring a graphical desktop.
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd
from scipy.stats import linregress


PARAMETERS = {
    "NBR_AUTHORITIES": "# Authorities",
    # "NBR_MIXNODES": "# Mixnodes",
    "PATH_LENGTH": "Path length",
    "THRESHOLD": "Threshold",
    # "NBR_CLIENT": "# Clients",
    # "CREDENTIAL": "Credential",
}
TARGET = "CPU_time_ms"
MIN_LEVELS = 3


def fit_scaling(group, parameter):
    """Return slope, log-space R-squared, and data-quality counts."""
    pairs = group[[parameter, TARGET]].apply(pd.to_numeric, errors="coerce")
    pairs = pairs.replace([np.inf, -np.inf], np.nan).dropna()
    pairs = pairs[(pairs[parameter] > 0) & (pairs[TARGET] > 0)]
    n = len(pairs)
    levels = pairs[parameter].nunique()
    result = {
        "exponent": np.nan, "r_squared_log": np.nan,
        "n_used": n, "n_excluded": len(group) - n, "n_levels": levels,
        "status": "insufficient_positive_levels",
    }
    if levels < MIN_LEVELS:
        return result

    x = np.log(pairs[parameter].to_numpy(dtype=float))
    y = np.log(pairs[TARGET].to_numpy(dtype=float))
    if np.ptp(y) == 0:
        # A constant response has slope zero, but its R-squared is undefined.
        result.update(exponent=0.0, status="constant_cpu_time")
    else:
        fit = linregress(x, y)
        result.update(
            exponent=float(fit.slope),
            r_squared_log=float(fit.rvalue ** 2),
            status="ok",
        )
    return result

def analyze(csv_path):
    df = pd.read_csv(csv_path, skipinitialspace=True, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names after trimming whitespace.")
    missing = {"entity", "function", TARGET} - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    for column in ["entity", "function"]:
        df[column] = df[column].astype("string").str.strip()
    df = df.dropna(subset=["entity", "function"])
    df = df[(df["entity"] != "") & (df["function"] != "")]
    if df.empty:
        raise ValueError("No rows have a valid entity and function.")

    parameters = [column for column in PARAMETERS if column in df.columns]
    if not parameters:
        raise ValueError("No configured parameter columns were found.")

    # Keep AUTH/setup and MIX/setup separate, while pooling entity IDs.
    groups = list(df.groupby(["entity", "function"], sort=True))
    exponents = np.full((len(groups), len(parameters)), np.nan)
    r_squared = np.full_like(exponents, np.nan)
    records = []
    for row, ((entity, function), group) in enumerate(groups):
        for col, parameter in enumerate(parameters):
            fit = fit_scaling(group, parameter)
            exponents[row, col] = fit["exponent"]
            r_squared[row, col] = fit["r_squared_log"]
            records.append({"entity": entity, "function": function,
                            "parameter": parameter, **fit})
    labels = [f"{entity} / {function}" for (entity, function), _ in groups]
    return exponents, r_squared, labels, parameters, pd.DataFrame(records)


def plot_heatmap(exponents, r_squared, labels, parameters, output_prefix):
    rows, cols = exponents.shape
    finite = exponents[np.isfinite(exponents)]
    limit = max(1.0, float(np.abs(finite).max())) if finite.size else 1.0
    cmap = LinearSegmentedColormap.from_list(
        "cpu_scaling", [(0, "#2166ac"), (0.5, "#dddddd"),
                        (0.75, "#f4a582"), (1, "#b40426")]
    )
    cmap.set_bad("#f4f4f4")
    fig, ax = plt.subplots(
        figsize=(max(9, cols * 1.65 + 2), max(3.5, rows * 0.85 + 2)),
        constrained_layout=True,
    )
    heatmap = ax.imshow(
        np.ma.masked_invalid(exponents), cmap=cmap,
        vmin=-limit, vmax=limit, aspect="auto", interpolation="nearest",
    )
    ax.set_xticks(np.arange(cols), labels=[PARAMETERS[p] for p in parameters])
    ax.set_yticks(np.arange(rows), labels=labels)
    ax.set_title("CPU-time scaling by function and parameter", pad=16)
    ax.tick_params(axis="both", which="major", length=0, pad=8)
    ax.set_xticks(np.arange(cols + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(rows + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for row in range(rows):
        for col in range(cols):
            beta, r2 = exponents[row, col], r_squared[row, col]
            if not np.isfinite(beta):
                ax.text(col, row, "N/A", ha="center", va="center", color="#888888")
                continue
            red, green, blue, _ = cmap(heatmap.norm(beta))
            dark = 0.2126 * red + 0.7152 * green + 0.0722 * blue < 0.45
            text_color = "white" if dark else "#171717"
            secondary_color = "#eeeeee" if dark else "#666666"
            shown_beta = 0.0 if abs(beta) < 0.005 else beta
            ax.text(col, row - 0.10, f"{shown_beta:.2f}", ha="center", va="center",
                    fontsize=13, color=text_color)
            r2_text = rf"$R^2={r2:.2f}$" if np.isfinite(r2) else r"$R^2$ = N/A"
            ax.text(col, row + 0.16, r2_text, ha="center", va="center",
                    fontsize=10, color=secondary_color)

    fig.colorbar(heatmap, ax=ax, pad=0.03, label=r"Scaling exponent $\beta$")
    ax.set_xlabel(
        "Pairwise log-log fits; other parameters are not controlled.\n"
        f"N/A: fewer than {MIN_LEVELS} positive parameter levels; "
        r"$R^2$ is measured in log space.",
        labelpad=18, fontsize=9, color="#555555",
    )
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for extension in ["png", "pdf"]:
        fig.savefig(f"{output_prefix}.{extension}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="?", default="benchmark/data/timing.csv", help="Input CSV")
    parser.add_argument("--output-prefix", default="benchmark/result/cpu_scaling",
                        help="Output path without extension (default: cpu_scaling)")
    args = parser.parse_args()
    exponents, r_squared, labels, parameters, records = analyze(args.csv)
    plot_heatmap(exponents, r_squared, labels, parameters, args.output_prefix)
    records.to_csv(f"{args.output_prefix}_fits.csv", index=False)
    print(f"Saved {args.output_prefix}.png, {args.output_prefix}.pdf, "
          f"and {args.output_prefix}_fits.csv")
    fitted = int(records["exponent"].notna().sum())
    print(f"Fitted {fitted}/{len(records)} cells; "
          "see the fits CSV for sample counts and N/A reasons.")


if __name__ == "__main__":
    main()