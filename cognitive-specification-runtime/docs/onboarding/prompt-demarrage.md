# Prompt de démarrage CSR (distribution publique)

## Le plus simple : une phrase

Dans une session **Claude Code locale** (PowerShell : `claude --permission-mode auto --effort low`), collez :

```
Installe CSR pour moi en suivant https://github.com/mohbsikri/csr-distribution/blob/main/docs/onboarding/prompt-demarrage.md (section « Prompt à copier ») ; si la page est illisible, utilise https://raw.githubusercontent.com/mohbsikri/csr-distribution/main/docs/onboarding/prompt-demarrage.md
```

Si Claude ne peut lire aucune des deux adresses (accès web désactivé), il peut récupérer le texte en PowerShell : `Invoke-RestMethod https://raw.githubusercontent.com/mohbsikri/csr-distribution/main/docs/onboarding/prompt-demarrage.md`. Vous pouvez aussi copier directement le bloc ci-dessous.

**Prérequis :** Claude Code installé et connecté ; Git installé. Aucun compte GitHub, aucune invitation, aucune authentification Git : le dépôt est public.

---

## Prompt à copier (version stable)

```
Installe et prépare le Cognitive Specification Runtime (CSR) pour moi.

DOSSIER DE TRAVAIL : (si je ne l'ai pas indiqué ici, applique l'étape 0)
SOURCE : https://github.com/mohbsikri/csr-distribution.git
MARKETPLACE : csr-private
PLUGIN : cognitive-specification-runtime@csr-private

Règles pour toute la procédure :
- Exécute les commandes une par une avec l'outil PowerShell et contrôle chaque code retour ($LASTEXITCODE) et chaque sortie.
- Ne masque aucune erreur : pas de 2>$null, pas de Out-Null sur une commande d'installation, pas de -ErrorAction SilentlyContinue.
- À la première erreur : montre-moi la commande, sa sortie exacte, explique en une phrase, et ARRÊTE-TOI. Ne tente pas de contournement.
- Ne modifie aucun paramètre système, aucune politique d'exécution, aucun réglage d'organisation, aucun autre plugin ou marketplace. Ne crée aucun projet. N'utilise jamais bypassPermissions. Ne me demande aucun secret ni jeton.
- Respecte les demandes d'autorisation natives de Claude Code ; ne prétends pas pouvoir modifier les réglages de la session en cours.

0. DOSSIER ET PLAN (lecture seule, avant toute écriture)
   - Si DOSSIER DE TRAVAIL n'est pas renseigné, cherche un espace CSR existant (présence de runtime\workspaces.md) :
     a) dans le dossier courant ;
     b) dans "<Documents>\CSR", où <Documents> = [Environment]::GetFolderPath('MyDocuments') (dossier Documents réel, redirection OneDrive comprise).
     Si un espace existe : propose-le (il sera conservé tel quel) et ne propose AUCUN autre dossier par défaut.
     Sinon : propose "<Documents>\CSR" (à créer).
     Pose une seule question : « J'utilise <chemin> ? Répondez oui, ou indiquez un autre chemin. » Le chemin peut contenir des espaces et ne pas exister.
   - Fais le DIAGNOSTIC (étape 1), puis montre-moi en une fois : première installation ou mise à jour, les commandes prévues (étapes 2 à 4) et le dossier visé. Attends mon accord.
   - Prérequis manquant (Claude Code, Git) : explique ce qui manque et donne la procédure officielle (Git : https://git-scm.com/download/win ; Claude Code : https://docs.claude.com/fr/docs/claude-code/setup). N'installe rien sans mon accord explicite ; sinon arrête-toi.

1. DIAGNOSTIC
   - claude --version et git --version.
   - Profil Claude effectif : si $env:CLAUDE_CONFIG_DIR est défini, c'est lui ; sinon "$env:USERPROFILE\.claude". Affiche-le.
     Toutes les commandes claude de cette procédure s'appliquent à ce profil.
   - claude plugin marketplace list et claude plugin list : indique si la marketplace csr-private et le plugin CSR existent déjà, et avec quelle source.
   - Accès au dépôt : git ls-remote <URL de SOURCE sans la partie #...> <branche après # si présente, sinon HEAD>.
     Note le commit obtenu (COMMIT_ATTENDU). Échec = problème réseau : arrête-toi.

2. INSTALLATION
   - Si la marketplace csr-private n'existe pas : claude plugin marketplace add "<SOURCE>" --scope user
   - Si elle existe déjà avec exactement la même source : claude plugin marketplace update csr-private
   - Si elle existe avec une AUTRE source (par exemple l'ancienne source pilote privée) : ne la modifie pas. Dis-moi que l'installation existante continue de fonctionner, renvoie-moi à la section « Passer de la source pilote à la source publique » de docs/onboarding/guide-demarrage.md, et arrête-toi.
   - Si le plugin n'est pas installé : claude plugin install cognitive-specification-runtime@csr-private --scope user
     Sinon : claude plugin update cognitive-specification-runtime@csr-private --scope user
   - Vérifie avec claude plugin list que le plugin apparaît, activé.

3. PROVENANCE
   - Lis <profil effectif>\plugins\installed_plugins.json, entrée "cognitive-specification-runtime@csr-private".
   - Affiche version, gitCommitSha et installPath.
   - gitCommitSha doit être égal à COMMIT_ATTENDU, et installPath doit exister et contenir tools\csr-init\csr-init.ps1. Sinon arrête-toi.

4. INITIALISATION DU DOSSIER DE TRAVAIL
   - Diagnostic : powershell -NoProfile -File "<installPath>\tools\csr-init\csr-init.ps1" -WorkDir "<DOSSIER DE TRAVAIL>" -DiagOnly
   - Si un [FAIL] apparaît : montre-le et arrête-toi (un registre absent ou illisible alors que des projets existent ne doit jamais être réinitialisé).
   - Sinon : powershell -NoProfile -File "<installPath>\tools\csr-init\csr-init.ps1" -WorkDir "<DOSSIER DE TRAVAIL>"
   - Code retour différent de 0 : montre la sortie et arrête-toi. Un espace existant est conservé (« deja present »).

5. FIN
   Résume en un tableau : profil effectif, version, commit, installPath, dossier, résultat de l'initialisation.
   Puis dis-moi exactement, en séparant les deux endroits :
   le plugin n'est pas chargé dans la session actuelle. Quittez-la (/exit), puis
   - dans PowerShell (même profil Claude) :
       Set-Location -LiteralPath "<DOSSIER DE TRAVAIL>"
       claude --permission-mode auto --effort low
   - dans Claude Code : /cognitive-specification-runtime:csr
   César vous accueillera. Ces options se choisissent au lancement : je ne peux pas les appliquer à la session actuelle.
```

---

## Notes

- La commande de César est `/cognitive-specification-runtime:csr` : Claude Code préfixe toujours les commandes d'un plugin par son nom ; il n'existe pas d'alias officiel `/csr`.
- Créer un projet : demandez-le à César (commande officielle `workspace-lifecycle CREATE`, projet en pause). L'activer est un acte distinct, sur votre accord (`SWITCH`).
- Profil Claude séparé (`$env:CLAUDE_CONFIG_DIR`) : ouvrez la nouvelle session depuis le même terminal.
- Ce prompt ne fonctionne pas dans la session web claude.ai : il exécute des commandes locales.
