# Workbench startup recovery, 2026-09-16

Chrome stayed at Loading workbench. The normal service responded to health and state requests, but returned HTTP 404 for `/site-catalog.js`. Current `global-settings.js` imports this module; the loaded parent server predated its static route. Runtime evidence reported changed parent source files. The import failure prevented application initialization.

Controlled restart loaded the current code. Eight owning databases were copied under quiescence; every existing table was unchanged after activation and foreign-key checks passed. `site-catalog.js` now returns 200 with text/javascript; served asset bytes match source and parent source changes are empty. Automation remained disabled and shared AI stayed Not connected. See `activation.json` and `activation-backup/manifest.json`. Ten isolated continuity/catalog tests passed in `catalog-tests.log`.

Chrome's original tab was reloaded and now renders PA004 and all four panes. It recovered a previously retained browser-local draft against saved personal revision 10 and shows a newer-saved-revision comparison notice. That draft was neither cleared nor saved over the database. Browser-extension listener errors remain in the console, but do not prevent the recovered workbench from rendering. No production code edits were necessary.
