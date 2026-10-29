# CBXY 0.1.0 conformance examples

These fixtures document how an independent CBXY reader should interpret the format.

Run the standard-library-only fixture check:

```sh
python3 conformance/check.py
```

The script builds real CBZ and CBXY archives in a temporary folder and checks their ZIP entries and JSON. It does not run a third-party reader or certify a complete implementation.

| Scenario | Expected behavior |
| --- | --- |
| Normal sidecar | Read two panels in listed order |
| Nested page path | Match Art/page-003.png with Art/page-003.json |
| Unknown JSON field | Ignore the unknown field |
| Empty panels array | Use page-level viewing |
| Missing page JSON entry | Use page-level viewing for that page |
| Missing sidecar | Continue reading normal pages |
| Out-of-bounds panel | Producer SHOULD avoid it; consumer MAY clamp |
| Backslash in ZIP entry name | Producer violates the forward-slash MUST rule |

The last two are guidance examples, not required consumer rejection tests. The specification is in [spec/v0.1.0.md](../spec/v0.1.0.md).
