import torch
import numpy as np
from collections import defaultdict
from sklearn.preprocessing import normalize

from config.labels import (
    IDX_TO_ACTION, IDX_TO_OBJECT, IDX_TO_TAG,
    NUM_ACTIONS, NUM_OBJECTS,
)

class IntentEvaluator:
    def evaluate(self, model, loader, device) -> dict:
        model.eval()
        action_preds = []
        action_true = []
        object_preds = []
        object_true = []
        action_confs = []

        with torch.no_grad():
            for batch in loader:
                ids = batch["input_ids"].to(device)
                mask = batch["attention_mask"].to(device)
                a_true = batch["action_label"]
                o_true = batch["object_label"]

                out = model(ids, mask)

                a_prob = torch.softmax(out["action_logits"], dim=-1)
                o_prob = torch.softmax(out["object_logits"], dim=-1)

                a_pred = a_prob.argmax(dim=-1).cpu()
                o_pred = o_prob.argmax(dim=-1).cpu()
                a_conf = a_prob.max(dim=-1).values.cpu()

                action_preds.extend(a_pred.tolist())
                action_true.extend(a_true.tolist())
                object_preds.extend(o_pred.tolist())
                object_true.extend(o_true.tolist())
                action_confs.extend(a_conf.tolist())

        model.train()

        action_acc = self._accuracy(action_preds, action_true)
        object_acc = self._accuracy(object_preds, object_true)
        action_f1 = self._per_class_f1(
            action_preds, action_true, IDX_TO_ACTION, NUM_ACTIONS
        )
        object_f1 = self._per_class_f1(
            object_preds, object_true, IDX_TO_OBJECT, NUM_OBJECTS
        )
        ece = self._ece(action_preds, action_true, action_confs)
        macro_action = np.mean([v["f1"] for v in action_f1.values()])
        macro_object = np.mean([v["f1"] for v in object_f1.values()])

        return {
            "action_acc": action_acc,
            "object_acc": object_acc,
            "action_f1": action_f1,
            "object_f1": object_f1,
            "macro_action": macro_action,
            "macro_object": macro_object,
            "ece": ece,
        }

    def _accuracy(self, preds, labels) -> float:
        return sum(p == l for p, l in zip(preds, labels)) / max(len(labels), 1)

    def _per_class_f1(self, preds, labels, idx_to_name, n_classes) -> dict:
        tp = defaultdict(int)
        fp = defaultdict(int)
        fn = defaultdict(int)

        for p, l in zip(preds, labels):
            if p == l:
                tp[l] += 1
            else:
                fp[p] += 1
                fn[l] += 1

        results = {}
        for idx in range(n_classes):
            name = idx_to_name[idx]
            t = tp[idx]
            f_p = fp[idx]
            f_n = fn[idx]
            prec = t / (t + f_p) if (t + f_p) > 0 else 0.0
            rec = t / (t + f_n) if (t + f_n) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
            results[name] = {
                "precision": round(prec, 3),
                "recall": round(rec, 3),
                "f1": round(f1, 3),
                "support": t + f_n,
            }
        return results

    def _ece(self, preds, labels, confs, n_bins=10) -> float:
        bins = np.linspace(0, 1, n_bins + 1)
        ece = 0.0
        n = len(preds)

        for i in range(n_bins):
            lo, hi = bins[i], bins[i + 1]
            mask = [lo <= c < hi for c in confs]
            if not any(mask):
                continue
            b_conf = [c for c, m in zip(confs, mask) if m]
            b_pred = [p for p, m in zip(preds, mask) if m]
            b_true = [l for l, m in zip(labels, mask) if m]
            acc = sum(p == l for p, l in zip(b_pred, b_true)) / len(b_pred)
            ece += (len(b_pred) / n) * abs(acc - np.mean(b_conf))

        return round(ece, 4)


