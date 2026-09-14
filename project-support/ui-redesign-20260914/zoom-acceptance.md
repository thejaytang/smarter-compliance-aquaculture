# Actual browser zoom acceptance

2026-09-14, isolated candidate at http://127.0.0.1:60515/, Chrome tab 354552464. No normal business changes.

PASS: native Chrome accessibility explicitly displayed 200% on the selected workbench tab. The viewport was 735 x 389 CSS px with devicePixelRatio 4; restored 100% was 1470 x 779 with devicePixelRatio 2. No viewport override substituted for browser zoom. An initial shortcut targeted the previous GitHub tab; its zoom was immediately reset to 100% before selecting the test tab and repeating the check correctly.

TS001 personal revision 4 opened in Material review. Global and task bars remained visible, including Save and Archive. All three panes retained the same y=90.6953 and height=298.8047 CSS px. The horizontal workspace was 980 px in a 735 px viewport. ArrowRight on the original separator changed its width to 367.8164 px; ArrowLeft on the Requirements separator increased the right pane to 241.7031 px. Repeated region ArrowRight moved scrollLeft to the maximum 245 px, preserving the three-pane layout. No pane tabs or vertical stacking appeared.

Save displayed a pending request, then reopening TS001 showed personal revision 5, Saved, still a content draft. There was an unexpected intervening transition to Source review history; its cause was not established, so this observation does not prove uninterrupted route retention through save. Saved content was recovered by returning to Materials.

Archive opened TS002 at finalized revision 2, explicitly Content finalized / Requirements unfinished. It retained the shared three-pane reader and Create revision, with no visible Save action. All panes shared y=90.6953, height=293.3047; widths were 367.8164 / 356.4805 / 241.7031 px. Original spreadsheet and archived content remained visible in their own panes. No archive mutation was made.

Native Chrome was restored to 100%, confirmed both by its accessibility label and viewport/DPR. Existing 1280/1440/1920 tests, owning-state regression and archive/inspection workflow evidence retain their earlier scope. This check closes the locked-Mac zoom blocker, but does not prove a connected automatic discovery provider.

A controlled follow-up save at restored 100% completed as personal revision 6 while remaining on the same TS001 Material review route, explicitly reporting that saving does not confirm content. The earlier intervening transition did not recur; no product cause is established.
