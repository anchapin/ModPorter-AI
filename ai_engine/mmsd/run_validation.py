import os
import json
from ai_engine.mmsd.validators.code_validator import CodeValidator


def _has_error_fields(entry):
    fields = ["reasoning_trace", "java_source", "bedrock_source"]
    for field in fields:
        val = entry.get(field, "")
        if isinstance(val, str) and (val.startswith("Error:") or val.startswith("ERROR_PREFIX")):
            return True
    return False


def main():
    input_path = "ai_engine/mmsd/data/processed/synthesis_pairs.jsonl"
    output_path = "ai_engine/mmsd/data/processed/validated_pairs.jsonl"

    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    print("---- Running Validation on Synthetic Pairs ---")
    validator = CodeValidator()

    valid_count = 0
    total_count = 0
    skipped_error = 0
    skipped_invalid = 0

    with open(input_path, "r") as in_f, open(output_path, "w") as out_f:
        for line in in_f:
            total_count += 1
            try:
                entry = json.loads(line)
                instr = entry.get("instruction", "Unknown")
                print(f"Sample {total_count}: {instr[:50]}...")

                if _has_error_fields(entry):
                    print(f"  SKIP (error fields)")
                    skipped_error += 1
                    continue

                java_ok, java_msg = validator.validate_java(entry["java_source"])
                bedrock_ok, bedrock_msg = validator.validate_bedrock_json(entry["bedrock_source"])

                if java_ok and bedrock_ok:
                    print(f"  VALID")
                    out_f.write(json.dumps(entry) + "\n")
                    valid_count += 1
                else:
                    print(f"  INVALID (Java: {java_ok}, Bedrock: {bedrock_ok})")
                    print(f"    Java Error: {java_msg[:100]}")
                    print(f"    Bedrock Error: {bedrock_msg[:100]}")
                    skipped_invalid += 1

            except Exception as e:
                print(f"  Error processing line {total_count}: {e}")

    print(f"\nValidation complete:")
    print(f"  {valid_count} / {total_count} pairs passed.")
    print(f"  Skipped (error fields): {skipped_error}")
    print(f"  Skipped (validation):   {skipped_invalid}")
    print(f"Clean dataset saved to {output_path}")


if __name__ == "__main__":
    main()
