import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from scipy.stats import linregress

*_, color1, color2 = sns.color_palette('deep', 5)
palette = {
    "Setup": color1,
    "Credential Issuance": color2
}

OUTPUT = ".benchmark/.results/setup.png"

PARAMS = [
    "PATH_LENGTH",
    "NBR_MIXNODES",
    "THRESHOLD",
    "NBR_AUTHORITIES",
]

CSV_FILE = ".benchmark/.data/timing.csv"


# ============================================================
# LOAD DATA
# ============================================================

df = pd.read_csv(CSV_FILE)

df = df.loc[df["CREDENTIAL"] == 1].copy()

df["function"] = df["function"].str.strip()


# ============================================================
# SELECT FUNCTIONS
# ============================================================

df = df[df["function"].isin([
    "setup",
    "get_credential",
])].copy()


df["time"] = df["CPU_time_ms"]

df["function"] = df["function"].replace({
    "setup": "Setup",
    "get_credential": "Credential Issuance",
})

df = df[
    [
        "time",
        "function",
        "PATH_LENGTH",
        "NBR_MIXNODES",
        "THRESHOLD",
        "NBR_AUTHORITIES",
    ]
]

# ============================================================
# THRESHOLD SCALING PLOT
# ============================================================

# Only keep the two operations we want to compare
df = df[
    df["function"].isin([
        "Setup",
        "Credential Issuance",
    ])
].copy()


# ============================================================
# PLOT
# ============================================================

fig, ax = plt.subplots(figsize=(9, 6))
sns.lineplot(
    data=df,
    x="THRESHOLD",
    y="time",
    hue="function",
    style="function",
    palette=palette,
    markers=True,
    dashes=False,
    linewidth=2.5,
    markersize=8,
    errorbar=None,
    ax=ax,
)
# ax.set_title("Computation Time as a Function of the Threshold k")
ax.set_xlabel("Reconstruction threshold k")
ax.set_ylabel("Computation time (ms)")
ax.grid(axis="y", alpha=0.25)
ax.legend(title=None)#, frameon=False)

fig.savefig(OUTPUT, dpi=300, bbox_inches="tight")
plt.close(fig)