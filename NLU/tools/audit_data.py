import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.labels import ACTION_LABELS, NER_TAGS, OBJECT_LABELS

NER_TAG_ALIASES = {
    "B-DES": "B-CONTENT",
    "I-DES": "I-CONTENT",
    "B-DESCRIPTION": "B-CONTENT",
    "I-DESCRIPTION": "I-CONTENT",
    "B-PARTICIPANT": "B-PERSON",
    "I-PARTICIPANT": "I-PERSON",
    "B-FREQUENCY": "B-DATE",
    "I-FREQUENCY": "I-DATE",
    "B-PRIORITY": "B-STATUS",
    "I-PRIORITY": "I-STATUS",
    "B-TITLET": "B-TITLE",
    "I-TITLET": "I-TITLE",
}


def normalize_ner_tag(tag: str) -> str:
    tag = str(tag).strip().upper()
    return NER_TAG_ALIASES.get(tag, tag)


def audit(path: Path) -> int:
    records = json.loads(path.read_text(encoding="utf-8"))
    actions = set(ACTION_LABELS)
    objects = set(OBJECT_LABELS)
    ner_tags = set(NER_TAGS)

    split_counts = Counter()
    action_counts = Counter()
    object_counts = Counter()
    combo_counts = Counter()
    invalid_actions = Counter()
    invalid_objects = Counter()
    invalid_ner_tags = Counter()
    mismatched_ner = 0
    missing_split = 0
    missing_ner = 0

    for record in records:
        split = str(record.get("split") or "").strip()
        action = str(record.get("action") or "").strip().upper()
        obj = str(record.get("object") or "").strip().upper()
        tokens = record.get("tokens") or []
        tags = record.get("ner_tags") or []

        if not split:
            missing_split += 1
        split_counts[split or "<missing>"] += 1

        if action not in actions:
            invalid_actions[action or "<missing>"] += 1
        else:
            action_counts[action] += 1

        if obj not in objects:
            invalid_objects[obj or "<missing>"] += 1
        else:
            object_counts[obj] += 1

        if action in actions and obj in objects:
            combo_counts[(action, obj)] += 1

        if not tags:
            missing_ner += 1
            continue

        if len(tokens) != len(tags):
            mismatched_ner += 1

        for tag in tags:
            normalized = normalize_ner_tag(tag)
            if normalized not in ner_tags:
                invalid_ner_tags[tag] += 1

    print(f"file: {path}")
    print(f"records: {len(records)}")
    print(f"missing_split: {missing_split}")
    print(f"missing_ner: {missing_ner}")
    print(f"token_tag_mismatch: {mismatched_ner}")
    print_counts("splits", split_counts)
    print_counts("actions", action_counts)
    print_counts("objects", object_counts)
    print_counts("action_object", combo_counts)
    print_counts("invalid_actions", invalid_actions)
    print_counts("invalid_objects", invalid_objects)
    print_counts("invalid_ner_tags", invalid_ner_tags)

    return int(
        missing_split > 0
        or mismatched_ner > 0
        or bool(invalid_actions)
        or bool(invalid_objects)
        or bool(invalid_ner_tags)
    )


def print_counts(title: str, counts: Counter):
    print(title + ":")
    if not counts:
        print("  ok")
        return

    for key, count in sorted(counts.items(), key=lambda item: str(item[0])):
        if isinstance(key, tuple):
            key = "/".join(key)
        print(f"  {key}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Audit Squire NLU JSON data.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    raise SystemExit(audit(args.path))


if __name__ == "__main__":
    main()