import os
import time
import psutil
from datetime import datetime

def count_lines(file_path):
    if not os.path.exists(file_path):
        return 0
    with open(file_path, "r") as f:
        return sum(1 for _ in f)

def find_pids():
    found = {"generator": "N/A", "synthesis": "N/A"}
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            info = proc.info
            if not info['cmdline']:
                continue
            cmds = " ".join(info['cmdline'])
            if "gen_instructions.py" in cmds:
                found["generator"] = info['pid']
            if "run_synthesis.py" in cmds or "ai_engine.mmsd.pipeline.run_synthesis" in cmds:
                found["synthesis"] = info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found

def main():
    instr_path = "ai_engine/mmsd/data/raw/instructions.jsonl"
    synth_path = "ai_engine/mmsd/data/processed/synthesis_pairs.jsonl"
    log_path = "ai_engine/mmsd/data/health_check.log"
    target = 1400

    print(f"MMSD Health Check started. Logging to {log_path}")

    while True:
        instr_count = count_lines(instr_path)
        synth_count = count_lines(synth_path)
        pids = find_pids()
        
        gen_pid = pids["generator"]
        syn_pid = pids["synthesis"]
        
        gen_status = "RUNNING" if gen_pid != "N/A" else "STOPPED"
        syn_status = "RUNNING" if syn_pid != "N/A" else "STOPPED"
        
        # Simple estimation: assuming 2.5 minutes per synthesis pair
        remaining = target - synth_count
        etc_minutes = remaining * 2.5
        etc_hours = etc_minutes / 60
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = (
            f"[{now}]\n"
            f"  Generator (PID {gen_pid}): {gen_status}\n"
            f"  Synthesis (PID {syn_pid}): {syn_status}\n"
            f"  Progress: {synth_count}/{target} pairs synthesized ({instr_count} instructions ready)\n"
            f"  Estimated Time Remaining: ~{etc_hours:.1f} hours\n"
            f"-------------------------------------------\n"
        )
        
        with open(log_path, "a") as f:
            f.write(log_entry)
        
        if synth_count >= target:
            with open(log_path, "a") as f:
                f.write(f"[{now}] Target of {target} pairs reached! Health check terminating.\n")
            break
            
        time.sleep(3600) # Check hourly

if __name__ == "__main__":
    main()
