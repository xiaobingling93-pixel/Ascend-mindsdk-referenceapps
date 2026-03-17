"""
Copyright 2026 Huawei Technologies Co., Ltd

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import json
import os
import shutil
import argparse

def rename_keys_in_jsonl(input_file, output_file=None):
    """
    Rename keys in a JSONL file: 'answer' -> 'ground_truth', 'question' -> 'problem'.

    If output_file is not provided, the original file is modified in-place
    (a backup is created automatically with suffix '.bak').

    Args:
        input_file (str): Path to input JSONL file.
        output_file (str, optional): Path to output file. If None, modify in-place.

    Raises:
        FileNotFoundError: If input_file does not exist.
    """
    # Check if input file exists
    if not os.path.isfile(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Determine output and handle in-place modification with backup
    if output_file is None:
        # Create a backup first
        backup_file = input_file + '.bak'
        shutil.copy2(input_file, backup_file)
        print(f"Backup created: {backup_file}")
        # We'll write to a temporary file then replace the original
        temp_file = input_file + '.tmp'
        out_path = temp_file
    else:
        out_path = output_file

    processed = 0
    errors = 0

    try:
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(out_path, 'w', encoding='utf-8') as outfile:

            for line_num, line in enumerate(infile, 1):
                line = line.strip()
                if not line:
                    continue  # skip empty lines

                try:
                    obj = json.loads(line)
                    # Rename keys if present
                    if 'answer' in obj:
                        obj['ground_truth'] = obj.pop('answer')
                    if 'question' in obj:
                        obj['problem'] = obj.pop('question')
                    outfile.write(json.dumps(obj, ensure_ascii=False) + '\n')
                    processed += 1
                except json.JSONDecodeError as e:
                    print(f"Warning: line {line_num} is not valid JSON, skipped. Error: {e}")
                    errors += 1
                    continue

        print(f"Processed {processed} lines, skipped {errors} lines.")

        # If in-place modification, replace original with temp file
        if output_file is None:
            os.replace(temp_file, input_file)
            print(f"Original file updated: {input_file}")

    except Exception as e:
        # Clean up temp file if it exists
        if output_file is None and os.path.exists(temp_file):
            os.remove(temp_file)
        raise e

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename keys in a JSONL file: 'answer' -> 'ground_truth', 'question' -> 'problem'.")
    parser.add_argument("input", help="Path to input JSONL file.")
    parser.add_argument("output", nargs="?", default=None, help="Path to output JSONL file. If not provided, modifies input file in-place (a backup with suffix .bak is created).")
    args = parser.parse_args()

    rename_keys_in_jsonl(args.input, args.output)