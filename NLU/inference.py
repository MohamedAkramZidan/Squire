import argparse
import json
import os
import sys
import time

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer

from config.labels import (                      
    ENCODER_MODEL,
    IDX_TO_ACTION,
    IDX_TO_OBJECT,
    IDX_TO_TAG,
    CONFIDENCE_THRESHOLD,
    MARGIN_THRESHOLD,
)

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
SQUIRE_ROOT = os.path.join(SCRIPT_DIR)          
if SQUIRE_ROOT not in sys.path:
    sys.path.insert(0, SQUIRE_ROOT)

def _store_entity(entities: dict, tag: str, tokens: list):
    value = " ".join(tokens)
    if tag in entities:
        if isinstance(entities[tag], list):
            entities[tag].append(value)
        else:
            entities[tag] = [entities[tag], value]
    else:
        entities[tag] = value


def _store_confidence(confidences: dict, tag: str, value: float):
    if tag in confidences:
        if isinstance(confidences[tag], list):
            confidences[tag].append(value)
        else:
            confidences[tag] = [confidences[tag], value]
    else:
        confidences[tag] = value


def decode_entities_with_confidence(
    text: str,
    tags: list,
    word_ids: list,
    tag_probs: np.ndarray = None, 
) -> tuple[dict, dict]:
    words       = text.split()
    entities    = {}
    confidences = {}
    cur_tag     = None
    cur_tokens  = []
    cur_conf    = []
    prev_wid    = None

    for i, wid in enumerate(word_ids):
        if i >= len(tags):
            break

        if wid is None:
            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens)
                if cur_conf:
                    _store_confidence(confidences, cur_tag,
                                      float(np.mean(cur_conf)))
                cur_tag, cur_tokens, cur_conf = None, [], []
            continue

        if wid == prev_wid:
            prev_wid = wid
            continue

        tag  = IDX_TO_TAG.get(tags[i], "O")
        word = words[wid] if wid < len(words) else ""

        if tag.startswith("B-"):
            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens)
                if cur_conf:
                    _store_confidence(confidences, cur_tag,
                                      float(np.mean(cur_conf)))
            cur_tag    = tag[2:]
            cur_tokens = [word]
            cur_conf   = []
            if tag_probs is not None:
                cur_conf.append(float(tag_probs[i, tags[i]]))

        elif tag.startswith("I-") and cur_tag:
            cur_tokens.append(word)
            if tag_probs is not None:
                cur_conf.append(float(tag_probs[i, tags[i]]))

        else:
            if cur_tag and cur_tokens:
                _store_entity(entities, cur_tag, cur_tokens)
                if cur_conf:
                    _store_confidence(confidences, cur_tag,
                                      float(np.mean(cur_conf)))
            cur_tag, cur_tokens, cur_conf = None, [], []

        prev_wid = wid

    if cur_tag and cur_tokens:
        _store_entity(entities, cur_tag, cur_tokens)
        if cur_conf:
            _store_confidence(confidences, cur_tag, float(np.mean(cur_conf)))

    return entities, confidences

