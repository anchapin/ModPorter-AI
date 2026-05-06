import os
import json
import time
from ai_engine.mmsd.pipeline.dual_teacher import DualTeacherPipeline


def main():
    """
    Runs the synthesis pipeline on the generated instructions.
    Continuous mode: waits for new instructions if the target hasn't been reached.
    """
    input_path = "ai_engine/mmsd/data/raw/instructions.jsonl"
    output_path = "ai_engine/mmsd/data/processed/synthesis_pairs.jsonl"
    target_total = 1400

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pipeline = DualTeacherPipeline(model="qwen2.5-coder:3b")

    # Load already processed instructions to skip them
    processed_ids = set()
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    processed_ids.add(entry["instruction"])
                except json.JSONDecodeError:
                    continue

    print(f"Starting synthesis in continuous mode. Target: {target_total} pairs.")

    while True:
        current_synth_count = len(processed_ids)
        if current_synth_count >= target_total:
            print(f"Goal of {target_total} reached. Exiting.")
            break

        # Read available instructions
        available_instructions = []
        if os.path.exists(input_path):
            with open(input_path, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        instr = entry["instruction"]
                        if instr not in processed_ids:
                            available_instructions.append(instr)
                    except (json.JSONDecodeError, KeyError):
                        continue

        if not available_instructions:
            print(
                f"No new instructions to process ({current_synth_count}/{target_total} done). Waiting 60s..."
            )
            time.sleep(60)
            continue

        print(f"Found {len(available_instructions)} new instructions. Processing...")

        with open(output_path, "a") as out_f:
            for instr in available_instructions:
                pair = pipeline.synthesize_pair(instr)
                if pair:
                    out_f.write(json.dumps(pair) + "\n")
                    out_f.flush()
                    processed_ids.add(instr)
                    count = len(processed_ids)
                    print(f"[{count}/{target_total}] Completed: {instr[:50]}...")
                else:
                    print(f"  SKIP: Failed to synthesize (will retry next run): {instr[:50]}...")

                if len(processed_ids) >= target_total:
                    break


if __name__ == "__main__":
    main()
