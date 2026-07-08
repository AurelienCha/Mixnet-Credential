import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

ORIGINAL_RESULTS = ".benchmark/.data/original_sphinx_time.csv"
OUR_RESULTS = ".benchmark/.data/timing.csv"

df = pd.read_csv(OUR_RESULTS)

# Clean & Filter - Implementation results
df['function'] = df['function'].str.strip()
df = df[df['function'].isin(['build_packet', 'process_header'])]
df = df.replace('build_packet', 'client')
df = df.replace('process_header', 'mixnode')

df = df.assign(CREDENTIAL=lambda x: x["CREDENTIAL"].map({1: "Credentials", 0: "No Credentials"}))

df['time'] = df['CPU_time_ms']
df['path_length'] = df['PATH_LENGTH']
df['version'] = df['CREDENTIAL']


df = df[['path_length', 'time', 'function', 'version']]

original = pd.read_csv(ORIGINAL_RESULTS)

original = (
    original.melt(
        id_vars="path_length",
        value_vars=["package_time", "process_time"],
        var_name="function",
        value_name="time"
    )
    .assign(
        function=lambda x: x["function"].map({
            "package_time": "client",
            "process_time": "mixnode"
        }),
        version="Original"
    )
)

df = pd.concat([df, original], ignore_index=True)
df = df[df['path_length'] >= 3]
df = df[df['path_length'] <= 7]

sns.lineplot(data=df, x="path_length", y="time", hue="version", style="function")
plt.xticks([3,4,5,6,7])
plt.ylabel("time (ms)")
plt.savefig(f".benchmark/.results/test.png", dpi=300)
