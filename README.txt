TEENIEPING CATCHER — COMPLETE IMAGE-FALLBACK BUILD

Upload index.html to the same GitHub Pages repository as before.

This version:
- keeps all existing verified image URLs
- adds image URLs for the remaining 48 entries
- tries a local images/Name.png file first
- then tries the supplied remote render
- then tries common Fandom render filename variations automatically

An internet connection is required for remote images. For a fully offline version, run get-images.py to create an images folder, then upload that folder beside index.html.