class NEREvaluator:
    def evaluate(self, model, loader, device) -> dict:
        model.eval()
        all_gold = []
        all_pred = []

        with torch.no_grad():
            for batch in loader:
                ids = batch["input_ids"].to(device)
                mask = batch["attention_mask"].to(device)
                labels = batch["ner_labels"]

                out = model(ids, mask)
                tags = out["tags"]

                for i in range(len(tags)):
                    seq_len = int(mask[i].sum())
                    gold_seq = labels[i].tolist()[:seq_len]
                    pred_seq = tags[i][:seq_len]
                    pred_seq = [
                        p if g != -100 else -100
                        for p, g in zip(pred_seq, gold_seq)
                    ]

                    all_gold.append(self._extract_spans(gold_seq))
                    all_pred.append(self._extract_spans(pred_seq))

        model.train()
        return self._compute_f1(all_gold, all_pred)

    def _extract_spans(self, tag_ids: list) -> list:
        spans = []
        cur_type = None
        cur_start = None

        for i, tid in enumerate(tag_ids):
            if tid == -100:
                if cur_type:
                    spans.append((cur_start, i - 1, cur_type))
                    cur_type, cur_start = None, None
                continue

            tag = IDX_TO_TAG.get(tid, "O")

            if tag.startswith("B-"):
                if cur_type:
                    spans.append((cur_start, i - 1, cur_type))
                cur_type = tag[2:]
                cur_start = i

            elif tag.startswith("I-"):
                if cur_type is None:
                    cur_type = tag[2:]
                    cur_start = i

            else:  # O
                if cur_type:
                    spans.append((cur_start, i - 1, cur_type))
                    cur_type, cur_start = None, None

        if cur_type:
            spans.append((cur_start, len(tag_ids) - 1, cur_type))

        return spans

    def _compute_f1(self, all_gold: list, all_pred: list) -> dict:
        tp_per = defaultdict(int)
        fp_per = defaultdict(int)
        fn_per = defaultdict(int)
        all_tp = all_fp = all_fn = 0

        for gold, pred in zip(all_gold, all_pred):
            gold_set = set(gold)
            pred_set = set(pred)

            for span in pred_set:
                if span in gold_set:
                    tp_per[span[2]] += 1
                else:
                    fp_per[span[2]] += 1

            for span in gold_set:
                if span not in pred_set:
                    fn_per[span[2]] += 1

        types = set(list(tp_per) + list(fp_per) + list(fn_per))
        per_type = {}

        for etype in sorted(types):
            tp = tp_per[etype]
            fp = fp_per[etype]
            fn = fn_per[etype]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
            per_type[etype] = {
                "precision": round(p, 3),
                "recall": round(r, 3),
                "f1": round(f1, 3),
                "tp": tp,
                "fp": fp,
                "fn": fn,
            }
            all_tp += tp
            all_fp += fp
            all_fn += fn

        micro_p = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0
        micro_r = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0
        micro_f1 = (
            2 * micro_p * micro_r / (micro_p + micro_r)
            if (micro_p + micro_r) > 0
            else 0.0
        )

        return {
            "micro_f1": round(micro_f1, 3),
            "micro_p": round(micro_p, 3),
            "micro_r": round(micro_r, 3),
            "per_type": per_type,
        }


class EmbeddingEvaluator:
    def evaluate(self, model, loader, device, n_batches: int = 10) -> dict:
        model.eval()
        raw_embs = []
        proj_embs = []
        action_labels = []
        object_labels = []
        joint_labels = []

        with torch.no_grad():
            for i, batch in enumerate(loader):
                if i >= n_batches:
                    break
                ids = batch["input_ids"].to(device)
                mask = batch["attention_mask"].to(device)
                a_lbls = batch["action_label"]
                o_lbls = batch["object_label"]

                out = model(ids, mask)
                cls = out["cls_vector"]
                proj = model.proj_head(cls)

                raw_embs.append(cls.cpu().numpy())
                proj_embs.append(proj.cpu().numpy())
                action_labels.extend(a_lbls.tolist())
                object_labels.extend(o_lbls.tolist())
                joint_labels.extend((a_lbls * NUM_OBJECTS + o_lbls).tolist())

        model.train()
        if not raw_embs:
            return {}

        raw = np.vstack(raw_embs)
        proj = np.vstack(proj_embs)
        action = np.array(action_labels)
        obj = np.array(object_labels)
        joint = np.array(joint_labels)

        action_raw = self._quality(raw, action)
        object_raw = self._quality(raw, obj)
        joint_proj = self._quality(proj, joint)

        return {
            "separation_ratio": joint_proj["ratio"],
            "joint_projected_intra": joint_proj["intra"],
            "joint_projected_inter": joint_proj["inter"],
            "joint_projected_sep": joint_proj["ratio"],
            "action_raw_sep": action_raw["ratio"],
            "object_raw_sep": object_raw["ratio"],
        }

    def _quality(self, embs, labels) -> dict:
        intra = self._intra_sim(embs, labels)
        inter = self._inter_sim(embs, labels)
        ratio = intra / inter if inter > 0 else 0.0

        return {
            "intra": round(intra, 3),
            "inter": round(inter, 3),
            "ratio": round(ratio, 3),
        }

    def _intra_sim(self, embs, labels) -> float:
        embs_n = normalize(embs)
        sims = []
        for cls in np.unique(labels):
            mask = labels == cls
            if mask.sum() < 2:
                continue
            e = embs_n[mask]
            sim = np.dot(e, e.T)
            np.fill_diagonal(sim, 0)
            n = mask.sum()
            sims.append(sim.sum() / (n * (n - 1)))
        return float(np.mean(sims)) if sims else 0.0

    def _inter_sim(self, embs, labels) -> float:
        embs_n = normalize(embs)
        classes = np.unique(labels)
        sims = []
        for i in range(len(classes)):
            for j in range(i + 1, len(classes)):
                ei = embs_n[labels == classes[i]]
                ej = embs_n[labels == classes[j]]
                sims.append(np.dot(ei, ej.T).mean())
        return float(np.mean(sims)) if sims else 1.0


