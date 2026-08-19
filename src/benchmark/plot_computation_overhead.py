import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

ORIGINAL_RESULTS = "benchmark/data/original_sphinx_time.csv"
OUR_RESULTS = "benchmark/data/timing.csv"
OUTPUT = "benchmark/results/computation_overhead.png"

blue, orange, green = sns.color_palette('deep', 3)
palette = {
    "Sphinx": green,
    "DSphinx": blue,
    "DSphinx + Credentials": orange,
}

def load_data():
    # DSphinx measurements
    dsphinx = pd.read_csv(OUR_RESULTS).copy()

    dsphinx["function"] = dsphinx["function"].str.strip()
    dsphinx = dsphinx[
        dsphinx["function"].isin(["build_packet", "process"])
    ].copy()

    dsphinx["function"] = dsphinx["function"].map({
        "build_packet": "Client",
        "process": "Mixnode",
    })

    dsphinx["Protocol"] = dsphinx["CREDENTIAL"].map({
        0: "DSphinx",
        1: "DSphinx + Credentials",
    })

    dsphinx["time"] = dsphinx["CPU_time_ms"]
    dsphinx["path_length"] = dsphinx["PATH_LENGTH"]

    dsphinx = dsphinx[["path_length", "time", "function", "Protocol"]]

    # Classical Sphinx is the baseline.
    sphinx = pd.read_csv(ORIGINAL_RESULTS)

    sphinx = (
        sphinx.melt(
            id_vars="path_length",
            value_vars=["package_time", "process_time"],
            var_name="function",
            value_name="time",
        )
        .assign(
            function=lambda x: x["function"].map({
                "package_time": "Client",
                "process_time": "Mixnode",
            }),
            Protocol="Sphinx",
        )
    )

    sphinx = sphinx[["path_length", "time", "function", "Protocol"]]

    dsphinx = dsphinx[(dsphinx["path_length"] >= 3) & (dsphinx["path_length"] <= 7)]
    sphinx = sphinx[(sphinx["path_length"] >= 3) & (sphinx["path_length"] <= 7)]

    # Compute overhead relative to classical Sphinx:
    #
    #   overhead (%) = (DSphinx - Sphinx) / Sphinx * 100
    #
    # The Sphinx value is matched by path length and function.
    baseline = sphinx.rename(columns={"time": "baseline_time"})[
        ["path_length", "function", "baseline_time"]
    ]

    overhead = dsphinx.merge(
        baseline,
        on=["path_length", "function"],
        how="left",
        validate="many_to_one",
    )

    overhead["overhead"] = (overhead["time"] / overhead["baseline_time"])

    # Add Sphinx itself as a reference line.
    sphinx_overhead = sphinx.copy()
    sphinx_overhead["overhead"] = 1.0

    return pd.concat(
        [
            overhead[["path_length", "function", "Protocol", "overhead"]],
            # sphinx_overhead[["path_length", "function", "Protocol", "overhead"]],
        ],
        ignore_index=True,
    )


def plot(df):
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(10, 4.8),
        sharex=True,
        constrained_layout=True,
    )

    for ax, function in zip(axes, ["Client", "Mixnode"]):
        subset = df[df["function"] == function]

        sns.lineplot(
            data=subset,
            x="path_length",
            y="overhead",
            hue="Protocol",
            style="Protocol",
            palette=palette,
            markers=True,
            dashes=False,
            linewidth=2.5,
            markersize=8,
            errorbar=None,
            ax=ax,
        )

        ax.set_title(f"{function} computational overhead relative to Sphinx")
        ax.set_xlabel("Path length (number of hops)")
        ax.set_ylabel("Overhead relative to Sphinx")
        ax.set_xticks([3, 4, 5, 6, 7])
        ax.grid(axis="y", alpha=0.25)

        if ax is axes[0]:
            ax.legend(title="Protocol")
        else:
            ax.get_legend().remove()

    fig.savefig(OUTPUT, dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    data = load_data()
    plot(data)