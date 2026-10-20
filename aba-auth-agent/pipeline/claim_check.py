"""Trace the numbers in a generated narrative back to the extracted source data.

A small model lists the narrative's quantitative claims; this module decides which of
them can't be traced. It is deliberately deterministic and number-aware:

* Formatting never matters: "7.8 per hour", "1,872 of 2,080" and "06/10/2026" match source
  values 7.8, 1872, 2080 and "2026-06-10".
* Each claim is checked against the part of the source it is about, found by matching the
  words in the claim's description ("task refusal baseline rate") to record and field
  names. A wrong baseline therefore can't pass by equalling an unrelated score elsewhere.
  If nothing in the source matches the description, the whole source is used instead.
* Derived values are accepted when they are simple arithmetic on numbers that sit together
  in the source: the baseline and current of one behavior, the previous and current score
  of one assessment, the units of one service, a count of items in a list, a total of
  sibling values. Arithmetic across unrelated numbers is NOT accepted, so a made-up
  figure doesn't pass by coincidence of some far-off pair.

It is a smoke detector, not an audit: a wrong number that happens to equal another number
in the source still passes, so the BCBA review remains the real check.
"""

import itertools
import json
import math
import re
from typing import Any

# Codes are identifiers, not measurements: ICD-10 ("F84.0") and five-digit CPT/HCPCS ("97153")
_IDENTIFIER = re.compile(r"\b[A-Z]\d{2}(?:\.\d+)?\b|\b\d{5}\b")
_NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
_MAX_PAIR_OPERANDS = 20
# Scopes scoring at least this fraction of the best match are all consulted.
_NEAR_BEST = 0.8

# Numbers a narrative legitimately cites that are rules, not client data: payors expect
# an explanation when service utilization falls below 80%.
_RULE_NUMBERS = {80.0}


def numbers_in(text: Any) -> list[float]:
    """Every number in a piece of text, ignoring thousands separators."""
    return [round(float(token.replace(",", "")), 6) for token in _NUMBER.findall(str(text))]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


_STOPWORDS = {
    "the", "and", "for", "per", "with", "from", "that", "this", "are", "was", "were", "has",
    "had", "its", "not", "all", "any", "total", "number", "value", "score", "claim", "stated",
}


def words_in(text: Any) -> set[str]:
    """Lower-case content words, lightly stemmed, for matching a claim to source fields."""
    found = set(re.findall(r"\d{4,}", str(text)))  # billing codes and years identify records too
    for word in re.findall(r"[a-zA-Z]{3,}", str(text).replace("_", " ")):
        word = word.lower()
        if word in _STOPWORDS:
            continue
        found.add(word[:-1] if word.endswith("s") and len(word) > 3 else word)
    return found


class Scope:
    """One record (or list) of the source: its words, its numbers, and values derived from it."""

    def __init__(self, words: set[str], parent: "Scope | None" = None):
        self.words = words
        self.parent = parent  # the list this record sits in, which holds counts and totals
        self.direct: set[float] = set()
        self._derived: list[float] = []
        self._additive: list[float] = []  # sums, differences and counts only (no percentages)
        self._one_decimal: set[float] = set()
        self._whole: set[int] = set()

    def finish(self) -> "Scope":
        self._one_decimal = {round(v, 1) for v in self._derived}
        self._whole = {round(v) for v in self._derived}
        self._additive_one_decimal = {round(v, 1) for v in self._additive}
        self._additive_whole = {round(v) for v in self._additive}
        return self

    def derives(self, number: float) -> bool:
        """Whether the number is simple arithmetic on this scope's values."""
        if round(number, 1) in self._one_decimal:
            return True
        return float(number).is_integer() and int(number) in self._whole

    def derives_additively(self, number: float) -> bool:
        """Like derives, but only sums, differences and counts, which are specific enough
        to trust in a loosely matched record (percentages are not)."""
        if round(number, 1) in self._additive_one_decimal:
            return True
        return float(number).is_integer() and int(number) in self._additive_whole

    def explains(self, number: float) -> bool:
        return number in self.direct or self.derives(number)


