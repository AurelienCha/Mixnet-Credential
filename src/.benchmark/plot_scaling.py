import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

OUTPUT = ".benchmark/.results/scaling.png"

PARAMS = [
    "PATH_LENGTH",
    "NBR_MIXNODES",
    "THRESHOLD",
    "NBR_AUTHORITIES",
]

metric = "CPU_time_ms"
CSV_FILE = ".benchmark/.data/timing.csv"
df = pd.read_csv(CSV_FILE)
df = df.loc[df['CREDENTIAL']==1]
df['function'] = df['function'].str.strip()

df = df[df["function"].isin([
    'setup', 'send_and_aggregate_shares', 'sign_params', 'sign_mix', 'sign_client',  # authority
    'get_credential', 'build_packet',                                                # client
    'sign_public_key', 'process'                                              # mixnode 
])].copy()


df["time"] = df["CPU_time_ms"]
df = df[['entity', 'time', 'function', 'PATH_LENGTH', 'NBR_MIXNODES', 'NBR_CLIENT', 'THRESHOLD', 'NBR_AUTHORITIES']]

# df = df.groupby(['function','entity']+PARAMS).sum()

###################################################

from scipy.stats import linregress
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# ------------------------------------------------------------
# Estimate empirical scaling exponent
#
# time ~ parameter^k
#
# log(time) = log(C) + k * log(parameter)
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Compute exponent for every function × parameter
# ------------------------------------------------------------

results = []

for function in sorted(df["function"].unique()):

    function_df = df[df["function"] == function]

    for param in PARAMS:

        exponent, r2 = estimate_exponent(
            function_df,
            param
        )

        results.append({
            "function": function,
            "parameter": param,
            "exponent": exponent,
            "R2": r2,
        })


results_df = pd.DataFrame(results)


# ------------------------------------------------------------
# Exponent table
# ------------------------------------------------------------

exponent_table = results_df.pivot(
    index="function",
    columns="parameter",
    values="exponent"
)

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

print("\nEmpirical complexity:")
print(complexity_table.to_string())

# print("\nEmpirical scaling exponents:")
# print(exponent_table.round(2).to_string())

### GRAPH

plt.figure(figsize=(12, 7))

sns.heatmap(
    exponent_table,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    center=0,
    linewidths=0.5,
    cbar_kws={"label": "Scaling exponent k"}
)

plt.title("Empirical Scaling Exponents")
plt.xlabel("Parameter")
plt.ylabel("Function")

plt.xticks(rotation=30, ha="right")
plt.tight_layout()

plt.savefig(OUTPUT, dpi=300, bbox_inches="tight")
plt.close()

r2_table = results_df.pivot(
    index="function",
    columns="parameter",
    values="R2"
)

plt.figure(figsize=(12, 7))

sns.heatmap(
    r2_table,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    center=0,
    linewidths=0.5,
    cbar_kws={"label": "Scaling exponent k"}
)

plt.title("Empirical Scaling Exponents")
plt.xlabel("Parameter")
plt.ylabel("Function")

plt.xticks(rotation=30, ha="right")
plt.tight_layout()

plt.savefig(OUTPUT[:-4]+"_r.png", dpi=300, bbox_inches="tight")
plt.close()