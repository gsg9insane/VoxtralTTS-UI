# PREMIUM UI

This folder contains the second interface pass for VoxtralTTS-UI, kept separate from the standard desktop layout.

## What Changes

- a compact premium hero with quick actions
- runtime, voice, export, and reference status cards
- a more production-oriented shell around the same synthesis engine
- renamed tabs: `Composer`, `Clone Lab`, and `Engine Room`
- resizable panels and remembered layout state

## What Stays The Same

- the same Voxtral client and runtime integration
- the same local and remote generation flow
- the same project data and configuration model

## Launch

```powershell
python PREMIUM\premium_app.py
```

or:

```powershell
scripts\setup_and_run.ps1 -Mode premium
```
