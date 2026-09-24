# Panel of three blind auditors (before code on a new scheme)

**A new scheme - a flow that moves money or documents, a migration, an
integration - gets a panel of three blind auditors BEFORE code.** Three
models x three lenses (`auditor-money` / `auditor-failures` /
`auditor-definitions`, launched with `/audit <path to the design document>`);
each reads the document and the repository ITSELF - a retelling by the
author is forbidden. A finding shared by 2+ auditors is fixed without
discussion; a finding by one is checked by hand first. Auditors
contradicting each other go into a separate section. Planning, auditing and
execution are done by DIFFERENT sessions.

Do not run it on point fixes: the panel is for schemes and flows where a
mistake costs a rewrite (roughly 350k tokens per run); small changes are
covered by tests, the linter and ordinary review.

Mechanics that hold this rule (`tests/test_toolkit_config.py`): the three
agents exist, their tools are read-only (the right to write is the end of an
audit), and their models are all different - one model three times is an
echo, not a panel.