class SourceNumbers:
    """The source split into scopes, each with its numbers and the derived values worth accepting."""

    def __init__(self, source: Any):
        self.scopes: list[Scope] = []
        self._walk(source, "")

    def _walk(self, node: Any, key: str, parent: "Scope | None" = None) -> None:
        if isinstance(node, dict):
            scope = Scope(words_in(key) | words_in(" ".join(node.keys())), parent)
            numeric = []
            for name, value in node.items():
                if _is_number(value):
                    scope.direct.add(round(float(value), 6))
                    numeric.append(float(value))
                elif isinstance(value, str):
                    scope.direct.update(numbers_in(value))
                    scope.words |= words_in(value)
            self._derive_from_siblings(scope, numeric)
            self.scopes.append(scope.finish())
            for name, value in node.items():
                if isinstance(value, (dict, list)):
                    self._walk(value, name)
        elif isinstance(node, list):
            scope = Scope(words_in(key))
            for item in node:
                if _is_number(item):
                    scope.direct.add(round(float(item), 6))
                elif isinstance(item, str):
                    scope.direct.update(numbers_in(item))
                    scope.words |= words_in(item)
            self._derive_from_list(scope, node)
            self.scopes.append(scope.finish())
            for item in node:
                if isinstance(item, (dict, list)):
                    self._walk(item, key, scope)

    @staticmethod
    def _derive_from_siblings(scope: Scope, values: list[float]) -> None:
        """Arithmetic between numbers stored side by side in one record."""
        values = values[:_MAX_PAIR_OPERANDS]
        if len(values) >= 2:
            scope._derived.append(sum(values))
            scope._additive.append(sum(values))
        for a, b in itertools.permutations(values, 2):
            scope._derived.append(abs(a - b))
            scope._additive.append(abs(a - b))
            if b:
                scope._derived.append(a / b * 100)  # a as a percent of b
                scope._derived.append(abs(a - b) / abs(b) * 100)  # percent change from b

    @staticmethod
    def _derive_from_list(scope: Scope, items: list) -> None:
        """Counts, tallies and totals across a list of records."""
        if not items:
            return
        total = len(items)
        counts = [float(total)]
        records = [item for item in items if isinstance(item, dict)]

        for key in {k for record in records for k in record}:
            column = [record[key] for record in records if key in record]
            booleans = [v for v in column if isinstance(v, bool)]
            if booleans:
                counts.extend([float(sum(booleans)), float(len(booleans) - sum(booleans))])
            numbers = [float(v) for v in column if _is_number(v)]
            if len(numbers) >= 2:
                scope._derived.append(sum(numbers))
                scope._additive.append(sum(numbers))

        for count in counts:
            scope._derived.append(count)
            scope._additive.append(count)
            scope._derived.append(count / total * 100)

    def related_scopes(self, text: str) -> list[Scope]:
        """Every scope sharing at least one word with the text."""
        wanted = words_in(text)
        return [scope for scope in self.scopes if wanted & scope.words]

    def relevant_scopes(self, text: str) -> list[Scope]:
        """The scopes that best match the text; every scope if none match.

        Words are weighted by rarity, so a field name that only one record has ("mapp")
        counts for far more than one every record has ("current"). Scopes within a
        close margin of the best match are kept, since a claim about "3 of 6 skills
        mastered" is about the list as much as about any one skill in it.
        """
        wanted = words_in(text)
        document_frequency: dict[str, int] = {}
        for scope in self.scopes:
            for word in scope.words:
                document_frequency[word] = document_frequency.get(word, 0) + 1
        total = len(self.scopes)

        def weight(word: str) -> float:
            return math.log(1 + total / document_frequency[word])

        scored = [(sum(weight(w) for w in wanted & scope.words), scope) for scope in self.scopes]
        best = max((score for score, _ in scored), default=0.0)
        if best <= 0:
            return self.scopes
        chosen = [scope for score, scope in scored if score >= best * _NEAR_BEST]
        # A record's list holds the counts and totals ("2 of 3 mastered") the record can't
        for scope in list(chosen):
            if scope.parent is not None and scope.parent not in chosen:
                chosen.append(scope.parent)
        return chosen


def find_discrepancies(claims: list[dict], source: Any) -> list[str]:
    """Messages for claims whose numbers can't be traced to the source.

    `source` is the extracted clinical data (a pydantic model or plain dict).
    """
    if hasattr(source, "model_dump"):
        source = source.model_dump(mode="json")
    known = SourceNumbers(source)
    source_text = json.dumps(source, default=str)

    discrepancies = []
    for claim in claims:
        value = str(claim.get("value", "")).strip()
        # Identifiers such as ICD codes ("F80.9") or credential numbers appear as written
        if len(value) >= 4 and re.search(r"\d", value) and value in source_text:
            continue
        # Codes inside longer text ("F84.0 Autism Spectrum Disorder") need only be present
        # somewhere in the source; what is left is checked as ordinary numbers.
        identifiers = _IDENTIFIER.findall(value)
        missing_codes = [code for code in identifiers if code not in source_text]
        value_without_codes = _IDENTIFIER.sub(" ", value)
        description = f"{claim.get('claim', '')} {value}"
        scopes = known.relevant_scopes(description)
        related = known.related_scopes(description)
        untraced = [
            n for n in numbers_in(value_without_codes)
            if n not in _RULE_NUMBERS
            and not any(scope.explains(n) for scope in scopes)
            # A computed gain, total or count may come from a record the description only
            # partly matches; exact values and percentages may not.
            and not any(scope.derives_additively(n) for scope in related)
        ]
        if untraced or missing_codes:
            shown = ", ".join(missing_codes + [f"{n:g}" for n in untraced])
            discrepancies.append(
                f"[{claim.get('section', '?')}] Claim: {claim.get('claim', '?')} "
                f"(value: {value}) — could not trace {shown} to the source data. Verify manually."
            )
    return discrepancies
