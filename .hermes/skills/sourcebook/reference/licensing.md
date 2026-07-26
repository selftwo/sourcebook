# Licensing and content discipline

This is a working policy, not legal advice. Fair use and fair dealing vary by jurisdiction
and by use.

## The kit

Apache-2.0. Vendor `skills/sourcebook/` into a private repo freely.

## Quote budget

| Scope | Cap |
|---|---|
| Single quote | 25 words **or** 200 characters |
| Per source, in a shipped artifact | 3 quotes **and** 500 characters total |
| Per source, in the local ledger | unlimited (a working file, not a publication) |
| Full text of any source in an artifact | never |

`sb ledger --html` enforces this while rendering: quotes past the budget are replaced with
their span reference (`chars 12840-12886`), which still lets anyone holding the source verify
the citation. `sb verify` re-checks the rendered document and fails with `E-QUOTE-BUDGET` if
you pasted long quotes into the prose by hand.

`sb package --public` goes further and replaces over-budget quotes with
`{source_id, start, end, quote_sha256, length}`. Anyone with the same source verifies every
citation byte-for-byte; nobody gets a free copy of the source. `sb package --private` (the
default) ships everything, for your own machine and your own team.

## Attribution

`CC BY` and `CC BY-SA` assets render their credit string visibly in the artifact, not only in
`credits.json`. Public domain and CC0 assets still record provenance.

## Collection

Respect `robots.txt` for automated fetching. Do not circumvent paywalls, logins, or rate
limits. Do not scrape a site wholesale: sourcebook is for a working set of sources a person
could reasonably have read. Record `retrieved_at` on everything.

## Publication defaults

An artifact containing third-party excerpts ships with
`<meta name="robots" content="noindex">` unless the user removes it deliberately. The default
is a private reading artifact, not a competing publication.

Every artifact renders a footer line naming sourcebook, the build date, and the source count.
That is provenance, not branding. It may be styled. It may not be removed.
