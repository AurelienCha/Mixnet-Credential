import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from scipy.stats import linregress


OUTPUT = "benchmark/results/scaling.png"

PARAMS = [
    "PATH_LENGTH",
    "NBR_MIXNODES",
    "THRESHOLD",
    "NBR_AUTHORITIES",
]

CSV_FILE = "benchmark/data/timing.csv"


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
    # Authority
    "setup",
    "sign_PK",

    # Client
    "get_credential",
    "build_packet",

    # Mixnode
    "sign_public_key",
    "process",
])].copy()

df["time"] = df["CPU_time_ms"]

df["function"] = df["function"].replace({
    "get_credential": "Credential Issuance",
    "build_packet": "Header Construction",
    "process": "Packet Processing",
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
# AGGREGATE SETUP PHASE
# ============================================================
#
# SETUP PHASE =
#
#   (sum(setup) + sum(sign_PK)) / NBR_AUTHORITIES
#   +
#   sum(sign_public_key) / NBR_MIXNODES
#
# ============================================================

# ------------------------------------------------------------
# Authority-side setup
# ------------------------------------------------------------

authority_setup = (
    df[
        df["function"].isin([
            "setup",
            "sign_PK",
        ])
    ]
    .groupby(PARAMS, as_index=False)["time"]
    .sum()
)

authority_setup["time"] /= authority_setup["NBR_AUTHORITIES"]


# ------------------------------------------------------------
# Mixnode-side setup
# ------------------------------------------------------------

mixnode_setup = (
    df[
        df["function"] == "sign_public_key"
    ]
    .groupby(PARAMS, as_index=False)["time"]
    .sum()
)

mixnode_setup["time"] /= mixnode_setup["NBR_MIXNODES"]


# ------------------------------------------------------------
# Combine authority + mixnode setup
# ------------------------------------------------------------

setup_df = authority_setup.merge(
    mixnode_setup,
    on=PARAMS,
    how="outer",
    suffixes=("_authority", "_mixnode"),
)

setup_df["time"] = (
    setup_df["time_authority"].fillna(0)
    + setup_df["time_mixnode"].fillna(0)
)

setup_df["function"] = "Setup"


# Keep only the columns needed by df
setup_df = setup_df[
    PARAMS + ["time", "function"]
]


# ------------------------------------------------------------
# Remove raw setup functions
# ------------------------------------------------------------

other_df = df[
    ~df["function"].isin([
        "setup",
        "sign_PK",
        "sign_public_key",
    ])
].copy()


# ------------------------------------------------------------
# Add aggregated SETUP PHASE
# ------------------------------------------------------------

df = pd.concat(
    [
        other_df,
        setup_df,
    ],
    ignore_index=True,
)

# ============================================================
# ESTIMATE EMPIRICAL SCALING EXPONENT
#
# time ~ parameter^k
#
# log(time) = log(C) + k * log(parameter)
# ============================================================

def estimate_exponent(group, param):

    data = group[[param, "time"]].dropna()

    # Log-log regression requires positive values
    data = data[
        (data[param] > 0) &
        (data["time"] > 0)
    ]

    # Need at least 2 different parameter values
    if data[param].nunique() < 2:
        return np.nan, np.nan

    x = np.log(data[param].values)
    y = np.log(data["time"].values)

    fit = linregress(x, y)

    exponent = fit.slope
    r2 = fit.rvalue ** 2

    return exponent, r2


# ============================================================
# COMPUTE EXPONENT FOR EVERY FUNCTION × PARAMETER
# ============================================================

results = []

for function in sorted(df["function"].unique()):

    function_df = df[df["function"] == function]

    for param in PARAMS:

        exponent, r2 = estimate_exponent(
            function_df,
            param,
        )

        results.append({
            "function": function,
            "parameter": param,
            "exponent": exponent,
            "R2": r2,
        })


results_df = pd.DataFrame(results)
row_order = [
    "Setup",
    "Credential Issuance",
    "Header Construction",
    "Packet Processing",
]

# ============================================================
# EXPONENT TABLE
# ============================================================

exponent_table = results_df.pivot(
    index="function",
    columns="parameter",
    values="exponent",
)
exponent_table = exponent_table.reindex(row_order)


# ============================================================
# COMPLEXITY LABEL
# ============================================================

def complexity_label(k):

    if pd.isna(k):
        return "N/A"

    if abs(k) < 0.15:
        return "O(1)"

    if abs(k - 0.5) < 0.15:
        return "O(√n)"

    if abs(k - 1) < 0.15:
        return "O(n)"

    if abs(k - 2) < 0.25:
        return "O(n²)"

    if abs(k - 3) < 0.35:
        return "O(n³)"

    return f"O(n^{k:.2f})"


complexity_table = exponent_table.map(complexity_label)

# ============================================================
# R² TABLE
# ============================================================

r2_table = results_df.pivot(
    index="function",
    columns="parameter",
    values="R2",
)
r2_table = r2_table.reindex(row_order)


# ============================================================
# EXPONENT HEATMAP
# ============================================================


fig, ax = plt.subplots(figsize=(12, 7))

heatmap = sns.heatmap(
    exponent_table,
    annot=False,
    cmap="coolwarm",
    center=0,
    linewidths=0.5,
    cbar_kws={"label": "Scaling exponent"},
    ax=ax,
)

plt.title("")  # "Empirical Parameter Sensitivity"
plt.xlabel("") # "Parameter"
plt.ylabel("") # "Phase"

# ------------------------------------------------------------
# Rename x-axis parameters
# ------------------------------------------------------------

parameter_labels = {
    "PATH_LENGTH": r"Path length $m$",
    "NBR_MIXNODES": "# Mixnodes",
    "THRESHOLD": r"Threshold $k$",
    "NBR_AUTHORITIES": "# Authorities",
}
ax.set_xticklabels([parameter_labels.get(col, col) for col in exponent_table.columns], fontsize=14)
ax.set_yticklabels(ax.get_yticklabels(), fontsize=12)

# ------------------------------------------------------------
# Colorbar label
# ------------------------------------------------------------

cbar = heatmap.collections[0].colorbar
cbar.set_label("Scaling exponent", rotation=90, fontsize=14)
cbar.ax.yaxis.set_label_position("left")

# ============================================================
# ANNOTATION
# ============================================================

for i, row in enumerate(exponent_table.index):
    for j, col in enumerate(exponent_table.columns):

        k = exponent_table.loc[row, col]
        r2 = r2_table.loc[row, col]

        # First line: normal opacity
        ax.text(
            j + 0.5, i + 0.43,
            f"{k:.2f}",
            ha="center", va="center",
            fontsize=16,
            alpha=1.0
        )

        # Second line: semi-transparent
        ax.text(
            j + 0.5, i + 0.60,
            rf"$R^2$={r2:.2f}",
            ha="center", va="center",
            fontsize=12,
            alpha=0.5
        )

# ============================================================
# SAVE
# ============================================================

plt.tight_layout()
plt.savefig(
    OUTPUT[:-4] + ".png",
    dpi=300,
    bbox_inches="tight",
)

plt.close()
