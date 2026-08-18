import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from pathlib import Path

ORIGINAL_RESULTS = ".benchmark/.data/original_sphinx_time.csv"
OUR_RESULTS = ".benchmark/.data/timing.csv"
OUTPUT = ".benchmark/.results/computation_time.png"

blue, orange, green = sns.color_palette('deep', 3)
palette = {
    "Sphinx": green,
    "DSphinx": blue,
    "DSphinx + Credentials": orange,
}

def load_data():

    # DSphinx get data
    df = pd.read_csv(OUR_RESULTS).copy()
    df["function"] = df["function"].str.strip()
    df = df[df["function"].isin(["build_packet", "process"])].copy()

    # Process data
    df["entity"] = df["function"].map({
        "build_packet": "Client",
        "process": "Mixnode",
    })

    df["Protocol"] = df["CREDENTIAL"].map({
        0: "DSphinx",
        1: "DSphinx + Credentials",
    })

    df["time"] = df["CPU_time_ms"]
    df["path_length"] = df["PATH_LENGTH"]

    # Classical Sphinx baseline
    original = pd.read_csv(ORIGINAL_RESULTS)

    original = (
        original.melt(
            id_vars="path_length",
            value_vars=["package_time", "process_time"],
            var_name="function",
            value_name="time",
        )
        .assign(
            entity=lambda x: x["function"].map({
                "package_time": "Client",
                "process_time": "Mixnode",
            }),
            Protocol="Sphinx",
        )
        .drop(columns="function")
    )

    # Filter and merged
    df = df[["path_length", "time", "entity", "Protocol"]]
    original = original[["path_length", "time", "entity", "Protocol"]]
    df = pd.concat([df, original], ignore_index=True)

    return df[(df["path_length"] >= 3) & (df["path_length"] <= 7)].copy()


def plot(df):
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(10, 4.8),
        sharex=True,
        constrained_layout=True,
    )

    for ax, entity in zip(axes, ["Client", "Mixnode"]):
        subset = df[df["entity"] == entity]

        sns.lineplot(
            data=subset,
            x="path_length",
            y="time",
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


        ax.set_title(f"{entity} computation")
        ax.set_xlabel("Path length (number of hops)")
        ax.set_ylabel("Computation time (ms)")
        ax.set_xticks([3, 4, 5, 6, 7])
        ax.grid(axis="y", alpha=0.25)

        # Only keep one legend for the whole figure.
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