class TrainingTracker:
    def __init__(self):
        self.history = []
        self.best_epoch = 0
        self.best_score = 0.0

    def record(
        self,
        epoch: int,
        phase: int,
        train_losses: dict,
        val_intent: dict,
        val_ner: dict,
        val_emb: dict = None,
    ) -> float:
        self.history.append({
            "epoch": epoch,
            "phase": phase,
            "train": train_losses,
            "val_intent": val_intent,
            "val_ner": val_ner,
            "val_emb": val_emb or {},
        })

        score = (
            0.33 * val_intent.get("action_acc", 0)
            + 0.33 * val_intent.get("object_acc", 0)
            + 0.34 * val_ner.get("micro_f1", 0)
        )

        if score > self.best_score:
            self.best_score = score
            self.best_epoch = epoch

        return score

    def print_epoch(
        self,
        epoch: int,
        phase: int,
        train_losses: dict,
        val_intent: dict,
        val_ner: dict,
        val_emb: dict = None,
    ):
        best_mark = "  * BEST" if epoch == self.best_epoch else ""
        sep = "-" * 70
        print(f"\n{sep}")
        print(f"Epoch {epoch:3d}  Phase {phase}{best_mark}")
        print(sep)

        tl = train_losses
        print(
            f"  Train:   total={tl.get('total', 0):.4f}  "
            f"action={tl.get('action', 0):.4f}  "
            f"object={tl.get('object', 0):.4f}  "
            f"ner={tl.get('ner', 0):.4f}  "
            f"con={tl.get('con', 0):.4f}"
        )

        vi = val_intent
        print(
            f"  Action:  acc={vi.get('action_acc', 0):.3f}  "
            f"macro_f1={vi.get('macro_action', 0):.3f}  "
            f"ECE={vi.get('ece', 0):.3f}"
        )

        print(
            f"  Object:  acc={vi.get('object_acc', 0):.3f}  "
            f"macro_f1={vi.get('macro_object', 0):.3f}"
        )

        vn = val_ner
        print(
            f"  NER:     micro_f1={vn.get('micro_f1', 0):.3f}  "
            f"p={vn.get('micro_p', 0):.3f}  "
            f"r={vn.get('micro_r', 0):.3f}"
        )

        per_type = vn.get("per_type", {})
        if per_type:
            low = [(t, v["f1"]) for t, v in per_type.items() if v["f1"] < 0.70]
            if low:
                low.sort(key=lambda x: x[1])
                low_str = "  ".join(f"{t}={f:.2f}" for t, f in low[:5])
                print(f"  ! Low entity F1: {low_str}")

        if val_emb:
            ratio = val_emb.get("separation_ratio", 0)
            quality = "strong" if ratio > 2.0 else "good" if ratio > 1.5 else "weak"
            print(
                f"  Contrastive: joint_proj={ratio:.2f} ({quality})  "
                f"raw_action={val_emb.get('action_raw_sep', 0):.2f}  "
                f"raw_object={val_emb.get('object_raw_sep', 0):.2f}"
            )

        print(sep)