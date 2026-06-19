from transformers import AutoTokenizer
ENCODER_MODEL = "microsoft/mdeberta-v3-base"
MAX_LENGTH = 64

_tokenizer = None
_session = None

def load(model_path: str):
    global _tokenizer, _session

_tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL)

print(_tokenizer("add note ml assignment")["input_ids"])
print(_tokenizer.encode("test", add_special_tokens=True))