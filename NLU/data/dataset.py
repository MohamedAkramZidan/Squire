import json
import torch
import numpy as np
from torch.utils.data import Dataset, Sampler
from transformers import AutoTokenizer
from collections import defaultdict

from config.labels import (
    ENCODER_MODEL,
    ACTION_LABELS, OBJECT_LABELS,
    NER_TAGS, MAX_LENGTH,
)

tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL)

class NLUDataset(Dataset):
    def __init__(self, data_path: str, split: str = "train"):
        with open(data_path, encoding="utf-8") as f:
            all_records = json.load(f)

        self.samples = []
        skipped = 0

        for record in all_records:
            if record.get("split") != split:
                continue

            action = record.get("action")
            obj = record.get("object")
            if action is None or obj is None:
                skipped += 1
                continue

            action = str(action).strip().upper()
            obj = str(obj).strip().upper()
            if action not in ACTION_LABELS or obj not in OBJECT_LABELS:
                skipped += 1
                continue

            sample = dict(record)
            sample["action"] = action
            sample["object"] = obj
            sample["ner_tags"] = sample.get("ner_tags", [])
            self.samples.append(sample)

        msg = f"[Dataset] {split}: {len(self.samples)} samples loaded"
        if skipped:
            msg += f" ({skipped} skipped invalid labels)"
        print(msg)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> dict:
        sample = self.samples[idx]
        text   = sample["text"]

        encoding = tokenizer(
            sample["tokens"],
            is_split_into_words=True,
            max_length=MAX_LENGTH,
            padding="max_length",
            truncation=True,
        )

        input_ids      = encoding["input_ids"]
        attention_mask = encoding["attention_mask"]
        word_ids       = encoding.word_ids()

        action_str   = sample["action"]
        action_label = ACTION_LABELS[action_str]

        object_str   = sample["object"]
        object_label = OBJECT_LABELS[object_str]

        ner_tags_raw = sample.get("ner_tags")
        has_ner      = (
            ner_tags_raw is not None
            and len(ner_tags_raw) > 0
            and len(ner_tags_raw) == len(sample.get("tokens", []))
        )
        ner_labels = self._align_ner(ner_tags_raw if has_ner else None,
                                     word_ids)

        return {
            "input_ids":      torch.tensor(input_ids,      dtype=torch.long),
            "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
            "action_label":   torch.tensor(action_label,  dtype=torch.long),
            "object_label":   torch.tensor(object_label,  dtype=torch.long),
            "ner_labels":     torch.tensor(ner_labels,    dtype=torch.long),
            "has_ner":        has_ner,
            "text":           text,
            "action_str":     action_str,
            "object_str":     object_str,
        }

    def _align_ner(self, raw_tags, word_ids):
        aligned = []
        prev_word = None

        for word_id in word_ids:
            if word_id is None:
                aligned.append(-100)

            elif raw_tags is None:
                aligned.append(-100)

            elif word_id != prev_word:
                tag = raw_tags[word_id]
                aligned.append(NER_TAGS.get(tag, NER_TAGS["O"]))
            else:
                aligned.append(-100)

            prev_word = word_id

        return aligned[:MAX_LENGTH] + [-100] * max(0, MAX_LENGTH - len(aligned))

    def get_action_indices(self) -> dict:
        mapping = defaultdict(list)
        for i, s in enumerate(self.samples):
            a = ACTION_LABELS[s["action"]]
            mapping[a].append(i)
        return mapping

    def get_object_indices(self) -> dict:
        mapping = defaultdict(list)
        for i, s in enumerate(self.samples):
            o = OBJECT_LABELS[s["object"]]
            mapping[o].append(i)
        return mapping

    def get_combo_indices(self) -> dict:
        mapping = defaultdict(list)
        n_objects = len(OBJECT_LABELS)
        for i, s in enumerate(self.samples):
            a = ACTION_LABELS[s["action"]]
            o = OBJECT_LABELS[s["object"]]
            mapping[a * n_objects + o].append(i)
        return mapping

class BalancedBatchSampler(Sampler):
    def __init__(self, dataset: NLUDataset,
                 batch_size: int = 32,
                 min_per_class: int = 2,
                 min_per_object: int = 8,
                 min_per_combo: int = 2):
        self.dataset        = dataset
        self.batch_size     = batch_size
        self.min_per_action = min_per_class
        self.min_per_object = min_per_object
        self.min_per_combo  = min_per_combo
        self.action_indices = dataset.get_action_indices()
        self.object_indices = dataset.get_object_indices()
        self.combo_indices  = dataset.get_combo_indices()
        self.n_action       = len(self.action_indices)
        self.n_object       = len(self.object_indices)
        self.n_combo        = len(self.combo_indices)
        self.n_samples      = len(dataset)

        guaranteed = (
            self.n_action * min_per_class
            + self.n_object * min_per_object
            + self.n_combo * min_per_combo
        )
        assert guaranteed <= batch_size, (
            f"batch_size={batch_size} too small for "
            f"{self.n_action} action x {min_per_class} "
            f"+ {self.n_object} object x {min_per_object} "
            f"+ {self.n_combo} combo x {min_per_combo} "
            f"= {guaranteed} guaranteed slots"
        )

    def __iter__(self):
        rng      = np.random.default_rng()
        n_batches = self.n_samples // self.batch_size
        all_idxs  = list(range(self.n_samples))

        for _ in range(n_batches):
            batch = set()

            for indices in self.object_indices.values():
                chosen = rng.choice(
                    indices,
                    size    = self.min_per_object,
                    replace = len(indices) < self.min_per_object,
                ).tolist()
                batch.update(chosen)

            for indices in self.combo_indices.values():
                chosen = rng.choice(
                    indices,
                    size    = self.min_per_combo,
                    replace = len(indices) < self.min_per_combo,
                ).tolist()
                batch.update(chosen)

            for indices in self.object_indices.values():
                chosen = rng.choice(
                    indices,
                    size    = self.min_per_object,
                    replace = len(indices) < self.min_per_object,
                ).tolist()
                batch.update(chosen)

            batch = list(batch)
            remaining = self.batch_size - len(batch)
            if remaining > 0:
                extra = rng.choice(
                    all_idxs,
                    size    = remaining,
                    replace = False,
                ).tolist()
                batch.extend(extra)

            batch = list(batch)[:self.batch_size]
            rng.shuffle(batch)
            yield batch

    def __len__(self) -> int:
        return self.n_samples // self.batch_size


def collate_fn(batch: list) -> dict:
    return {
        "input_ids":      torch.stack([b["input_ids"]      for b in batch]),
        "attention_mask": torch.stack([b["attention_mask"] for b in batch]),
        "action_label":   torch.stack([b["action_label"]   for b in batch]),
        "object_label":   torch.stack([b["object_label"]   for b in batch]),
        "ner_labels":     torch.stack([b["ner_labels"]     for b in batch]),
        "has_ner":        [b["has_ner"]     for b in batch],
        "texts":          [b["text"]        for b in batch],
        "action_strs":    [b["action_str"]  for b in batch],
        "object_strs":    [b["object_str"]  for b in batch],
    }