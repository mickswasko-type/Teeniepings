# Teenieping Catcher

Teenieping Catcher is a small, static, child-friendly web app with a Teenieping handbook and a guess-the-Teenieping quiz. It is made with plain HTML, CSS, JavaScript, and local image assets. No npm, build step, server, database, or framework is required.

## Run Locally

Open `index.html` in a browser, or run a simple static server from this folder:

```sh
python3 -m http.server 8000
```

Then visit `http://localhost:8000/`.

## Enable GitHub Pages

In GitHub, go to:

Settings -> Pages -> Deploy from a branch -> main -> /(root) -> Save

The public URL will use this format:

```text
https://USERNAME.github.io/REPOSITORY-NAME/
```

For this repository, that should be:

```text
https://mickswasko-type.github.io/Teeniepings/
```

## Add Or Replace A Character Image

1. Add the image file to the `images/` folder.
2. Use a relative path from `index.html`, such as `images/Heartsping.webp`.
3. Match capitalization exactly. GitHub Pages paths are case-sensitive.
4. Update the `IMAGE_MANIFEST` object in `index.html` so the character name points to the image path.

If a character does not have an entry in `IMAGE_MANIFEST`, the app keeps the existing emoji badge.
