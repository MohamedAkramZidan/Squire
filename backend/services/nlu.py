import numpy as np
from onnxruntime import InferenceSession
from transformers import AutoTokenizer

from config.labels import (
    IDX_TO_ACTION,
    IDX_TO_OBJECT,
    IDX_TO_TAG,
)

from config.settings import settings

ENCODER_MODEL = settings.encoder_model
MAX_LENGTH = settings.max_length
MODEL_PATH = settings.model_path

_tokenizer = None
_session = None

def load(model_path: str):
    global _tokenizer, _session

    _tokenizer = AutoTokenizer.from_pretrained(
        ENCODER_MODEL,
        use_fast=False
    )

    _session = InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )

def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


def _softmax2d(x):
    e = np.exp(x - x.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)

def _store_entity(entities, tag, tokens, confidence=None):
    value = " ".join(tokens)

    entities.append({
        "type": tag,
        "value": value,
        "confidence": confidence
    })

def decode_entities_with_confidence(text, tags, word_ids, tag_probs=None):

    words = text.split()

    entities = []

    cur_tag = None
    cur_tokens = []
    cur_conf = []

    prev_wid = None

    for i, wid in enumerate(word_ids):

        if i >= len(tags):
            break

        if wid is None:
            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens, float(np.mean(cur_conf)) if cur_conf else None)

            cur_tag = None
            cur_tokens = []
            cur_conf = []
            continue

        if wid == prev_wid:
            continue

        tag = IDX_TO_TAG.get(tags[i], "O")
        word = words[wid] if wid < len(words) else ""

        if tag.startswith("B-"):

            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens, float(np.mean(cur_conf)) if cur_conf else None)

            cur_tag = tag[2:]
            cur_tokens = [word]
            cur_conf = []

            if tag_probs is not None:
                cur_conf.append(float(tag_probs[i, tags[i]]))

        elif tag.startswith("I-") and cur_tag:

            cur_tokens.append(word)

            if tag_probs is not None:
                cur_conf.append(float(tag_probs[i, tags[i]]))

        else:

            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens, float(np.mean(cur_conf)) if cur_conf else None)

            cur_tag = None
            cur_tokens = []
            cur_conf = []

        prev_wid = wid

    if cur_tag and cur_tokens:
        _store_entity(entities, cur_tag, cur_tokens, float(np.mean(cur_conf)) if cur_conf else None)

    return entities

def predict(text: str):

    enc = _tokenizer(
        text,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        add_special_tokens=False
    )

    action_logits, object_logits, ner_emissions = _session.run(
        None,
        {
            "input_ids": np.array([enc["input_ids"]], dtype=np.int64),
            "attention_mask": np.array([enc["attention_mask"]], dtype=np.int64),
        },
    )

    action_probs = _softmax(action_logits[0])
    object_probs = _softmax(object_logits[0])
    ner_probs = _softmax2d(ner_emissions[0])

    tags = ner_emissions[0].argmax(axis=-1).tolist()

    action_idx = int(action_probs.argmax())
    object_idx = int(object_probs.argmax())

    entities = decode_entities_with_confidence(
        text=text,
        tags=tags,
        word_ids=enc.word_ids(),
        tag_probs=ner_probs,
    )

    return {
        "action": IDX_TO_ACTION[action_idx],
        "object": IDX_TO_OBJECT[object_idx],
        "action_conf": float(action_probs[action_idx]),
        "object_conf": float(object_probs[object_idx]),
        "entities": entities,
        "action_probs": action_probs.tolist(),
        "object_probs": object_probs.tolist(),
    }