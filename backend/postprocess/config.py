REQUIRED = {
    ("ADD", "MEETING"): ["DATE"],
    ("ADD", "TASK"): ["TITLE"],
    ("ADD", "NOTE"): [],
    ("ADD", "PROGRESS"): ["TITLE"],

    ("GET", "MEETING"): [],
    ("GET", "TASK"): [],
    ("GET", "NOTE"): [],
    ("GET", "PROGRESS"): [],

    ("UPDATE", "MEETING"): ["TITLE"],
    ("UPDATE", "TASK"): ["TITLE"],
    ("UPDATE", "NOTE"): [],
    ("UPDATE", "PROGRESS"): ["TITLE"],

    ("DELETE", "MEETING"): [],
    ("DELETE", "TASK"): [],
    ("DELETE", "NOTE"): [],
    ("DELETE", "PROGRESS"): [],
}