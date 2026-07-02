#!/usr/bin/env python3
"""
Build a chat fine-tuning corpus for TinyStories-Instruct models.

Sources:
  - allenai/soda (CC BY 4.0): everyday two-person dialogues, filtered hard for
    simple English (the base model only knows TinyStories-level vocabulary).
    We keep the longest *contiguous window* of simple turns per dialogue (not
    just the prefix — many dialogues fail on turn 1 but have clean middles)
    and deterministically rename speakers to TinyStories-frequent names so
    rare-name tokens neither reject dialogues nor inflate the pruned vocab.
  - li2017dailydialog/daily_dialog (CC BY-NC-SA 4.0): human-written everyday
    chat from English-learner materials; naturally simple English.
  - tools/qa_facts.py (hand-written): kindergarten Q&A the model *can*
    memorize, plus "meta honesty" exchanges.
  - allenai/sciq (CC BY-NC 3.0): only the *questions*, deliberately allowed
    to be OOV, paired with hand-written deflection replies — teaches "I
    don't know" for questions beyond a tiny model, while the answerable QA
    above teaches the opposite side of that decision boundary. A fraction of
    these get an easy QA follow-up so the bot learns to recover after
    deflecting instead of refusing everything.
  - TinyStories-Instruct validation text: mixed in so the fine-tune doesn't
    forget how to write stories (story mode keeps working).

Output samples (plain text, one per line-block, separated by blank lines):
  User: <turn>\nBot: <turn><|endoftext|>\nUser: ...
The literal "<|endoftext|>" is understood by GPT2Tokenizer as the EOS token,
so the training script can tokenize samples as-is. The on-device chat mode
reproduces exactly this format, inserting EOS between exchanges.

Usage:
  ../cardputer_ai_venv/bin/python tools/prepare_chat_data.py
"""

import argparse
import json
import random
import re
from pathlib import Path

from qa_facts import qa_pairs, DEFLECTIONS

EOS = "<|endoftext|>"

# Names that appear all over TinyStories — replacements for SODA's rarer
# speaker names. All tokenize into the kept vocab.
TS_NAMES = [
    "Tom", "Lily", "Ben", "Sam", "Anna", "Mia", "Max", "Sue", "Jack", "Emma",
    "Tim", "Amy", "Lucy", "Jane", "Bob", "Billy", "Sara", "Jill", "Joe",
    "Mark", "Kate", "Molly", "Peter", "Ellie", "Leo", "Nina", "Ella",
    "Jake", "Dan", "Meg", "Beth", "Fred", "Ann", "Toby", "Polly", "Ruby",
    "Will", "Mary", "John", "Lisa",
]

# Speaker names that are also common English words — renaming these would
# mangle normal text ("Hope you are ok"), so leave them alone.
NAME_STOPLIST = {
    "Hope", "Grace", "Rose", "Joy", "Faith", "Autumn", "Summer", "Dawn",
    "May", "June", "Angel", "Destiny", "Star", "Sky", "Rain", "Honey",
    "Ginger", "Pepper", "Sunny", "Happy", "Melody", "Harmony", "Precious",
    "Miracle", "Mom", "Dad", "Teacher", "Doctor", "Nurse", "Coach", "Boss",
}


def tinystories_token_set(snap: Path, valid_txt: Path):
    from tokenizers import ByteLevelBPETokenizer
    tok = ByteLevelBPETokenizer(str(snap / "vocab.json"), str(snap / "merges.txt"))
    text = valid_txt.read_text()
    seen = set()
    CH = 1_000_000
    for i in range(0, len(text), CH):
        seen.update(tok.encode(text[i:i + CH]).ids)
    return tok, seen


def clean_turn(t):
    """One turn = one line of the sample format; make sure it stays that way."""
    t = t.replace(EOS, " ")
    return re.sub(r"\s+", " ", t).strip()


