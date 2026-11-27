# Guide de démarrage CSR (distribution publique)

> Chemin recommandé : la phrase ou le prompt de `prompt-demarrage.md` (même dossier). Ce guide détaille les étapes, la mise à jour et le passage depuis une installation pilote.
>
> Source stable : `https://github.com/mohbsikri/csr-distribution.git` (branche `main`), dépôt public. Produit 1.0.1, runtime 2.8.21.

## Prérequis

| Élément | Contrôle |
|---|---|
| Claude Code **local**, connecté | `claude --version` |
| Git | `git --version` |
| Accès réseau à github.com | `git ls-remote https://github.com/mohbsikri/csr-distribution.git HEAD` répond `<commit>  HEAD` |

Aucun compte GitHub, aucune invitation, aucune authentification Git.

## Lancer Claude Code pour CSR

| Où | Quoi taper |
|---|---|
| **PowerShell** | `Set-Location -LiteralPath "<dossier de travail>"` puis `claude --permission-mode auto --effort low` |
| **Dans Claude Code** | `/cognitive-specification-runtime:csr` (démarre César) |

Mode auto indisponible sur votre compte ou version : lancez `claude --effort low` ; les accords demandés par César restent identiques dans tous les modes.

## Dossier de travail

Par défaut, Claude propose `Documents\CSR`, résolu par `[Environment]::GetFolderPath('MyDocuments')` (le vrai dossier Documents, y compris s'il est redirigé vers OneDrive). S'il trouve déjà un espace CSR (fichier `runtime\workspaces.md`) dans le dossier courant ou dans `Documents\CSR`, il propose celui-là et aucun autre. Vous pouvez toujours indiquer un autre chemin. L'initialisation (`csr-init.ps1`) ne réécrit jamais un registre existant.

## Installation manuelle

```powershell
claude plugin marketplace add "https://github.com/mohbsikri/csr-distribution.git" --scope user
claude plugin install cognitive-specification-runtime@csr-private --scope user
claude plugin list
```

Puis initialisez le dossier (`<installPath>` = valeur de `installed_plugins.json`, entrée `cognitive-specification-runtime@csr-private`) :

```powershell
powershell -NoProfile -File "<installPath>\tools\csr-init\csr-init.ps1" -WorkDir "<dossier de travail>"
```

## Mise à jour

```powershell
claude plugin marketplace update csr-private
claude plugin update cognitive-specification-runtime@csr-private --scope user
```

Puis quittez et relancez Claude Code.

## Passer de la source pilote à la source publique

Les installations pilotes (source privée, identité `cognitive-specification-runtime@csr-private`) **continuent de fonctionner** sans rien faire. Rien n'est migré automatiquement : la procédure ci-dessous est à lancer vous-même, quand vous le décidez. Le nom de la marketplace (`csr-private`) et celui du plugin restent les mêmes : mêmes commandes, pas de doublon.

Vos projets vivent dans votre dossier de travail, pas dans le plugin : cette procédure n'y touche pas.

```powershell
claude plugin marketplace remove csr-private
claude plugin marketplace add "https://github.com/mohbsikri/csr-distribution.git" --scope user
claude plugin install cognitive-specification-runtime@csr-private --scope user
claude plugin list
```

`marketplace remove` retire aussi le plugin installé depuis cette source : c'est pourquoi `install` suit immédiatement. Contrôle : `claude plugin marketplace list` affiche la source `csr-distribution`, et `/cognitive-specification-runtime:csr` retrouve vos projets dans votre dossier de travail.

N'ajoutez pas la source publique sous un **autre** nom de marketplace à côté de l'ancienne : vous auriez deux copies du même plugin et des commandes en double.

## Séparation plugin / projet

| Dans le plugin (lecture seule) | Dans votre dossier de travail |
|---|---|
| `commands/`, `docs/`, `templates/`, `tools/` | `workspaces/<id>/`, `runtime/workspaces.md`, `runtime/current_workspace.md` |

Désinstaller ou réinstaller le plugin ne touche pas à vos projets.

## Après initialisation

Demandez à César de créer un projet : il propose un identifiant, attend votre accord et l'enregistre en pause. L'activation est une étape distincte, sur votre accord. Il vous invite ensuite à indiquer votre premier fichier source.

## Dépannage concis

| Symptôme | Cause probable | Action |
|---|---|---|
| `git ls-remote` → `getaddrinfo` ou délai dépassé | Réseau, proxy ou DNS | Vérifier l'accès à github.com, réessayer |
| `marketplace add` → nom déjà utilisé | Une marketplace `csr-private` existe (installation pilote) | Section « Passer de la source pilote à la source publique » |
| `/cognitive-specification-runtime:csr` inconnu | Session ouverte avant l'installation, ou autre profil Claude | Quitter (`/exit`) et relancer depuis le même terminal |
| `csr-init` affiche `[FAIL]` | Prérequis manquant ou registre illisible | Lire la ligne `[FAIL]` ; ne jamais supprimer `runtime\workspaces.md` |

## Désinstallation

```powershell
claude plugin uninstall cognitive-specification-runtime@csr-private --scope user
```

Vos dossiers de travail restent intacts.
