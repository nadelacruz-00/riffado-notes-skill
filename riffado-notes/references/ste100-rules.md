# Simplified English rules (ASD-STE100-based)

This file is a condensed version of the open-source skill [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT License, © 2026 Dustin Yuchen Teng), adapted for meeting notes. The bundled `scripts/ste-lint.py` is that project's linter, unchanged. ASD-STE100 is the AeroSpace and Defense Industries Association of Europe's controlled-English standard. This file paraphrases its rule categories and does not reproduce ASD's dictionary. The result is a clarity tool, not certified STE.

## Modes

- **STE-flavored** (summary, section text, glossary): apply all the structural rules below. Treat the lexical rules as advice. Notes need some range of words.
- **Strict** (action items and medical or safety instructions): apply every rule. Use one verb for one action across the whole note.

## Structural rules: apply these

| Rule | Do | Don't |
|---|---|---|
| Active voice | "The doctor prescribed paracetamol." | "Paracetamol was prescribed." Exception: passive is acceptable when the actor is unknown. |
| No phrasal verbs | "Start the test." / "Contact the bank." | "Kick off the test." / "Reach out to the bank." |
| One instruction per sentence | "Open the form. Fill in the phone number." | "Open the form and fill in the number, then check it." |
| Sentence length | ≤20 words for instructions, ≤25 words for descriptions | Long sentences with many clauses |
| No semicolons | Split the text into two sentences | Any `;` in prose |
| Noun clusters | ≤3 stacked nouns ("account branch code") | "customer account branch code mapping field" |
| No ellipsis | Keep the subject, the verb and the article | "Files not uploaded will be lost" (which files?) |
| Keep modality | "The test **may** show an infection." | Turn the hedge into a fact: "The test shows an infection." |
| Paragraphs | One topic per paragraph, ≤6 sentences | Paragraphs that mix topics |
| Lists | Use a list for 3 or more steps or conditions | A sequence hidden inside one sentence |

## Lexical rules: direction of travel

- **One word, one meaning.** Use one name for one thing, every time. Write "the patient" each time, not "the patient", then "she", then "the client". Write "CoreBank" each time, not "CB", then "core", then "the bank".
- **Linter word groups.** The linter treats the words in each group below as one meaning, and flags a note that mixes words from the same group. Use the first word of each group:
  - check (not verify, confirm, validate)
  - delete (not remove, erase)
  - start (not launch, begin, initiate)
  - stop (not halt, terminate)
  - show (not display)
  - use (not utilize, employ)
  - fix (not repair, correct)
  - send (not transmit)
  - get (not retrieve, fetch, obtain)
  - change (not modify, alter)

  Exception: keep a group word when it is part of a name, such as "Confirm button".
- **Verb, not noun.** Write "analyze the log", not "perform an analysis of the log".
- **Plain words.** Write "use", not "utilize". Write "help", not "provide assistance". Write "start", not "commence".
- **Domain terms.** Keep the technical terms that the meaning needs. Define a term once in the glossary when most readers will not know it.

## Simple tenses, with one exception

Prefer simple past and simple present. Write "We received the report", not "We have received the report". If a compound tense carries information the simple form cannot, keep it. Examples: "may have failed", or "has completed" when the result is available now.

## Scan checklist

Before you finalize the note, find and fix these six problems:

1. **Synonym rotation.** The note gives one thing several names.
2. **Hedge stacking.** The note piles up qualifiers, such as "it may potentially help to possibly…". State the claim once, at the strength the speaker used.
3. **Nominalization.** The note uses "perform a review of" instead of "review".
4. **Marketing adjectives.** The note uses "seamless", "robust" or "powerful". Delete the word, or give the fact that supports it.
5. **Run-on sentences.** A sentence holds many ideas. Split it so each sentence holds one idea.
6. **Soft phrasal verbs.** The note uses "spin up", "reach out", "dive into" or "kick off".

## Linter

```bash
python3 <skill-dir>/scripts/ste-lint.py notes.md            # human-readable findings
python3 <skill-dir>/scripts/ste-lint.py --json notes.md     # structured output
```

The linter skips code fences, so Mermaid blocks are safe. Passive voice and compound tenses are advisory findings only. The linter never flags hedges. Fix hard violations in your own prose. Ignore findings inside recording titles, system names or quoted speech. Those are not your sentences.

## Never

- Never drop a safety condition, an exception or a number to make a sentence shorter.
- Never add a fact, a cause or a frequency that the speaker did not state.
- Never shorten a sentence past the point where it stays clear. The goal is no ambiguity, not the fewest words.
