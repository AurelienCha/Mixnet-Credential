if __name__ == "__main__":
    # IMPORT AND ADAPT THE TEST FUNCTION
    import _external_code.sphinxmix.SphinxClient as sc
    import inspect

    source = inspect.getsource(sc.test_c25519)
    source = source.replace(
        "def test_c25519(rep=100, payload_size=1024 * 10):",
        "def test_c25519(r, rep=100, payload_size=1024 * 10):"
    )
    source = source.replace("r = 5", "")

    namespace = dict(sc.__dict__)  # reuse original module globals
    exec(source, namespace)
    test_c25519 = namespace["test_c25519"]

    # RUN TEST

    import matplotlib.pyplot as plt
    import csv

    RESULT_FOLDER = '.results/'
    
    times_packages = []
    times_processes = []

    # Run test_c25519 for path lengths 1 to 7 and collect timings of Original Sphinx implementation of G. Danezis
    for r in range(1, 8):
        try:
            T_package, T_process = test_c25519(r)

            times_packages.append((r, T_package))
            times_processes.append((r, T_process))

        except Exception as e:
            print(f"Error occurred for path_length {r}: {e}")

    # Save CSV
    with open(f"{RESULT_FOLDER}original_sphinx_computation_time.csv", "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "path_length",
            "package_time",
            "process_time"
        ])

        for (r1, pkg), (_, proc) in zip(times_packages, times_processes):
            writer.writerow([r1, pkg, proc])

    # Prepare data for plotting
    x = [r for r, _ in times_packages]
    y_package = [t for _, t in times_packages]
    y_process = [t for _, t in times_processes]

    # Plot
    plt.figure(figsize=(8, 5))

    plt.plot(x, y_package, marker="o", label="Packaging")
    plt.plot(x, y_process, marker="s", label="Processing")

    plt.xlabel("Path length")
    plt.ylabel("Time (seconds)")
    plt.title("Sphinx Timing Benchmark")

    plt.grid(True)
    plt.legend()

    plt.tight_layout()

    # Save figure
    plt.savefig(f"{RESULT_FOLDER}original_sphinx_computation_time.png", dpi=300)

    # Optional: display the plot interactively
    plt.show() 
