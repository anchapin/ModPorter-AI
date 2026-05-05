import os
import json
import time
import asyncio
import argparse
from ai_engine.mmsd.pipeline.dual_teacher import DualTeacherPipeline


def load_processed(output_path: str) -> set:
    processed = set()
    if os.path.exists(output_path):
        with open(output_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    processed.add(entry["instruction"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return processed


def load_new_instructions(input_path: str, processed: set) -> list:
    instructions = []
    if os.path.exists(input_path):
        with open(input_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    instr = entry["instruction"]
                    if instr not in processed:
                        instructions.append(instr)
                except (json.JSONDecodeError, KeyError):
                    continue
    return instructions


def run_sequential(pipeline, instructions, output_path, processed, target):
    with open(output_path, "a") as out_f:
        for instr in instructions:
            pair = pipeline.synthesize_pair(instr)
            if pair:
                out_f.write(json.dumps(pair) + "\n")
                out_f.flush()
                processed.add(instr)
                print(f"[{len(processed)}/{target}] Completed: {instr[:50]}...")
            else:
                print(f"  SKIP: Failed: {instr[:50]}...")

            if len(processed) >= target:
                break


async def run_parallel(pipeline, instructions, output_path, processed, target, concurrency):
    semaphore = asyncio.Semaphore(concurrency)

    async def process_one(instr):
        return await pipeline.synthesize_pair_async(instr, semaphore)

    batch_size = concurrency * 2
    idx = 0

    while idx < len(instructions) and len(processed) < target:
        batch = instructions[idx : idx + batch_size]
        idx += batch_size

        tasks = [process_one(instr) for instr in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        with open(output_path, "a") as out_f:
            for instr, result in zip(batch, results):
                if isinstance(result, Exception):
                    print(f"  SKIP: Exception: {str(result)[:80]}")
                    continue
                if result:
                    out_f.write(json.dumps(result) + "\n")
                    out_f.flush()
                    processed.add(instr)
                    print(f"[{len(processed)}/{target}] Completed: {instr[:50]}...")
                else:
                    print(f"  SKIP: Failed: {instr[:50]}...")

        if len(processed) >= target:
            break


def main():
    parser = argparse.ArgumentParser(description="MMSD Synthesis Pipeline")
    parser.add_argument("--parallel", type=int, default=1, help="Concurrency level (1=sequential)")
    parser.add_argument("--target", type=int, default=1400, help="Target pair count")
    args = parser.parse_args()

    input_path = "/home/alex/mmsd-work/data/raw/instructions.jsonl"
    output_path = "/home/alex/mmsd-work/data/processed/synthesis_pairs.jsonl"
    target = args.target
    concurrency = args.parallel

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pipeline = DualTeacherPipeline(model="local", api_base="http://localhost:8002/v1")

    processed = load_processed(output_path)

    print(
        f"Starting synthesis ({'parallel=' + str(concurrency) if concurrency > 1 else 'sequential'}). Target: {target} pairs."
    )

    while True:
        if len(processed) >= target:
            print(f"Goal of {target} reached. Exiting.")
            break

        instructions = load_new_instructions(input_path, processed)

        if not instructions:
            print(f"No new instructions ({len(processed)}/{target} done). Waiting 60s...")
            time.sleep(60)
            continue

        print(
            f"Found {len(instructions)} new instructions. Processing (concurrency={concurrency})..."
        )

        if concurrency > 1:
            asyncio.run(
                run_parallel(pipeline, instructions, output_path, processed, target, concurrency)
            )
        else:
            run_sequential(pipeline, instructions, output_path, processed, target)

        if len(processed) >= target:
            print(f"Goal of {target} reached. Exiting.")
            break


if __name__ == "__main__":
    main()