def turn_ok(t, tok, known, max_words, max_oov_frac):
    words = t.split()
    if not words or len(words) > max_words:
        return False
    ids = tok.encode(t).ids
    oov = sum(1 for i in ids if i not in known)
    return oov / len(ids) <= max_oov_frac


def simple_windows(turns, tok, known, max_words, max_oov_frac):
    """Longest contiguous run of simple turns anywhere in the dialogue.
    Speakers strictly alternate, so any window relabels cleanly with its
    first turn as User."""
    ok = [turn_ok(t, tok, known, max_words, max_oov_frac) for t in turns]
    best_i = best_j = 0
    i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]:
                j += 1
            if j - i > best_j - best_i:
                best_i, best_j = i, j
            i = j
        else:
            i += 1
    return turns[best_i:best_j]


def simple_prefix(turns, tok, known, max_words, max_oov_frac):
    """Old behavior (--prefix-only): longest simple prefix."""
    kept = []
    for t in turns:
        if not turn_ok(t, tok, known, max_words, max_oov_frac):
            break
        kept.append(t)
    return kept


def rename_speakers(turns, speakers, rng):
    """Map this dialogue's speaker names onto TinyStories-frequent names.
    Deterministic per dialogue (rng is seeded globally, dialogues are read
    in a fixed order). Only simple capitalized names are touched."""
    distinct = []
    for s in speakers:
        if s not in distinct:
            distinct.append(s)
    renameable = [s for s in distinct
                  if re.fullmatch(r"[A-Z][a-z]{2,}", s)
                  and s not in NAME_STOPLIST and s not in TS_NAMES]
    if not renameable:
        return turns
    text_all = " ".join(turns)
    pool = [n for n in TS_NAMES
            if not re.search(rf"\b{n}\b", text_all)]
    rng.shuffle(pool)
    mapping = dict(zip(renameable, pool))
    for old, new in mapping.items():
        pat = re.compile(rf"\b{re.escape(old)}\b")
        turns = [pat.sub(new, t) for t in turns]
    return turns


def format_dialogue(turns):
    """Alternate User/Bot; every Bot turn ends with EOS (the device's stop)."""
    out = []
    for i, t in enumerate(turns):
        if i % 2 == 0:
            out.append(f"User: {t}")
        else:
            out.append(f"Bot: {t}{EOS}")
    return "\n".join(out)


def trim_even(turns, min_turns):
    """End on a Bot turn; None if too short."""
    if len(turns) % 2 == 1:
        turns = turns[:-1]
    return turns if len(turns) >= min_turns else None


def story_samples(valid_txt: Path, n_chars: int, rng):
    """Random complete records (instruction header + story) from the
    TinyStories-Instruct text, which uses <|endoftext|> as separator."""
    text = valid_txt.read_text()
    records = [r.strip() for r in text.split(EOS) if len(r.strip()) > 100]
    rng.shuffle(records)
    out, total = [], 0
    for r in records:
        if total >= n_chars:
            break
        out.append(r + EOS)
        total += len(r)
    return out


def soda_samples(tok, known, args, rng):
    from datasets import load_dataset
    ds = load_dataset("allenai/soda", split="train", streaming=True)
    pick = simple_prefix if args.prefix_only else simple_windows
    chats, chars, scanned = [], 0, 0
    for ex in ds:
        scanned += 1
        if scanned > args.dialogues or chars >= args.max_chat_chars:
            scanned -= 1
            break
        turns = [clean_turn(t) for t in ex["dialogue"]]
        if args.rename_speakers:
            turns = rename_speakers(turns, ex.get("speakers") or [], rng)
        turns = pick(turns, tok, known, args.max_words, args.max_oov)
        turns = trim_even(turns, args.min_turns)
        if not turns:
            continue
        s = format_dialogue(turns)
        chats.append(s)
        chars += len(s)
        if scanned % 25000 == 0:
            print(f"    SODA scanned {scanned:,}: kept {len(chats):,} "
                  f"({chars/1e6:.1f} M chars)")
    return chats, chars, scanned


