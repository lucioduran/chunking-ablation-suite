"""Generate the original fictional fixtures from reviewed literal templates."""

import json
from pathlib import Path

from chunking_suite.core import document_text


def create() -> dict:
    documents, queries = [], []
    subjects = [
        ("Aster", "dev", "pump", "pressure", "18", "45", "amber"),
        ("Birch", "dev", "relay", "voltage", "24", "60", "violet"),
        ("Cobalt", "eval", "cooler", "temperature", "12", "90", "silver"),
        ("Delta", "eval", "valve", "flow", "32", "75", "copper"),
        ("Ember", "eval", "fan", "speed", "48", "120", "indigo"),
        ("Flint", "eval", "sensor", "humidity", "65", "150", "scarlet"),
    ]
    for name, split, device, quantity, limit, delay, badge in subjects:
        for kind in ("code", "table", "cross_reference"):
            doc_id = f"{name.lower()}-{kind}"
            blocks: list[dict] = []
            labels = []

            def add(section: str, text: str, target: list[dict] = blocks) -> None:
                target.append({"section": section, "text": text})

            add(
                "overview",
                f"# {name} {device}: {kind.replace('_', ' ')} reference\n"
                f"This fictional manual covers the {name} station {device}. "
                f"Operators distinguish the live {quantity} reading from the test reading. "
                "Test readings never authorize a live restart. Keep the maintenance log "
                "with the device serial number and record the current shift before changing settings.",
            )
            if kind == "code":
                add(
                    "startup",
                    f"## Starting the {name} controller\n"
                    f"The controller checks {quantity} before enabling the {device}. "
                    "The maintenance branch returns a diagnostic result without activating hardware. "
                    "A missing reading is a hard failure. Callers must handle the exception and "
                    "must not replace a missing reading with zero. This distinction matters during startup.",
                )
                code = (
                    f"```python\ndef start_{device}(reading, maintenance=False):\n"
                    "    if reading is None:\n        raise ValueError('missing reading')\n"
                    "    if maintenance:\n        return 'diagnostic-only'\n"
                    f"    if reading > {limit}:\n        return 'blocked'\n"
                    f"    return 'start-{badge}'\n```"
                )
                add("startup", code)
                labels += [
                    (
                        f"In {name}'s {device} function, what happens if the reading is missing?",
                        ["if reading is None:\n        raise ValueError('missing reading')"],
                    ),
                    (
                        f"What does {name}'s {device} startup return in maintenance mode?",
                        ["if maintenance:\n        return 'diagnostic-only'"],
                    ),
                ]
                add(
                    "retries",
                    f"## Retry policy\nThe {name} {device} startup caller waits {delay} seconds "
                    "after a blocked attempt. A diagnostic-only result is not a blocked attempt. "
                    "Retries require a new reading; cached readings cannot be reused. The retry "
                    "counter is reset only after a successful live start, never after a diagnostic run.",
                )
                labels += [
                    (
                        f"For {name}'s {device}, what threshold blocks startup and how long must "
                        "the caller wait after it is blocked?",
                        [
                            f"if reading > {limit}:\n        return 'blocked'",
                            f"startup caller waits {delay} seconds",
                        ],
                    )
                ]
            elif kind == "table":
                add(
                    "limits",
                    f"## {name} limits\nUse the active-mode row for the live {device}. "
                    "The standby row applies only after shutdown. The inspection row is used "
                    "during supervised maintenance and does not authorize production. Each row "
                    "specifies its own maximum reading, wait duration, and required permit. "
                    "Never combine cells from different rows.",
                )
                add(
                    "limits",
                    "| Mode | Maximum reading | Wait seconds | Permit |\n"
                    "| --- | ---: | ---: | --- |\n"
                    f"| active | {limit} | {delay} | {badge} |\n"
                    f"| standby | {int(limit) + 7} | {int(delay) + 15} | white |\n"
                    f"| inspection | {int(limit) + 11} | {int(delay) + 30} | black |",
                )
                labels += [
                    (
                        f"What maximum reading and wait apply to the active {name} {device}?",
                        [f"| active | {limit} | {delay} | {badge} |"],
                    ),
                    (
                        f"Which permit and maximum reading are listed for {name} {device} inspection?",
                        [f"| inspection | {int(limit) + 11} | {int(delay) + 30} | black |"],
                    ),
                ]
                add(
                    "exceptions",
                    f"## Expired permits\nAn expired {badge} permit invalidates the active row "
                    f"for the {name} {device}. Renew it at the station desk before retrying. "
                    "Standby limits remain valid while renewal is pending. The desk cannot waive "
                    "the active maximum; approval restores permission but never changes the table values.",
                )
                labels += [
                    (
                        f"Which permit does the {name} active row require, and where is it renewed?",
                        [
                            f"| active | {limit} | {delay} | {badge} |",
                            "Renew it at the station desk before retrying.",
                        ],
                    )
                ]
            else:
                add(
                    "release",
                    f"## Release procedure R-{name}\n"
                    f"Release of the {name} {device} requires the {badge} permit defined in "
                    f"section P-{name}. The release operator must also complete the waiting rule "
                    f"in section W-{name}. A signature on the shift log records completion; "
                    "it does not replace either prerequisite. Training releases follow a separate "
                    "procedure and cannot authorize a live device.",
                )
                add(
                    "unrelated",
                    "## Archive retention\nArchive completed shift logs for fourteen days "
                    "in the local cabinet. Copy only the serial number into the central index. "
                    "The archive clerk checks page counts at the end of each shift. Missing "
                    "pages require an incident note, but the archive process cannot issue permits "
                    "or change device waiting rules.",
                )
                add(
                    "permit",
                    f"## P-{name}: Permit definition\n"
                    f"The {badge} permit requires two signatures: the operator and the duty engineer. "
                    f"This permit applies to the {name} {device} only. A training supervisor "
                    "cannot substitute for the duty engineer. Both signatures must be dated "
                    "during the current shift. An older signed permit expires at shift handover.",
                )
                add(
                    "wait",
                    f"## W-{name}: Waiting rule\n"
                    f"Wait {delay} seconds after the {quantity} falls below {limit} before release. "
                    "Restart the timer whenever the reading rises above the limit. "
                    "The operator records the final uninterrupted interval in the shift log. "
                    "The timer is a prerequisite separate from the permit signatures.",
                )
                labels += [
                    (
                        f"What signatures are required by the permit referenced in {name}'s release procedure?",
                        [
                            f"Release of the {name} {device} requires the {badge} permit defined in section P-{name}.",
                            f"The {badge} permit requires two signatures: the operator and the duty engineer.",
                        ],
                    ),
                    (
                        f"What waiting rule does {name}'s release procedure reference?",
                        [
                            f"The release operator must also complete the waiting rule in section W-{name}.",
                            f"Wait {delay} seconds after the {quantity} falls below {limit} before release.",
                        ],
                    ),
                    (
                        f"When does {name}'s {badge} permit expire?",
                        ["An older signed permit expires at shift handover."],
                    ),
                ]
            add(
                "closing",
                f"## Contact\nFor an unreadable {name} label, stop the {device} and contact "
                "the station desk. This document contains fictional operational information for "
                "retrieval experiments only. It is not an engineering procedure for real equipment.",
            )
            doc = {"id": doc_id, "kind": kind, "split": split, "blocks": blocks}
            documents.append(doc)
            text = document_text(doc)
            for i, (question, evidence) in enumerate(labels):
                spans = []
                for fragment in evidence:
                    assert text.count(fragment) == 1, fragment
                    start = text.index(fragment)
                    spans.append([start, start + len(fragment)])
                queries.append(
                    {
                        "id": f"{doc_id}-q{i + 1}",
                        "doc_id": doc_id,
                        "split": split,
                        "text": question,
                        "evidence": spans,
                    }
                )
    return {"version": 1, "documents": documents, "queries": queries}


if __name__ == "__main__":
    Path("data/fixtures.json").write_text(json.dumps(create(), indent=2) + "\n", encoding="utf-8")