class ONNXInferenceEngine:
    def __init__(
        self,
        model_path: str,
        intra_threads: int = 4,
        inter_threads: int = 1,
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL)

        opts = ort.SessionOptions()
        opts.intra_op_num_threads       = intra_threads
        opts.inter_op_num_threads       = inter_threads
        opts.graph_optimization_level   = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.execution_mode             = ort.ExecutionMode.ORT_SEQUENTIAL

        self.sess = ort.InferenceSession(
            model_path,
            opts,
            providers=["CPUExecutionProvider"],
        )

        _dummy_ids  = np.zeros((1, 64), dtype=np.int64)
        _dummy_mask = np.ones((1, 64),  dtype=np.int64)
        for _ in range(3):
            self.sess.run(None, {
                "input_ids":      _dummy_ids,
                "attention_mask": _dummy_mask,
            })

        print(f"[infre_onnx] loaded {model_path}", file=sys.stderr)

    def _encode(self, text: str) -> dict:
        enc = self.tokenizer(
            text,
            max_length     = 64,
            padding        = "max_length",
            truncation     = True,
            return_tensors = "np",
        )
        return {
            "input_ids":      enc["input_ids"].astype(np.int64),
            "attention_mask": enc["attention_mask"].astype(np.int64),
            "word_ids":       self.tokenizer(
                                   text,
                                   max_length=64,
                                   padding="max_length",
                                   truncation=True,
                               ).word_ids(),
        }

    def _run(self, enc: dict) -> tuple:
        return self.sess.run(
            None,
            {
                "input_ids":      enc["input_ids"],
                "attention_mask": enc["attention_mask"],
            },
        )
    
    def predict(self, text: str) -> dict:
        enc = self._encode(text)
        action_logits, object_logits, ner_emissions = self._run(enc)

        def softmax(x):
            e = np.exp(x - x.max())
            return e / e.sum()

        action_probs = softmax(action_logits[0])   
        object_probs = softmax(object_logits[0])   
        ner_probs    = np.exp(ner_emissions[0] -   
                              ner_emissions[0].max(axis=-1, keepdims=True))
        ner_probs   /= ner_probs.sum(axis=-1, keepdims=True)
        tags         = ner_emissions[0].argmax(axis=-1).tolist()

        action_idx   = int(action_probs.argmax())
        object_idx   = int(object_probs.argmax())

        entities, entity_conf = decode_entities_with_confidence(
            text, tags, enc["word_ids"], ner_probs
        )

        return {
            "action":        IDX_TO_ACTION[action_idx],
            "object":        IDX_TO_OBJECT[object_idx],
            "action_conf":   float(action_probs[action_idx]),
            "object_conf":   float(object_probs[object_idx]),
            "action_second": IDX_TO_ACTION[int(np.argsort(action_probs)[::-1][1])],
            "object_second": IDX_TO_OBJECT[int(np.argsort(object_probs)[::-1][1])],
            "variance":      0.0,
            "entities":      entities,
            "entity_conf":   entity_conf,
            "action_probs":  action_probs.tolist(),
            "object_probs":  object_probs.tolist(),
        }

    def is_confident(self, result: dict) -> bool:
        a_conf   = result["action_conf"]
        o_conf   = result["object_conf"]
        a_second = result["action_probs"][
            [i for i in range(len(result["action_probs"]))
             if IDX_TO_ACTION[i] == result["action_second"]][0]
        ]
        margin = a_conf - a_second
        return (
            a_conf >= CONFIDENCE_THRESHOLD
            and o_conf >= CONFIDENCE_THRESHOLD
            and margin >= MARGIN_THRESHOLD
        )

def main():
    parser = argparse.ArgumentParser(
        description="Squire ONNX inference engine"
    )
    parser.add_argument("--model",      required=True,
                        help="Path to squire_int8.onnx (or fp32)")
    parser.add_argument("--text",       action="append",
                        help="Text to predict. Repeat for multiple inputs.")
    parser.add_argument("--json",       action="store_true",
                        help="Output raw JSON (default: pretty summary)")
    args = parser.parse_args()

    engine = ONNXInferenceEngine(args.model, intra_threads=args.threads)

    texts = args.text or []
    if not texts:
        print("Enter text. Empty line exits.", file=sys.stderr)
        while True:
            try:
                text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                break
            texts.append(text)

    for text in texts:
        result = engine.predict(text)

        if args.json:
            print(json.dumps({"text": text, "prediction": result}, indent=2))
        else:
            # human-friendly summary
            confident = engine.is_confident(result)
            print(f"\n  text    : {text}")
            print(f"  intent  : {result['action']} × {result['object']}"
                  f"  ({result['action_conf']:.0%} / {result['object_conf']:.0%})"
                  f"  {'✓' if confident else '⚠ low confidence'}")
            if result["entities"]:
                print(f"  entities: {result['entities']}")
            if result["entity_conf"]:
                print(f"  ent_conf: {result['entity_conf']}")


if __name__ == "__main__":
    main()
