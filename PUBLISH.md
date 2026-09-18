# Publishing this repo

The token available to the Cowork session is **repository-scoped and cannot
create repositories** (`/user/repos` returns *"sessions are bound to their
configured repositories"*), so the repo has to be created by you. Everything
else is ready in this folder.

## 1. Create the repo and push

With the GitHub CLI:

```bash
cd ~/Developer/lithuanian_anki_project/site
git init -b main
git add .
git commit -m "Lithuanian A2 deck: landing page and README"
gh repo create elatier/lithuanian-a2-anki --public --source=. --push
```

Without `gh` — create an empty **public** repo named `lithuanian-a2-anki` at
<https://github.com/new> (no README, no .gitignore, no licence), then:

```bash
cd ~/Developer/lithuanian_anki_project/site
git init -b main
git add .
git commit -m "Lithuanian A2 deck: landing page and README"
git remote add origin https://github.com/elatier/lithuanian-a2-anki.git
git push -u origin main
```

## 2. Turn on Pages

Repo → **Settings → Pages** → Source: *Deploy from a branch* → Branch `main`,
folder **`/docs`** → Save.

The site appears at <https://elatier.github.io/lithuanian-a2-anki/> within a
minute or two.

## 3. Attach the deck as a Release

GitHub **blocks any file over 100 MiB inside a repo**, and the deck is 116 MB,
so it cannot be committed or served from Pages. Release assets allow up to 2 GB
on a free plan, which is where the download button points.

`decks/lietuviu_A2.apkg` was **verified current** on 18 Sep by opening the
package and reading its database: 1,593 notes, 3,186 cards, 6,372 media files,
Charter styling and the dark-mode block present, and the six new pronoun cards
(`tas`, `šis`, `kuris`, `kas`, `savo`, `jos`) plus the `jie | jos` table all
inside. No rebuild is needed.

```bash
gh release create v1.0.0 decks/lietuviu_A2.apkg \
  --repo elatier/lithuanian-a2-anki \
  --title "Lietuvių A2 — 1,593 words" \
  --notes "1,593 words, 3,186 cards, 6,372 recordings, 18 themes."
```

Or drag the `.apkg` onto **Releases → Draft a new release** in the browser.

## 4. AnkiWeb

Sharing on AnkiWeb is not an `.apkg` upload. Per the Anki manual you sync the
deck to AnkiWeb from your own collection, then log in and choose **Share** from
the menu next to that deck. Limits worth knowing:

- sync: 100 MB compressed / 250 MB uncompressed
- individual media file: 100 MB
- the Share form states a 250 MB limit; this deck is 116 MB

The field values to paste — title, tags, description — are in
`../ANKIWEB_SHARE.md`.
