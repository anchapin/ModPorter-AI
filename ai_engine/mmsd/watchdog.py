#!/usr/bin/env python3
"""
MMSD Pipeline Watchdog
Monitors instruction generation, then automatically swaps to synthesis phase.
"""

import os
import sys
import time
import json
import signal
import subprocess
import requests

INSTR_PATH = "/home/alex/mmsd-work/data/raw/instructions.jsonl"
SYNTH_PATH = "/home/alex/mmsd-work/data/processed/synthesis_pairs.jsonl"
LOG_DIR = "/home/alex/mmsd-work/logs"
LLAMA_BIN = "/home/alex/.local/lib/llama/llama-server"
LLAMA_DIR = "/home/alex/.local/lib/llama"
MODEL_CACHE = "/home/alex/.cache/llmfit/models"
PYTHONPATH = "/home/alex/Projects/portkit"
TARGET = 1400
POLL_INTERVAL = 60

PHASE1_MODEL = f"{MODEL_CACHE}/Phi-mini-MoE-instruct-Q6_K.gguf"
PHASE1_PORT = 8001
PHASE1_NGL = 40
PHASE1_CTX = 4096

PHASE2_MODEL = f"{MODEL_CACHE}/Qwen2.5-Coder-3B-Instruct-Q8_0.gguf"
PHASE2_PORT = 8002
PHASE2_NGL = 99
PHASE2_CTX = 8192
PHASE2_THREADS = 6
PHASE2_BATCH = 512


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r") as f:
        return sum(1 for _ in f)


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def get_pid_on_port(port):
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split("\n")
        return [int(p) for p in pids if p.strip()]
    except Exception:
        return []


def kill_port(port, timeout=10):
    pids = get_pid_on_port(port)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            log(f"  Killed PID {pid} on port {port}")
        except ProcessLookupError:
            pass
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not get_pid_on_port(port):
            return True
        time.sleep(1)
    for pid in get_pid_on_port(port):
        try:
            os.kill(pid, signal.SIGKILL)
            log(f"  Force killed PID {pid}")
        except ProcessLookupError:
            pass
    return True


def start_llama_server(model, port, ngl, ctx, extra_flags=""):
    cmd = (
        f"{LLAMA_BIN} -m {model} --port {port} -ngl {ngl} -c {ctx} "
        f"{extra_flags}"
    )
    log_file = f"{LOG_DIR}/llama_server_port{port}.log"
    proc = subprocess.Popen(
        cmd.split(),
        cwd=LLAMA_DIR,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
    )
    log(f"  Started llama-server PID {proc.pid} on port {port}")
    for _ in range(30):
        time.sleep(1)
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=2)
            if r.status_code == 200:
                log(f"  Port {port} healthy")
                return proc
        except Exception:
            pass
    log(f"  WARNING: Port {port} not healthy after 30s")
    return proc


def wait_for_server(port, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def start_script(script_path, log_name, pythonpath=None, extra_args=""):
    env = os.environ.copy()
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    log_file = f"{LOG_DIR}/{log_name}"
    cmd = ["python3", "-u", script_path]
    if extra_args:
        cmd.extend(extra_args.split())
    proc = subprocess.Popen(
        cmd,
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )
    log(f"  Started {script_path} PID {proc.pid} {' '.join(cmd[2:])}")
    return proc


def phase1_status():
    instr_count = count_lines(INSTR_PATH)
    synth_count = count_lines(SYNTH_PATH)
    log(f"Phase 1 — Instructions: {instr_count}/{TARGET}, Synthesis: {synth_count}/{TARGET}")
    return instr_count


def phase2_status():
    synth_count = count_lines(SYNTH_PATH)
    instr_count = count_lines(INSTR_PATH)
    log(f"Phase 2 — Synthesis: {synth_count}/{TARGET}, Instructions available: {instr_count}")
    return synth_count


def main():
    log("=" * 60)
    log("MMSD Pipeline Watchdog starting")
    log(f"Target: {TARGET} pairs")
    log("=" * 60)

    instr_count = count_lines(INSTR_PATH)
    synth_count = count_lines(SYNTH_PATH)

    if synth_count >= TARGET:
        log(f"Synthesis already at {synth_count}/{TARGET}. Done!")
        return

    if instr_count >= TARGET:
        log(f"Instructions already at {instr_count}/{TARGET}. Starting synthesis phase.")
        run_phase2()
        return

    run_phase1_then_phase2()


def run_phase1_then_phase2():
    log("--- PHASE 1: Instruction Generation ---")
    if not wait_for_server(PHASE1_PORT):
        log("Starting instruction gen server...")
        start_llama_server(PHASE1_MODEL, PHASE1_PORT, PHASE1_NGL, PHASE1_CTX)

    script_running = get_pid_on_port(PHASE1_PORT)
    if not script_running:
        log("Instruction gen server not running. Check manually.")
        log("Waiting for instruction gen to reach target...")

    last_count = 0
    stall_ticks = 0
    while True:
        count = phase1_status()
        if count >= TARGET:
            log(f"Instruction target reached ({count}/{TARGET})!")
            break
        if count == last_count:
            stall_ticks += 1
            if stall_ticks >= 10:
                log(f"WARNING: No progress for {stall_ticks * POLL_INTERVAL}s")
                if stall_ticks >= 30:
                    log("Stalled for 30 min. Something may be wrong.")
        else:
            stall_ticks = 0
        last_count = count
        time.sleep(POLL_INTERVAL)

    log("Shutting down Phase 1...")
    try:
        for pid in get_pid_on_port(PHASE1_PORT):
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    kill_port(PHASE1_PORT)
    time.sleep(5)

    run_phase2()


def run_phase2():
    log("--- PHASE 2: Synthesis ---")
    log(f"Starting synthesis server (Qwen2.5-Coder-3B Q8_0)...")
    start_llama_server(
        PHASE2_MODEL, PHASE2_PORT, PHASE2_NGL, PHASE2_CTX,
        extra_flags=f"-t {PHASE2_THREADS} -b {PHASE2_BATCH}"
    )

    log("Starting synthesis script (parallel=3)...")
    start_script(
        "/home/alex/mmsd-work/pipeline/run_synthesis.py",
        "synthesis.log",
        pythonpath=PYTHONPATH,
        extra_args="--parallel 3",
    )

    last_count = 0
    stall_ticks = 0
    while True:
        count = phase2_status()
        if count >= TARGET:
            log(f"Synthesis target reached ({count}/{TARGET})!")
            log("Pipeline complete!")
            break
        if count == last_count:
            stall_ticks += 1
            if stall_ticks >= 10:
                log(f"WARNING: No progress for {stall_ticks * POLL_INTERVAL}s")
                if stall_ticks >= 30:
                    log("Stalled for 30 min. Something may be wrong.")
        else:
            stall_ticks = 0
        last_count = count
        time.sleep(POLL_INTERVAL)

    log("Shutting down...")
    kill_port(PHASE2_PORT)


if __name__ == "__main__":
    main()
