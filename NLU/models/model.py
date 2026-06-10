import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from transformers import AutoModel, AutoTokenizer

from config.labels import (
    ENCODER_MODEL,
    NUM_ACTIONS, NUM_OBJECTS, NUM_TAGS,
    IDX_TO_ACTION, IDX_TO_OBJECT, IDX_TO_TAG,
    ACTION_LABELS, OBJECT_LABELS,
    ADAPTER_SIZE, ADAPTER_DROPOUT,
    CONTRASTIVE_TEMP, CONTRASTIVE_WEIGHT, NER_WEIGHT,
    NER_CLASS_WEIGHTS, OBJECT_CLASS_WEIGHTS,
    MC_SAMPLES,
)

class AdapterLayer(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.norm    = nn.LayerNorm(hidden_size)
        self.down    = nn.Linear(hidden_size, ADAPTER_SIZE)
        self.up      = nn.Linear(ADAPTER_SIZE, hidden_size)
        self.act     = nn.GELU()
        self.dropout = nn.Dropout(ADAPTER_DROPOUT)

        nn.init.normal_(self.down.weight, std=1e-3)
        nn.init.zeros_(self.down.bias)
        nn.init.normal_(self.up.weight,   std=1e-3)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = self.norm(x)
        x = self.down(x)
        x = self.act(x)
        x = self.dropout(x)
        x = self.up(x)
        return x + residual


class SupConLoss(nn.Module):
    def __init__(self, temperature: float = CONTRASTIVE_TEMP):
        super().__init__()
        self.temp = temperature

    def forward(self, embeddings: torch.Tensor,
                labels: torch.Tensor) -> torch.Tensor:
        
        device = embeddings.device
        B      = embeddings.size(0)

        if B < 2:
            return torch.tensor(0.0, device=device)

        embeddings = F.normalize(embeddings, dim=1)

        sim = torch.matmul(embeddings, embeddings.T) / self.temp

        eye     = torch.eye(B, dtype=torch.bool, device=device)
        sim     = sim.masked_fill(eye, float("-inf"))

        L_row   = labels.unsqueeze(1)
        L_col   = labels.unsqueeze(0)
        pos_mask= (L_row == L_col) & ~eye

        has_pos = pos_mask.any(dim=1)
        if not has_pos.any():
            return torch.tensor(0.0, device=device)

        log_prob   = F.log_softmax(sim, dim=1)
        pos_log_prob = log_prob.masked_fill(~pos_mask, 0.0)
        pos_sum = pos_log_prob.sum(dim=1)
        pos_count  = pos_mask.float().sum(dim=1).clamp(min=1)
        loss       = -(pos_sum / pos_count)

        return loss[has_pos].mean()

class MDeBERTaNLU(nn.Module):
    def __init__(self):
        super().__init__()

        self.backbone   = AutoModel.from_pretrained(
            ENCODER_MODEL,
            torch_dtype=torch.float32,
            output_hidden_states=True,
        )
        H               = self.backbone.config.hidden_size
        n_layers        = self.backbone.config.num_hidden_layers

        for p in self.backbone.parameters():
            p.requires_grad = False

        self.adapters   = nn.ModuleList([
            AdapterLayer(H) for _ in range(n_layers)
        ])

        self.proj_head  = nn.Sequential(
            nn.Linear(H, 256),
            nn.GELU(),
            nn.Linear(256, 128),
        )

        self.proj_head_object = nn.Sequential(
            nn.Linear(H, 256),
            nn.GELU(),
            nn.Linear(256, 128),
        )
        for p in self.proj_head_object.parameters():
            p.requires_grad = False

        self.dropout     = nn.Dropout(0.1)
        self.action_head = nn.Linear(H, NUM_ACTIONS)
        self.object_head = nn.Linear(H, NUM_OBJECTS)

        self.ner_linear  = nn.Linear(H, NUM_TAGS)

        ner_w = torch.tensor(NER_CLASS_WEIGHTS, dtype=torch.float32)
        self.register_buffer("ner_loss_weight", ner_w)

        obj_w = torch.tensor(OBJECT_CLASS_WEIGHTS, dtype=torch.float32)
        self.register_buffer("object_loss_weight", obj_w)

        self.log_var_cls = nn.Parameter(torch.zeros(1))
        self.log_var_ner = nn.Parameter(torch.zeros(1))

        self.supcon      = SupConLoss()

    def encode(self, input_ids: torch.Tensor,
               attention_mask: torch.Tensor):
        out    = self.backbone(
            input_ids            = input_ids,
            attention_mask       = attention_mask,
            output_hidden_states = True,
        )
        hidden = out.hidden_states  

        adapted = hidden[0]
        for i, adapter in enumerate(self.adapters):
            adapted = adapter(hidden[i + 1] + adapted)

        cls_vector = adapted[:, 0, :]
        return adapted, cls_vector

    def forward(self,
                input_ids:     torch.Tensor,
                attention_mask:torch.Tensor,
                action_labels: torch.Tensor = None,
                object_labels: torch.Tensor = None,
                ner_labels:    torch.Tensor = None,
                use_contrastive: bool = False):

        all_vectors, cls_vector = self.encode(input_ids, attention_mask)

        action_logits = self.action_head(self.dropout(cls_vector))
        object_logits = self.object_head(self.dropout(cls_vector))

        ner_emissions = self.ner_linear(self.dropout(all_vectors))

        if action_labels is None:
            return {
                "action_logits": action_logits,
                "object_logits": object_logits,
                "ner_emissions": ner_emissions,
                "cls_vector":    cls_vector,
                "tags":          ner_emissions.argmax(dim=-1).detach().cpu().tolist(),
            }
        
        ce          = nn.CrossEntropyLoss()
        action_loss = ce(action_logits, action_labels)
        object_loss = nn.CrossEntropyLoss(
            weight=self.object_loss_weight
        )(object_logits, object_labels)
        cls_loss    = action_loss + object_loss

        if ner_labels is not None and torch.any(ner_labels != -100):
            ner_loss = F.cross_entropy(
                ner_emissions.reshape(-1, NUM_TAGS),
                ner_labels.reshape(-1),
                weight       = self.ner_loss_weight,
                ignore_index = -100,
            )
        else:
            ner_loss = torch.tensor(0.0, device=cls_vector.device)

        if use_contrastive:
            joint_labels = action_labels * NUM_OBJECTS + object_labels
            proj_joint = self.proj_head(cls_vector)
            con_loss = self.supcon(proj_joint, joint_labels)
        else:
            con_loss = torch.tensor(0.0, device=cls_vector.device)

        p_cls  = torch.exp(-self.log_var_cls)
        p_ner  = torch.exp(-self.log_var_ner)
        ner_scaled = ner_loss * NER_WEIGHT

        total = (
            p_cls * (cls_loss + CONTRASTIVE_WEIGHT * con_loss) + self.log_var_cls
            + p_ner * ner_scaled + self.log_var_ner
        )

        return {
            "loss":          total,
            "action_loss":   action_loss.item(),
            "object_loss":   object_loss.item(),
            "ner_loss":      ner_loss.item(),
            "con_loss":      con_loss.item(),
            "action_logits": action_logits,
            "object_logits": object_logits,
        }

    def set_trainable_backbone_layers(self, n_last_layers: int = 0):
        for p in self.backbone.parameters():
            p.requires_grad = False

        if n_last_layers <= 0:
            return

        layers = getattr(getattr(self.backbone, "encoder", None), "layer", None)
        if layers is None:
            return

        for layer in list(layers)[-n_last_layers:]:
            for p in layer.parameters():
                p.requires_grad = True

    def _trainable_backbone_group(self):
        params = [p for p in self.backbone.parameters() if p.requires_grad]
        if not params:
            return None
        return {"params": params, "lr": 2e-5}

    def get_param_groups(self, phase: int) -> list:
        if phase == 1:
            groups = [
                {"params": self.adapters.parameters(),    "lr": 1e-3},
                {"params": self.action_head.parameters(), "lr": 1e-3},
                {"params": self.object_head.parameters(), "lr": 1e-3},
                {"params": self.ner_linear.parameters(),  "lr": 1e-3},
                {"params": [self.log_var_cls,
                            self.log_var_ner],            "lr": 1e-3},
            ]
        elif phase == 2:
            groups = [
                {"params": self.adapters.parameters(),    "lr": 1e-3},
                {"params": self.action_head.parameters(), "lr": 5e-4},
                {"params": self.object_head.parameters(), "lr": 5e-4},
                {"params": self.ner_linear.parameters(),  "lr": 5e-4},
                {"params": [self.log_var_cls,
                            self.log_var_ner],            "lr": 1e-3},
            ]
        else:  # phase 3
            groups = [
                {"params": self.adapters.parameters(),          "lr": 2e-4},
                {"params": self.proj_head.parameters(),         "lr": 5e-4},
                {"params": self.action_head.parameters(),       "lr": 1e-4},
                {"params": self.object_head.parameters(),       "lr": 1e-4},
                {"params": self.ner_linear.parameters(),        "lr": 1e-4},
                {"params": [self.log_var_cls,
                            self.log_var_ner],                  "lr": 2e-4},
            ]

        backbone_group = self._trainable_backbone_group()
        if backbone_group:
            groups.insert(0, backbone_group)
        return groups

class NLUInference:
    def __init__(self, model_path: str = None):
        self.tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL)
        self.model     = MDeBERTaNLU()

        if model_path:
            state = torch.load(model_path, map_location="cpu")
            self.model.load_state_dict(state)
            print(f"[NLUInference] loaded from {model_path}")

        self.model.eval()

    def predict(self, text: str) -> dict:
        enc = self._encode(text)
        with torch.no_grad():
            out = self.model(
                enc["input_ids"],
                enc["attention_mask"]
            )

        action_probs = torch.softmax(out["action_logits"], dim=-1)[0]
        object_probs = torch.softmax(out["object_logits"], dim=-1)[0]

        action_idx   = int(action_probs.argmax())
        object_idx   = int(object_probs.argmax())

        entities     = self._decode_entities(
            text,
            out["tags"][0],
            enc["word_ids"]
        )

        return {
            "action":        IDX_TO_ACTION[action_idx],
            "object":        IDX_TO_OBJECT[object_idx],
            "action_conf":   float(action_probs[action_idx]),
            "object_conf":   float(object_probs[object_idx]),
            "action_second": IDX_TO_ACTION[
                int(action_probs.topk(2).indices[1])
            ],
            "object_second": IDX_TO_OBJECT[
                int(object_probs.topk(2).indices[1])
            ],
            "variance":      0.0,
            "entities":      entities,
            "action_probs":  action_probs.numpy(),
            "object_probs":  object_probs.numpy(),
        }

    def predict_with_uncertainty(self, text: str,
                                  n: int = MC_SAMPLES) -> dict:
        enc           = self._encode(text)
        self.model.train()   
        mc_action     = []
        mc_object     = []

        with torch.no_grad():
            for _ in range(n):
                out = self.model(
                    enc["input_ids"],
                    enc["attention_mask"]
                )
                mc_action.append(
                    torch.softmax(out["action_logits"], dim=-1)[0].numpy()
                )
                mc_object.append(
                    torch.softmax(out["object_logits"], dim=-1)[0].numpy()
                )

        self.model.eval()

        mc_action   = np.array(mc_action)   
        mc_object   = np.array(mc_object)  

        mean_action = mc_action.mean(axis=0)
        mean_object = mc_object.mean(axis=0)
        variance    = float(mc_action.var(axis=0).max())

        action_idx  = int(mean_action.argmax())
        object_idx  = int(mean_object.argmax())
        action_conf = float(mean_action[action_idx])
        object_conf = float(mean_object[object_idx])

        self.model.eval()
        with torch.no_grad():
            out = self.model(enc["input_ids"], enc["attention_mask"])

        entities = self._decode_entities(
            text, out["tags"][0], enc["word_ids"]
        )

        return {
            "action":        IDX_TO_ACTION[action_idx],
            "object":        IDX_TO_OBJECT[object_idx],
            "action_conf":   action_conf,
            "object_conf":   object_conf,
            "action_second": IDX_TO_ACTION[
                int(np.argsort(mean_action)[::-1][1])
            ],
            "object_second": IDX_TO_OBJECT[
                int(np.argsort(mean_object)[::-1][1])
            ],
            "variance":      variance,
            "entities":      entities,
            "action_probs":  mean_action,
            "object_probs":  mean_object,
        }

    def _encode(self, text: str) -> dict:
        enc = self.tokenizer(
            text,
            max_length     = 64,
            padding        = "max_length",
            truncation     = True,
            return_tensors = "pt",
        )
        return {
            "input_ids":      enc["input_ids"],
            "attention_mask": enc["attention_mask"],
            "word_ids":       enc.word_ids(),
        }

    def _decode_entities(self, text: str,
                         tags: list,
                         word_ids: list) -> dict:
        words      = text.split()
        entities   = {}
        cur_tag    = None
        cur_tokens = []
        prev_wid   = None

        for i, wid in enumerate(word_ids):
            if wid is None:
                if cur_tag and cur_tokens:
                    self._store(entities, cur_tag, cur_tokens)
                    cur_tag, cur_tokens = None, []
                continue

            if wid == prev_wid:
                prev_wid = wid
                continue

            tag  = IDX_TO_TAG.get(tags[i], "O")
            word = words[wid] if wid < len(words) else ""

            if tag.startswith("B-"):
                if cur_tag and cur_tokens:
                    self._store(entities, cur_tag, cur_tokens)
                cur_tag    = tag[2:]
                cur_tokens = [word]

            elif tag.startswith("I-") and cur_tag:
                cur_tokens.append(word)

            else:
                if cur_tag and cur_tokens:
                    self._store(entities, cur_tag, cur_tokens)
                cur_tag, cur_tokens = None, []

            prev_wid = wid

        if cur_tag and cur_tokens:
            self._store(entities, cur_tag, cur_tokens)

        return entities

    def _store(self, entities: dict, tag: str, tokens: list):
        value = " ".join(tokens)
        if tag in entities:
            existing = entities[tag]
            if isinstance(existing, list):
                existing.append(value)
            else:
                entities[tag] = [existing, value]
        else:
            entities[tag] = value

    def save(self, path: str):
        torch.save(self.model.state_dict(), path)
        print(f"[NLUInference] saved to {path}")