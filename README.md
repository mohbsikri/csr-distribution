# CSR — Cognitive Specification Runtime (distribution publique)

**Version produit :** 1.0.1 · **Version runtime :** 2.8.21  
**Dépôt :** https://github.com/mohbsikri/csr-distribution — lecture publique, aucune invitation ni authentification Git nécessaire.

> Fichier généré par `build_public.py` (dépôt source). Ne pas l'éditer ici. Licence : MIT ([`LICENSE`](LICENSE)) ; composants tiers : [`NOTICE.md`](NOTICE.md).

CSR transforme des connaissances fragmentées en spécifications validées et maintenables. Il s'installe comme plugin **Claude Code local** (application ou terminal ; pas la version web).

## Démarrer en une phrase

1. Dans PowerShell : `claude --permission-mode auto --effort low`
2. Collez dans Claude Code :

```
Installe CSR pour moi en suivant https://github.com/mohbsikri/csr-distribution/blob/main/docs/onboarding/prompt-demarrage.md (section « Prompt à copier ») ; si la page est illisible, utilise https://raw.githubusercontent.com/mohbsikri/csr-distribution/main/docs/onboarding/prompt-demarrage.md
```

Claude vous propose le dossier `Documents\CSR` (ou un espace CSR existant s'il en trouve un), accepte un autre chemin, montre une fois les actions prévues, attend votre accord, installe, vérifie le commit installé, initialise le dossier sans rien écraser, puis vous dit comment ouvrir César.

Ensuite, dans une **nouvelle** session lancée depuis ce dossier : `/cognitive-specification-runtime:csr`

## Installation manuelle

```powershell
claude plugin marketplace add "https://github.com/mohbsikri/csr-distribution.git" --scope user
claude plugin install cognitive-specification-runtime@csr-private --scope user
claude plugin list
```

L'identité du plugin (`cognitive-specification-runtime@csr-private`) est celle des installations pilotes existantes : mêmes commandes, aucun doublon. Vous avez déjà une installation pilote (source privée) ? Elle continue de fonctionner ; pour passer à cette source publique, suivez « Passer de la source pilote à la source publique » dans [`docs/onboarding/guide-demarrage.md`](docs/onboarding/guide-demarrage.md). Rien n'est migré automatiquement.

Mise à jour : `claude plugin marketplace update csr-private` puis `claude plugin update cognitive-specification-runtime@csr-private --scope user`, puis relancez Claude Code.

## Documents

| Document | Rôle |
|---|---|
| [`docs/onboarding/prompt-demarrage.md`](docs/onboarding/prompt-demarrage.md) | Procédure exécutée par Claude : diagnostic, installation, provenance, initialisation |
| [`docs/onboarding/guide-demarrage.md`](docs/onboarding/guide-demarrage.md) | Guide : prérequis, dossier de travail, mise à jour, migration, dépannage |
| [`LICENSE`](LICENSE) | Licence MIT du code et de la documentation CSR |
| [`NOTICE.md`](NOTICE.md) | Portée de la licence et composants tiers (Mermaid, MIT) |
