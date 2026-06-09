import argparse 
import os
import sys
import json
import torch
from collections import Counter
from torch.utils.data import DataLoader, WeightedRandomSampler
from transformers import get_linear_schedule_with_warmup

sys.path.insert(0, os.path.dirname(__file__))

from config.labels import (
    PHASE1_EPOCHS, PHASE2_EPOCHS, PHASE3_EPOCHS,
    BATCH_SIZE,
)
from data.dataset     import NLUDataset, BalancedBatchSampler, collate_fn
from nlp.model        import MDeBERTaNLU
from evaluation.metrics import (
    IntentEvaluator, NEREvaluator,
    EmbeddingEvaluator, TrainingTracker
)

def build_loader(dataset: NLUDataset,
                 batch_size: int,
                 balanced: bool = False) -> DataLoader:
    if balanced:
        n_action = max(len(dataset.get_action_indices()), 1)
        n_object = max(len(dataset.get_object_indices()), 1)
        n_combo = max(len(dataset.get_combo_indices()), 1)
        min_per_action = max(1, min(4, batch_size // n_action // 8))
        min_per_object = max(1, min(4, batch_size // n_object // 8))
        min_per_combo = max(1, min(4, batch_size // n_combo // 2))
        sampler = BalancedBatchSampler(
            dataset,
            batch_size     = batch_size,
            min_per_class  = min_per_action,
            min_per_object = min_per_object,
            min_per_combo  = min_per_combo,
        )
        return DataLoader(
            dataset,
            batch_sampler = sampler,
            collate_fn    = collate_fn,
            num_workers   = 0,
        )

    combo_counts = Counter(
        (sample["action"], sample["object"]) for sample in dataset.samples
    )
    weights = [
        1.0 / combo_counts[(sample["action"], sample["object"])]
        for sample in dataset.samples
    ]
    sampler = WeightedRandomSampler(
        weights,
        num_samples=len(weights),
        replacement=True,
    )
    return DataLoader(
        dataset,
        batch_size  = batch_size,
        sampler     = sampler,
        collate_fn  = collate_fn,
        num_workers = 0,
    )


def run_epoch(model, loader, optimizer,
              scheduler, device,
              phase: int) -> dict:
    model.train()
    use_con = (phase == 3)

    total_loss   = 0.0
    action_loss  = 0.0
    object_loss  = 0.0
    ner_loss     = 0.0
    con_loss     = 0.0
    n_batches    = 0

    for batch in loader:
        optimizer.zero_grad()

        ids    = batch["input_ids"].to(device)
        mask   = batch["attention_mask"].to(device)
        a_lbls = batch["action_label"].to(device)
        o_lbls = batch["object_label"].to(device)
        n_lbls = batch["ner_labels"].to(device)

        out    = model(
            input_ids       = ids,
            attention_mask  = mask,
            action_labels   = a_lbls,
            object_labels   = o_lbls,
            ner_labels      = n_lbls,
            use_contrastive = use_con,
        )

        loss = out["loss"]
        loss.backward()

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        optimizer.step()
        if scheduler:
            scheduler.step()

        total_loss  += loss.item()
        action_loss += out["action_loss"]
        object_loss += out["object_loss"]
        ner_loss    += out["ner_loss"]
        con_loss    += out["con_loss"]
        n_batches   += 1

    n = max(n_batches, 1)
    return {
        "total":  total_loss  / n,
        "action": action_loss / n,
        "object": object_loss / n,
        "ner":    ner_loss    / n,
        "con":    con_loss    / n,
    }

def train(args):
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    print(f"\n{'='*60}")
    print(f"  mDeBERTa-v3-base NLU Training")
    print(f"  Device:   {device}")
    print(f"  Data:     {args.data}")
    print(f"  Output:   {args.output}")
    print(f"{'='*60}\n")

    train_data = NLUDataset(args.data, split="train")
    val_data   = NLUDataset(args.data, split="val")

    val_loader = DataLoader(
        val_data,
        batch_size  = args.batch_size,
        shuffle     = False,
        collate_fn  = collate_fn,
        num_workers = 0,
    )

    model = MDeBERTaNLU().to(device)

    total_params    = sum(p.numel() for p in model.parameters())
    trainable_start = sum(
        p.numel() for p in model.parameters() if p.requires_grad
    )
    print(f"  Total params:     {total_params:,}")
    print(f"  Trainable params: {trainable_start:,}")
    print(f"  Frozen ratio:     "
          f"{(total_params - trainable_start) / total_params:.1%}\n")
    
    intent_eval = IntentEvaluator()
    ner_eval    = NEREvaluator()
    emb_eval    = EmbeddingEvaluator()
    tracker     = TrainingTracker()

    best_score    = 0.0
    global_epoch  = 0
    patience      = args.patience

    print(f"\n{'─'*60}")
    print(f"  PHASE 1 — Adapter warmup ({args.epochs_p1} epochs)")
    print(f"  Training: adapters + heads")
    print(f"  Contrastive: OFF")
    print(f"{'─'*60}")

    model.set_trainable_backbone_layers(0)
    p1_loader   = build_loader(train_data, args.batch_size, balanced=False)
    p1_optimizer= torch.optim.AdamW(
        model.get_param_groups(phase=1)
    )
    p1_scheduler= get_linear_schedule_with_warmup(
        p1_optimizer,
        num_warmup_steps  = len(p1_loader),
        num_training_steps= len(p1_loader) * args.epochs_p1,
    )

    for epoch in range(1, args.epochs_p1 + 1):
        global_epoch += 1
        losses = run_epoch(
            model, p1_loader, p1_optimizer,
            p1_scheduler, device, phase=1
        )

        val_intent = intent_eval.evaluate(model, val_loader, device)
        val_ner    = ner_eval.evaluate(model, val_loader, device)

        score = tracker.record(
            global_epoch, 1, losses, val_intent, val_ner
        )
        tracker.print_epoch(
            global_epoch, 1, losses, val_intent, val_ner
        )

    print(f"\n{'─'*60}")
    print(f"  PHASE 2 — Head training ({args.epochs_p2} epochs, patience={patience})")
    print(f"  Training: adapters + heads + top {args.unfreeze_layers_p2} encoder layers")
    print(f"  Contrastive: OFF")
    print(f"{'─'*60}")

    no_improve   = 0
    model.set_trainable_backbone_layers(args.unfreeze_layers_p2)
    p2_loader    = build_loader(train_data, args.batch_size, balanced=False)
    p2_optimizer = torch.optim.AdamW(
        model.get_param_groups(phase=2)
    )
    p2_scheduler = get_linear_schedule_with_warmup(
        p2_optimizer,
        num_warmup_steps  = len(p2_loader),
        num_training_steps= len(p2_loader) * args.epochs_p2,
    )

    for epoch in range(1, args.epochs_p2 + 1):
        global_epoch += 1
        losses = run_epoch(
            model, p2_loader, p2_optimizer,
            p2_scheduler, device, phase=2
        )

        val_intent = intent_eval.evaluate(model, val_loader, device)
        val_ner    = ner_eval.evaluate(model, val_loader, device)

        score = tracker.record(
            global_epoch, 2, losses, val_intent, val_ner
        )
        tracker.print_epoch(
            global_epoch, 2, losses, val_intent, val_ner
        )

        if score > best_score:
            best_score = score
            no_improve = 0
            torch.save(model.state_dict(), args.output)
            print(f"  ✓ Saved best model (score={best_score:.4f})")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  Early stopping phase 2: no improvement for {patience} epochs")
                break

    print(f"\n{'─'*60}")
    print(f"  PHASE 3 — Joint fine-tuning ({args.epochs_p3} epochs, patience={patience})")
    print(f"  Training: all heads + joint contrastive + top {args.unfreeze_layers_p3} encoder layers")
    print(f"  Contrastive: ON  (joint action/object positives)")
    print(f"{'─'*60}")

    if os.path.exists(args.output):
        model.load_state_dict(torch.load(args.output, map_location=device))
        print(f"  Loaded phase-2 best checkpoint")

    no_improve   = 0
    model.set_trainable_backbone_layers(args.unfreeze_layers_p3)
    p3_loader    = build_loader(train_data, args.batch_size, balanced=True)
    p3_optimizer = torch.optim.AdamW(
        model.get_param_groups(phase=3)
    )
    p3_scheduler = get_linear_schedule_with_warmup(
        p3_optimizer,
        num_warmup_steps  = len(p3_loader),
        num_training_steps= len(p3_loader) * args.epochs_p3,
    )

    for epoch in range(1, args.epochs_p3 + 1):
        global_epoch += 1
        losses = run_epoch(
            model, p3_loader, p3_optimizer,
            p3_scheduler, device, phase=3
        )

        val_intent = intent_eval.evaluate(model, val_loader, device)
        val_ner    = ner_eval.evaluate(model, val_loader, device)
        val_emb    = emb_eval.evaluate(model, val_loader, device)

        score = tracker.record(
            global_epoch, 3, losses, val_intent, val_ner, val_emb
        )
        tracker.print_epoch(
            global_epoch, 3, losses, val_intent, val_ner, val_emb
        )

        if score > best_score:
            best_score = score
            no_improve = 0
            torch.save(model.state_dict(), args.output)
            print(f"  ✓ Saved best model (score={best_score:.4f})")
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  Early stopping phase 3: no improvement for {patience} epochs")
                break

    print(f"\n{'='*60}")
    print(f"  Training complete")
    print(f"  Best epoch:  {tracker.best_epoch}")
    print(f"  Best score:  {tracker.best_score:.4f}")
    print(f"  Saved to:    {args.output}")
    print(f"{'='*60}\n")

    history_path = args.output.replace(".pt", "_history.json")
    with open(history_path, "w") as f:
        json.dump(tracker.history, f, indent=2)
    print(f"  History saved to {history_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train mDeBERTa-v3-base NLU model"
    )
    parser.add_argument(
        "--data",
        default="data/master.json",
        help="Path to master.json dataset"
    )
    parser.add_argument(
        "--output",
        default="model_best.pt",
        help="Output path for best model checkpoint"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=BATCH_SIZE,
        help="Batch size for training"
    )
    parser.add_argument(
        "--epochs_p1",
        type=int,
        default=PHASE1_EPOCHS,
        help="Phase 1 epochs (adapter warmup)"
    )
    parser.add_argument(
        "--epochs_p2",
        type=int,
        default=PHASE2_EPOCHS,
        help="Phase 2 epochs (head training)"
    )
    parser.add_argument(
        "--epochs_p3",
        type=int,
        default=PHASE3_EPOCHS,
        help="Phase 3 epochs (joint fine-tuning)"
    )
    parser.add_argument(
        "--unfreeze_layers_p2",
        type=int,
        default=2,
        help="Number of top encoder layers to fine-tune in phase 2"
    )
    parser.add_argument(
        "--unfreeze_layers_p3",
        type=int,
        default=0,
        help="Number of top encoder layers to fine-tune in phase 3"
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=5,
        help="Early stopping patience per phase"
    )
    args = parser.parse_args()
    train(args)