---
title: Deadwax
emoji: 💿
colorFrom: yellow
colorTo: gray
sdk: gradio
sdk_version: 6.31.0
python_version: "3.13"
app_file: app.py
pinned: true
license: mit
short_description: An AI music librarian whose model never does the maths
---

# Deadwax

An AI librarian for a music collection. Ask it about the library in plain English, or ask for
a playlist to a brief. The language model reads the question and writes the reply; every
count, total and playlist check is computed in plain Python, and each answer shows the tool
calls behind it.

This Space runs on a fixed library of 100 tracks, the same data the project's evaluation
suite is graded against. Source code, evaluation results and the setup guide for running it
against your own Spotify library: [github.com/TheDavidKoen/deadwax](https://github.com/TheDavidKoen/deadwax).

This folder is deployed automatically from the repository's `main` branch after CI passes.
Edit it there, not on the Space.