def normalize_dd(t):
    """DailyDialog text is pre-tokenized: ' I ’ m fine . ' -> 'I'm fine.'"""
    t = t.replace("’", "'")
    t = re.sub(r"\s*'\s*", "'", t)
    t = re.sub(r"\s+([.,!?;:%])", r"\1", t)
    # native DD artifact: missing space after sentence end ("work.It's");
    # require lowercase before the punctuation so acronyms are left alone
    t = re.sub(r"([a-z]{2}[.!?])([A-Z])", r"\1 \2", t)
    return clean_turn(t)


def dailydialog_samples(tok, known, args):
    from datasets import load_dataset
    # Script datasets are unsupported in datasets>=3; use the parquet export.
    ds = load_dataset("li2017dailydialog/daily_dialog",
                      revision="refs/convert/parquet", split="train")
    pick = simple_prefix if args.prefix_only else simple_windows
    chats, chars = [], 0
    for ex in ds:
        turns = [normalize_dd(t) for t in ex["dialog"]]
        turns = pick(turns, tok, known, args.max_words, args.max_oov)
        turns = trim_even(turns, args.min_turns)
        if not turns:
            continue
        s = format_dialogue(turns)
        chats.append(s)
        chars += len(s)
    return chats, chars


def qa_samples(rng, repeat):
    """Answerable kindergarten QA, grouped 1-2 exchanges per sample."""
    out = []
    for _ in range(repeat):
        pairs = qa_pairs(rng)
        i = 0
        while i < len(pairs):
            take = 2 if rng.random() < 0.35 and i + 1 < len(pairs) else 1
            turns = []
            for q, a in pairs[i:i + take]:
                turns += [q, a]
            out.append(format_dialogue(turns))
            i += take
    rng.shuffle(out)
    return out, sum(len(s) for s in out)


