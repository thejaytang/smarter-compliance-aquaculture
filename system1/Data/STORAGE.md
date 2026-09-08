# System1 source storage

This is a storage reference. Daily human reviews and authorised replacements are handled in the [browser workbench](../../workbench/USER_GUIDE.md). Project entry and maintenance guidance: [System1 guide](../USER_GUIDE.md).

Current valid original-format files live directly in the `folder_code` directory mapped from `source_family`. Filenames begin with `snapshot_id_`. The folder represents the organisation responsible for the content, not the channel through which the copy was obtained; an OEM manual supplied by a client still belongs in the manufacturer/supplier folder, with the channel recorded separately.

The updater preserves replaced originals under `<folder_code>/_archive/<source_id>/`. Preserve published format and authoritative language. System1 retrieval/storage supports PDF, HTML, XLSX and ZIP. Do not convert a source merely for convenience or overwrite a current original by hand.

`00_Human_Intake` is a maintainer-assisted intake folder for authorised, unregistered files. Intake scanning proposes metadata and a named-human acceptance task; a formal source is created only after ACCEPT. The dedicated browser candidate form is not yet connected. Routine intake is an advanced maintainer operation, not a program the reviewer must run after every browser decision.

For an existing source's missing or replacement original, use the workbench's file chooser and required format and human confirmation checks. The program applies the normal snapshot, hash, provenance and audit rules. A failed replacement preserves the valid current file. `Human Operation Desktop` remains hidden adapter staging and history, not an Excel editing surface; do not edit `Source Register` directly.
