#!/usr/bin/env bash
set -euo pipefail
: "${NS3_ROOT:?Set NS3_ROOT to an installed ns-3 checkout.}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$NS3_ROOT/scratch"
cp "$ROOT/ns3/fsecure_scenario_export.cc" "$NS3_ROOT/scratch/fsecure_scenario_export.cc"
cd "$NS3_ROOT"
for nodes in 100 150 200; do
  for run in 101 102 103 104 105 106 107 108 1 2 3 4 5 6 7 8 9 10; do
    for attack in blackhole selective sybil_proxy; do
      output="$ROOT/outputs/ns3_scenarios/n${nodes}_seed${run}_${attack}"
      ./ns3 run "scratch/fsecure_scenario_export --nodes=$nodes --run=$run --attack=$attack --outDir=$output"
    done
  done
done
