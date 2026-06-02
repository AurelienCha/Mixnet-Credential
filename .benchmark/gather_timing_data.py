import pandas as pd
from pathlib import Path

SHORT_NAME ={'p': 'PATH_LENGTH', 'm': 'NBR_MIXNODES', 'c': 'NBR_CLIENT', 't':'THRESHOLD', 'a':'NBR_AUTHORITIES', 'z':'CREDENTIAL'}

# Get all CSV files
root_dir = Path(".benchmark/.data/.logs")
csv_files = list(root_dir.rglob("*.csv"))
print(f"{len(csv_files)} CSV files found")


dfs = []
for file in csv_files:
    df = pd.read_csv(file, names=["timestamp", "entity", "entity_id", "direction", "DESTINATION", "DESTINATION_ID", "type", "Hash", "function", "CPU_time_ms", "wall_time_ms", "credential"])

    # Drop unused columns
    df.drop(columns=["direction", "DESTINATION", "DESTINATION_ID", "type", "Hash"], inplace=True)

    # Extract time
    df["CPU_time_ms"] = df["CPU_time_ms"].str.extract(r"([\d.]+)").astype(float)
    df["wall_time_ms"] = df["wall_time_ms"].str.extract(r"([\d.]+)").astype(float)

    # Keep only rows with timing info
    df = df[df["CPU_time_ms"].notna()]

    # Add script parameters
    for val in file._str.split('/')[3].split('_'):
        df[SHORT_NAME[val[0]]] = int(val[1:])

    dfs.append(df)

table = pd.concat(dfs, ignore_index=True)
table["timestamp"] = table["timestamp"].str.strip("[]")

table.to_csv(".benchmark/.data/timing.csv", index=False)
