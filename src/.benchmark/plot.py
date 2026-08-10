import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

PARAMS = [
    "PATH_LENGTH",
    "NBR_MIXNODES",
    "NBR_CLIENT",
    "THRESHOLD",
    "NBR_AUTHORITIES",
]

metric = "CPU_time_ms"
CSV_FILE = ".benchmark/.data/timing.csv"
df = pd.read_csv(CSV_FILE)
df = df.loc[df['CREDENTIAL']==1]
df['function'] = df['function'].str.strip()

AUTH_FCTS = ['sign_mix', 'sign_client', 'setup',   'send_and_aggregate_shares', 'sign_params', 'verif_sign_params']
CLIENT_FCTS = ['get_credential', 'build_packet',   'encode_destination','select_mixnodes','derive_shared_secrets','update_credential','compute_layers',   'initial_layer', 'add_layer', 'compute_gamma']
MIX_FCTS = ['sign_public_key', 'process_header',   'verify_credential','compute_shared_secret','verify_integrity','decrypt_beta','update_alpha','update_credential','get_next_hop']

FCTS = {
    'Authority': ['sign_mix', 'sign_client', {
        'setup': ['send_and_aggregate_shares', 'sign_params', 'verif_sign_params']
    }],
    'Client': ['get_credential', {
        'build_packet': ['encode_destination','select_mixnodes','derive_shared_secrets','update_credential', {
            'compute_layers': ['initial_layer', 'add_layer', 'compute_gamma']
        }]
    }],
    'Mixnodes': ['sign_public_key', {
        'process_header': ['verify_credential','compute_shared_secret','verify_integrity','decrypt_beta','update_alpha','update_credential','get_next_hop']
    }]
}


fct_groups = [
    ("AUTH", AUTH_FCTS),
    ("CLIENT", CLIENT_FCTS),
    ("MIX", MIX_FCTS),
]

# Compute exponents for all function groups
all_results = {}
for group_name, fcts in fct_groups:
    results = []
    for func in fcts:
        df_f = df[df["function"] == func]
        for param in PARAMS:
            sub = df_f[[param, metric]].dropna()
            x = sub[param].values.astype(float)
            y = sub[metric].values.astype(float)

            x = np.where(x <= 0, np.nan, x)
            y = np.where(y <= 0, np.nan, y)
            mask = ~np.isnan(x) & ~np.isnan(y)
            x = x[mask]
            y = y[mask]

            if len(x) > 1:
                logx = np.log(x)
                logy = np.log(y)
                b, loga = np.polyfit(logx, logy, 1)
                results.append({"function": func, "parameter": param, "b": b})

    all_results[group_name] = pd.DataFrame(results).pivot(index="function", columns="parameter", values="b")

# Find global min/max for consistent scale
vmin = min(df.min().min() for df in all_results.values())
vmax = max(df.max().max() for df in all_results.values())

# Create figure with gridspec for colorbar spanning full height
fig = plt.figure(figsize=(19, 12))
gs = gridspec.GridSpec(3, 2, figure=fig, width_ratios=[20, 1], hspace=0.1, wspace=0.1)

last_im = None
for idx, (group_name, _) in enumerate(fct_groups):
    ax = fig.add_subplot(gs[idx, 0])

    pivot = all_results[group_name]
    im = sns.heatmap(pivot, annot=True, fmt=".1f", cmap="coolwarm", center=1, vmin=vmin, vmax=vmax, ax=ax, cbar=False)#, yticklabels=False)
    last_im = im

    ax.yaxis.set_label_position("right")
    ax.set_ylabel(group_name, fontsize=14, fontweight='bold')

    # Only show x-axis labels on bottom plot
    if idx < 2:
        ax.set_xticklabels([])
        ax.set_xlabel('', fontsize=14, fontweight='bold')
    else:
        ax.set_xlabel('', fontsize=14, fontweight='bold')

# Create colorbar spanning all three subplots
cax = fig.add_subplot(gs[:, 1])
cbar = fig.colorbar(last_im.collections[0], cax=cax)
cbar.set_label('Degree of scaling', fontsize=13)
plt.suptitle("Degree of scaling for the CPU time execution for each functions", fontsize=16)
plt.show()

fig.savefig(".benchmark/.results/CPU_scaling.png")