import os
import glob
import matplotlib.pyplot as plt

# Press Shift+F10 to execute it or replace it with your code.
import numpy as np

exp_names = ["latency/test"]
savedir = "graphs/"
os.makedirs(savedir, exist_ok=True)

threads = 14
n_clients = 3
payload = 128
reads = 0
n_servers = [3, 5, 7]

algorithms = ["chain_mixed",
              "chainrep",
              "uring",
              "multi",
              "distinguished",
              "epaxos",
              "esolatedpaxos",
              "ring",
              ]


alg_mapper = {"chain_mixed": "ChainPaxos",
              "distinguished": "Multi-1Learn",
              "multi": "MultiPaxos",
              "ring": "RingPaxos",
              "chainrep": "ChainReplication",
              "uring": "U-RingPaxos",
              "epaxos": "EPaxos",
              "esolatedpaxos": "EPaxos-NoDeps"}

n_runs = 3
skip = 3
time_min = 30
time_max = 80


def average(lst):
    return sum(lst) / len(lst)


def weighted_average(lst):
    vals_sum = 0
    weight_sum = 0
    for (val, weight) in lst:
        vals_sum += (val * weight)
        weight_sum += weight
    return vals_sum / weight_sum


def check_folder_or_exit(path):
    if not os.path.isdir(path):
        print("No folder: " + path)
        exit(1)


def check_len_or_exit(obj_to_check, size, message=""):
    if not len(obj_to_check) == size:
        print("Size mismatch: " + str(size) + " " + str(len(obj_to_check)) + " - " + message)
        exit(1)


def get_idx_of(split, word, initial_look=0):
    for i in range(initial_look, len(split)):
        if split[i] == word:
            return i
    print("String not found: " + word + " in " + " ".join(split))
    return -1


def process_alg(alg_path):
    results_raw = {}
    # 1,2,3
    for run in range(1, n_runs + 1):
        results_raw[run] = {}
        run_path = alg_path + "/" + str(run)
        check_folder_or_exit(run_path)
        # 1,2,5,10,20,...
        thread_files = glob.glob(run_path + "/" + str(threads) + "_*")
        if not len(thread_files) == n_clients:
            print(str(len(thread_files)) + " instead of " + str(n_clients) + " clients for thread " +
                  str(threads) + " in path " + run_path)
            exit(1)
        client = 0
        # paravance-26, paravance-30,...
        for thread_file in thread_files:
            results_raw[run][client] = {}
            # print(thread_file)
            file = open(thread_file, 'r')
            for line in file.readlines()[skip:]:
                split = line.split()
                try:
                    time = int(split[2])

                    if time_min > time or time > time_max:
                        print("Unexpected time " + str(time) + " in file " + thread_file)
                        exit(1)

                    write_idx = get_idx_of(split, "[INSERT:", initial_look=7)
                    n_writes = int(split[write_idx + 1].strip(',').split('=')[1])
                    avg_write_lats = float(split[write_idx + 4].strip(',').split('=')[1])
                    results_raw[run][client][int(split[2])] = (avg_write_lats, n_writes)
                    if time == time_max:
                        break
                except:
                    print("Error parsing " + thread_file)
                    print("On line: " + line)
                    raise
            check_len_or_exit(results_raw[run][client], (time_max - time_min) / 10 + 1,
                              f"alg {alg} run {run} client {client}")
            client += 1
        check_len_or_exit(results_raw[run], n_clients)
    check_len_or_exit(results_raw, n_runs)

    avg_thread_lat_list = []
    for run in range(1, n_runs + 1):
        avg_run_lat_list = []
        for time in range(time_min, time_max + 1, 10):
            for client in range(0, n_clients):
                (lat, nOps) = results_raw[run][client][time]
                avg_run_lat_list.append((lat, nOps))
        avg_thread_lat_list.append(weighted_average(avg_run_lat_list))
    return (average(avg_thread_lat_list) / 1000, np.std(avg_thread_lat_list)/1000)


def create_plot(results_all, results_all_error):
    plt.rcParams.update({'font.size': 12})

    # plt.figure(figsize=(10, 8))

    labels = ['3', '5', '7']
    x = np.arange(len(labels))
    width = 0.9 / len(results_all)

    i = 0
    for alg in results_all.keys():
        lats = results_all[alg]
        errors = results_all_error[alg]
        plt.bar(x - (len(results_all)/2 * width) + width*i, lats, width, label=alg_mapper[alg],
                yerr=errors, capsize=3, alpha=1)
        i+=1

    plt.xlabel("Number of replicas")
    plt.ylabel("Average latency (ms)")
    plt.xticks(x, labels)
    plt.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(savedir + "latency" + "_" + str(n_servers) + ".pdf")

    plt.show()


if __name__ == '__main__':
    results_all = {}
    results_all_error = {}
    for exp_name in exp_names:
        for alg in algorithms:
            results_all[alg] = []
            results_all_error[alg] = []
            print(alg)
            for server in n_servers:
                alg_path = "logs/" + exp_name + "/client/" + str(server) + "/" + str(reads) + "/" + str(
                    payload) + "/" + alg
                check_folder_or_exit(alg_path)
                lat, error = process_alg(alg_path)
                results_all[alg].append(lat)
                results_all_error[alg].append(error)
            print(results_all[alg])
            print(results_all_error[alg])
        create_plot(results_all, results_all_error)