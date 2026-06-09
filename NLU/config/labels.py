ENCODER_MODEL = "microsoft/mdeberta-v3-base"

ACTION_LABELS = {
    "ADD":          0,
    "GET":          1,
    "UPDATE":       2,
    "DELETE":       3,
}
IDX_TO_ACTION = {v: k for k, v in ACTION_LABELS.items()}
NUM_ACTIONS   = len(ACTION_LABELS)

OBJECT_LABELS = {
    "TASK":         0,
    "MEETING":      1,
    "PROGRESS":     2,
    "NOTE":         3,
}
IDX_TO_OBJECT = {v: k for k, v in OBJECT_LABELS.items()}
NUM_OBJECTS   = len(OBJECT_LABELS)

VALID_COMBINATIONS = {
    ("ADD",    "TASK"),
    ("GET",    "TASK"),
    ("UPDATE", "TASK"),
    ("DELETE", "TASK"),
    ("ADD",    "MEETING"),
    ("GET",    "MEETING"),
    ("UPDATE", "MEETING"),
    ("DELETE", "MEETING"),
    ("ADD",    "PROGRESS"),
    ("GET",    "PROGRESS"),
    ("UPDATE", "PROGRESS"),
    ("DELETE", "PROGRESS"),
    ("ADD",    "NOTE"),
    ("GET",    "NOTE"),
    ("UPDATE", "NOTE"),
    ("DELETE", "NOTE"),
}

NER_TAGS = {
    "O":               0,
    "B-TITLE":         1,  "I-TITLE":         2,
    "B-DATE":          3,  "I-DATE":          4,
    "B-TIME":          5,  "I-TIME":          6,
    "B-PERSON":        7,  "I-PERSON":        8,
    "B-LOCATION":      9,  "I-LOCATION":      10,
    "B-STATUS":        11, "I-STATUS":        12,
    "B-FIELD":         13, "I-FIELD":         14,
    "B-VALUE":         15, "I-VALUE":         16,
    "B-CONTENT":       17, "I-CONTENT":       18,
}
IDX_TO_TAG = {v: k for k, v in NER_TAGS.items()}
NUM_TAGS   = len(NER_TAGS)

OBJECT_ENTITIES = {
    "TASK":     {"required": [],"optional": ["TITLE","DATE","TIME","STATUS"]},
    "MEETING":  {"required": [],"optional": ["TIME","PERSON","LOCATION","TITLE","DATE","STATUS"]},
    "PROGRESS": {"required": [],"optional": ["FIELD","VALUE","TITLE","STATUS"]},
    "NOTE":     {"required": [],"optional": ["TITLE","CONTENT"]},
}

NER_CLASS_WEIGHTS = [
    1.0,        # O
    2.0, 2.0,   # B-TITLE    I-TITLE
    2.0, 2.0,   # B-DATE     I-DATE
    1.8, 1.8,   # B-TIME     I-TIME
    2.0, 2.0,   # B-PERSON   I-PERSON
    1.8, 1.8,   # B-LOCATION I-LOCATION
    2.2, 2.2,   # B-STATUS   I-STATUS
    2.5, 2.5,   # B-FIELD    I-FIELD
    1.2, 1.2,   # B-VALUE    I-VALUE
    1.0, 1.0,   # B-CONTENT  I-CONTENT
]

OBJECT_CLASS_WEIGHTS = [
    4.0,  
    1.5,  
    3.5,  
    1.0,  
]

ADAPTER_SIZE    = 128   
ADAPTER_DROPOUT = 0.1

# Training
PHASE1_EPOCHS   = 5    
PHASE2_EPOCHS   = 15   
PHASE3_EPOCHS   = 15   

BATCH_SIZE      = 240
MAX_LENGTH      = 64

ADAPTER_LR      = 1e-3
HEAD_LR_P2      = 2e-3
HEAD_LR_P3      = 1e-3

CONTRASTIVE_WEIGHT = 0.25  
NER_WEIGHT         = 0.4    
CONTRASTIVE_TEMP   = 0.07   

CONFIDENCE_THRESHOLD = 0.82
MARGIN_THRESHOLD     = 0.18
VARIANCE_THRESHOLD   = 0.04
MC_SAMPLES           = 30