def idk_samples(tok, known, args, rng):
    """Hard (out-of-scope) questions + hand-written deflections. A fraction
    gets an answerable follow-up so deflection doesn't become the default."""
    from datasets import load_dataset
    ds = load_dataset("allenai/sciq", split="train")
    qs, seen = [], set()
    for ex in ds:
        q = clean_turn(ex["question"])
        if not q.endswith("?") or len(q.split()) > 15:
            continue
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        # These *should* look unfamiliar — but cap OOV so tokenization noise
        # doesn't dominate, and skip anything with weird symbols.
        ids = tok.encode(q).ids
        if sum(1 for i in ids if i not in known) / len(ids) > 0.4:
            continue
        if re.search(r"[^A-Za-z0-9 ,.'?-]", q):
            continue
        qs.append(q)
        if len(qs) >= args.idk_max:
            break
    easy = qa_pairs(rng)
    out = []
    for i, q in enumerate(qs):
        turns = [q, rng.choice(DEFLECTIONS)]
        if rng.random() < args.idk_followup_frac:
            eq, ea = easy[i % len(easy)]
            turns += [eq, ea]
        out.append(format_dialogue(turns))
    rng.shuffle(out)
    return out, sum(len(s) for s in out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dialogues", type=int, default=500000,
                    help="max SODA dialogues to scan")
    ap.add_argument("--max-chat-chars", type=int, default=30_000_000,
                    help="stop scanning SODA at this many kept chars")
    ap.add_argument("--max-words", type=int, default=22, help="per turn")
    ap.add_argument("--max-oov", type=float, default=0.02,
                    help="max fraction of tokens outside the TinyStories set")
    ap.add_argument("--min-turns", type=int, default=2)
    ap.add_argument("--story-frac", type=float, default=0.3,
                    help="fraction of corpus chars that are story records")
    ap.add_argument("--val-frac", type=float, default=0.01)
    ap.add_argument("--prefix-only", action="store_true",
                    help="old behavior: longest simple prefix, no windows")
    ap.add_argument("--rename-speakers", action=argparse.BooleanOptionalAction,
                    default=True)
    ap.add_argument("--dailydialog", action=argparse.BooleanOptionalAction,
                    default=True)
    ap.add_argument("--qa-repeat", type=int, default=5,
                    help="times the templated QA set is re-rolled (0 = off)")
    ap.add_argument("--idk-max", type=int, default=6000,
                    help="max SciQ 'I don't know' samples (0 = off)")
    ap.add_argument("--idk-followup-frac", type=float, default=0.4,
                    help="fraction of IDK samples with an easy QA follow-up")
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--cache", default=str(Path.home() / ".cache" / "cardputer_ai"))
    args = ap.parse_args()

    from huggingface_hub import snapshot_download, hf_hub_download
    snap = Path(snapshot_download(repo_id="roneneldan/TinyStories-Instruct-3M",
                                  cache_dir=args.cache,
                                  allow_patterns=["*.json", "merges.txt"]))
    valid = Path(hf_hub_download(repo_id="roneneldan/TinyStoriesInstruct",
                                 repo_type="dataset",
                                 filename="TinyStories-Instruct-valid.txt",
                                 cache_dir=args.cache))

    print("[+] building TinyStories token set...")
    tok, known = tinystories_token_set(snap, valid)
    print(f"[+] {len(known):,} known tokens")

    rng = random.Random(1234)

    print("[+] scanning SODA...")
    soda, soda_chars, scanned = soda_samples(tok, known, args, rng)
    print(f"[+] SODA kept: {len(soda):,} / {scanned:,} "
          f"({100*len(soda)/max(1,scanned):.0f}% yield, {soda_chars/1e6:.1f} M chars)")

    dd, dd_chars = ([], 0)
    if args.dailydialog:
        dd, dd_chars = dailydialog_samples(tok, known, args)
        print(f"[+] DailyDialog kept: {len(dd):,} ({dd_chars/1e6:.1f} M chars)")

    qa, qa_chars = ([], 0)
    if args.qa_repeat > 0:
        qa, qa_chars = qa_samples(rng, args.qa_repeat)
        print(f"[+] kindergarten QA: {len(qa):,} ({qa_chars/1e6:.1f} M chars)")

    idk, idk_chars = ([], 0)
    if args.idk_max > 0:
        idk, idk_chars = idk_samples(tok, known, args, rng)
        print(f"[+] IDK (SciQ + deflections): {len(idk):,} "
              f"({idk_chars/1e6:.1f} M chars)")

    chat_chars = soda_chars + dd_chars + qa_chars + idk_chars
    n_story_chars = int(chat_chars * args.story_frac / (1 - args.story_frac))
    stories = story_samples(valid, n_story_chars, rng)
    print(f"[+] story records mixed in: {len(stories):,} ({n_story_chars/1e6:.1f} M chars)")

    samples = soda + dd + qa + idk + stories
    rng.shuffle(samples)
    n_val = max(1, int(len(samples) * args.val_frac))

    out = Path(args.out_dir)
    out.mkdir(exist_ok=True)
    (out / "chat_val.txt").write_text("\n\n".join(samples[:n_val]) + "\n")
    (out / "chat_train.txt").write_text("\n\n".join(samples[n_val:]) + "\n")
    meta = {"train_samples": len(samples) - n_val, "val_samples": n_val,
            "chat_chars": chat_chars, "story_chars": n_story_chars,
            "sources": {
                "soda":        {"samples": len(soda), "chars": soda_chars,
                                "scanned": scanned},
                "dailydialog": {"samples": len(dd), "chars": dd_chars},
                "qa":          {"samples": len(qa), "chars": qa_chars},
                "idk":         {"samples": len(idk), "chars": idk_chars},
                "stories":     {"samples": len(stories), "chars": n_story_chars},
            },
            "args": {k: v for k, v in vars(args).items() if k != "cache"}}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"[+] wrote {out/'chat_train.txt'} ({len(samples)-n_val:,} samples) "
          f"and {out/'chat_val.txt'} ({n_val:,})")


if __name__ == "__main__":
    main()
