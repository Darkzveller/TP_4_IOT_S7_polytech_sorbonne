# TP4 IoT — Tracker par Wi-Fi Sniffing

Projet réalisé dans le cadre du TP4 IoT (S7) à Polytech Sorbonne.

L'objectif est de récupérer des informations sur les réseaux Wi-Fi visibles (SSID, BSSID, RSSI), d'en déduire une position approximative et de conserver l'historique des déplacements d'un tracker.

**Choix actuel :** on laisse de côté l'ESP32 et LoRaWAN. Le serveur est développé avec **FastAPI**, il tourne **en local sur mon PC Windows** et utilise **SQLite**. Le site contient maintenant une **carte OpenStreetMap interactive**, sur laquelle je peux placer mes points d'accès et consulter les trajets estimés à partir des scans Wi-Fi.

## 1. Avancement du projet — 9 novembre 2026

| Élément | État | Commentaire |
| --- | --- | --- |
| Environnement Python 3.11 | OK | Environnement `py3.11` créé par le Makefile |
| Installation des dépendances | OK | `fastapi` et `uvicorn` installés |
| Démarrage manuel de FastAPI | OK | Uvicorn a affiché `Application startup complete.` |
| Démarrage avec `make run` | À revalider | Le Makefile d'origine lançait `src/main.py` sans démarrer Uvicorn |
| Configuration générique du Makefile | Préparée | Utilisation possible d'un `Makefile.project` propre au TP |
| Routes API et SQLite | Implémentées et testées sur une copie du projet | À vérifier ensuite sur mon PC Windows |
| Carte de France OpenStreetMap / Leaflet | Développée | Ajouter, déplacer, modifier et supprimer des points d’accès |
| Migration de l’ancienne base SQLite | Testée | Les coordonnées historiques X/Y sont conservées |
| Envoi de scans simulés | Testé sur la version fournie | 7 nouvelles positions GPS calculées ; à reproduire sur Windows |
| Relevés Wi-Fi du PC Windows | Script disponible | Test matériel/Windows restant à faire |
| Référencement des bornes du campus | À faire | BSSID et coordonnées réelles à collecter |
| Vérification de la précision | À faire | Les valeurs RSSI devront être calibrées |

**Dernier test effectué :**

```powershell
.\py3.11\Scripts\python.exe -m uvicorn main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Résultat observé :

```text
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.
```

Ce message confirme le **démarrage du serveur**. En complément, **3 tests automatisés** ont réussi sur la version fournie : anciennes coordonnées X/Y, nouveaux points GPS, compatibilité SQLite. La démo a aussi envoyé **7 scans** donnant **7 positions géographiques** ; ces vérifications restent à reproduire sur mon PC Windows.

## 2. Organisation des fichiers

```text
TP_4_IOT_S7_polytech_sorbonne/
├── Makefile                    # Gestion générique des environnements Python
├── Makefile.project            # Lancement Uvicorn propre à ce TP
├── requirements.txt           # Dépendances du serveur
├── README.md
├── .make-python-version        # Version Python mémorisée par le Makefile
├── py3.11/                     # Environnement virtuel généré localement
└── src/
    ├── main.py                # Application FastAPI et base SQLite
    ├── demo.py                # Envoi de scans fictifs
    ├── tracker_windows.py     # Scan Wi-Fi depuis Windows (facultatif)
    ├── test_api.py            # Tests automatiques (dépendances de test à installer)
    └── static/
        └── index.html         # Carte de France et gestion des points d’accès
```

`Makefile.project` est fourni dans l’archive complète ; dans mon dépôt d’origine, il n’est présent que si j’ai ajouté la configuration proposée. Le fichier `tracker.sqlite3` est créé dans `src/` lors du démarrage de l'application. Si une ancienne base existe déjà, le serveur ajoute les colonnes latitude et longitude sans effacer les scans et positions X/Y historiques. Il est néanmoins conseillé de faire une copie de la base avant de tester un changement de version.

## 3. Installation sous Windows

Se placer à la racine du projet dans **PowerShell**, puis vérifier la configuration :

```powershell
make info
```

Pour créer l'environnement Python 3.11 et installer les dépendances :

```powershell
make setup PY=3.11
```

On peut aussi utiliser `make install` pour installer les dépendances ou `make list-python` pour afficher les versions disponibles.

Le Makefile utilise directement le Python de `py3.11`. **Il n'est pas nécessaire d'activer l'environnement virtuel dans le terminal** pour utiliser `make run` ou les commandes explicites avec `py3.11\Scripts\python.exe`.

## 4. Lancer le serveur FastAPI

### Méthode déjà vérifiée : commande directe

À la racine du projet :

```powershell
.\py3.11\Scripts\python.exe -m uvicorn main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

- `main:app` : objet FastAPI `app` défini dans `main.py`.
- `--app-dir src` : indique qu'il faut chercher le module dans `src/`.
- `--host 127.0.0.1` : accès depuis le PC uniquement.
- `--port 8000` : port HTTP utilisé.
- `--reload` : redémarrage automatique après modification du code (développement).

Le terminal reste occupé pendant que le serveur fonctionne. Pour l'arrêter, faire **`Ctrl + C`**.

### Méthode avec le Makefile générique

Le but du Makefile est de fonctionner avec **tous les projets Python**, pas uniquement FastAPI. On garde donc `make run` générique et on personnalise uniquement la commande de ce projet.

Avec la version générique du Makefile préparée précédemment, créer à la racine un fichier `Makefile.project` contenant :

```makefile
RUN_CMD = "$(VENV_PYTHON)" -m uvicorn main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Puis démarrer le serveur :

```powershell
make run
```

**Important :** cette commande ne démarrera FastAPI de cette manière que si le **Makefile générique mis à jour** est utilisé et qu'il charge `Makefile.project`. Le Makefile d'origine exécutait seulement `python src/main.py`, puis rendait la main au terminal.

Dans un autre projet Python classique, sans `Makefile.project`, `make run` continue à lancer le script configuré par `SRC`.

## 5. Accéder au serveur

Une fois Uvicorn démarré :

| Adresse | Utilité |
| --- | --- |
| <http://127.0.0.1:8000/docs> | Documentation interactive des routes REST |
| <http://127.0.0.1:8000/health> | Vérification de l'état du serveur |
| <http://127.0.0.1:8000/map> | Interface web avec les positions et les trajets |

Pour un premier contrôle, ouvrir `/docs`, puis essayer **GET `/health`** avec le bouton *Try it out* et *Execute*. La réponse attendue est du type :

```json
{"status": "ok", "database": "tracker.sqlite3"}
```

## 6. Fonctionnement des étapes du TP

### Étape 1 — Recevoir les données Wi-Fi

La route **POST `/scans`** permet d'envoyer les informations d'un tracker :

```json
{
  "tracker_id": "pc-01",
  "readings": [
    {"ssid": "Reseau_A", "bssid": "AA:BB:CC:DD:EE:01", "rssi": -51},
    {"ssid": "Reseau_B", "bssid": "AA:BB:CC:DD:EE:02", "rssi": -68}
  ]
}
```

- **SSID** : nom du réseau Wi-Fi.
- **BSSID** : identifiant du point d'accès Wi-Fi.
- **RSSI** : niveau du signal reçu, exprimé ici en dBm ou estimé à partir des informations de Windows.

L'API enregistre les relevés avec un identifiant de scan et un horodatage. Un scan peut être enregistré même si les points d'accès ne sont pas encore connus dans la base.

### Étape 2 — Référencer les points d'accès sur la carte

La page **`http://127.0.0.1:8000/map`** utilise **Leaflet 1.9.4** avec un fond **OpenStreetMap**.

1. Utiliser la barre **« Rechercher un lieu en France »**, par exemple `4 place Jussieu, Paris`, puis cliquer sur **Rechercher** (ou appuyer sur Entrée).
2. Choisir le bon résultat dans la liste : la carte se centre sur le lieu et les champs latitude/longitude se remplissent. On peut aussi utiliser le menu « Aller à » ou cliquer directement sur la carte pour ajuster la position.
3. Renseigner le SSID et surtout le **BSSID** de la borne Wi-Fi.
4. Cliquer sur **Enregistrer** : `POST /access-points` stocke le point dans SQLite.
5. Cliquer sur un marqueur orange (ou sur son nom dans la liste) pour le modifier.
6. Pour changer sa position, cliquer ailleurs sur la carte ou **glisser le marqueur** ; cliquer ensuite sur Enregistrer.
7. Pour retirer une borne, choisir le point et cliquer sur Supprimer.

Exemple du **nouveau format GPS** pour l'API `POST /access-points` :

```json
{
  "bssid": "AA:BB:CC:DD:EE:01",
  "ssid": "Reseau_A",
  "latitude": 48.847,
  "longitude": 2.3571
}
```

L'API accepte toujours **l'ancien format X/Y en mètres** pour conserver la compatibilité :

```json
{
  "bssid": "AA:BB:CC:DD:EE:02",
  "ssid": "Reseau_B",
  "x": 5.0,
  "y": 12.0
}
```

**Important :** une borne en X/Y local reste conservée dans SQLite, mais ne peut pas apparaître sur une carte GPS avant d'avoir été géoréférencée. On peut la sélectionner dans la liste du site, puis lui attribuer un emplacement GPS.

Le serveur estime la position du tracker par **barycentre pondéré à partir des RSSI**. Si des BSSID géoréférencés sont reconnus dans un scan, la nouvelle position comporte aussi latitude/longitude, ce qui permet de tracer le déplacement sur OpenStreetMap. Les BSSID connus uniquement en X/Y ne sont pas mélangés à ceux placés géographiquement. Ce calcul demeure une **approximation pédagogique** ; la latitude/longitude est **estimée** à partir des bornes et n'est pas du GPS mesuré.

### Étape 3 — Stocker l'historique

Les données sont enregistrées dans SQLite avec les tables suivantes :

- `access_points` : les BSSID, SSID, coordonnées `x/y` et éventuelles `latitude/longitude`.
- `scans` : l'identifiant du tracker et la date du relevé.
- `observations` : les SSID, BSSID et RSSI mesurés pendant chaque scan.
- `positions` : les positions estimées (`x/y`, éventuellement `latitude/longitude`) associées au tracker et à la date.

Principales routes de consultation :

| Méthode | Route | Utilité |
| --- | --- | --- |
| GET | `/access-points` | Liste des points d'accès, dont les coordonnées GPS si connues |
| POST | `/access-points` | Ajouter ou mettre à jour un point d'accès sur la carte |
| DELETE | `/access-points/{bssid}` | Supprimer un point d'accès |
| POST | `/scans` | Enregistrer un scan et calculer une position si possible |
| GET | `/scans` | Lister les scans |
| GET | `/scans/{scan_id}` | Détails d'un scan |
| GET | `/trackers` | Liste des trackers |
| GET | `/trackers/{tracker_id}/positions` | Historique des positions |
| GET | `/trackers/{tracker_id}/positions?start=2026-11-09T14:00:00Z&end=2026-11-09T17:00:00Z` | Historique sur une période |

### Étape 4 — Afficher les positions sur une vraie carte

La page `/map` permet maintenant de :

- afficher **la carte de la France** et zoomer jusqu'au campus ;
- voir les points d'accès géolocalisés en **orange** ;
- afficher la **trajectoire estimée** en bleu et la dernière position en vert ;
- choisir le tracker et limiter l'affichage à une période ;
- enregistrer ou déplacer les bornes directement depuis le site ;
- voir le nombre de points X/Y historiques qui n'ont pas encore de coordonnées GPS.

La barre de recherche utilise **Nominatim**, le géocodeur public d'OpenStreetMap, pour convertir une ville ou une adresse en coordonnées. Elle lance une requête **uniquement après un clic sur Rechercher** (aucune recherche à chaque frappe), affiche jusqu'à 5 correspondances, conserve temporairement en mémoire les résultats et respecte un intervalle entre les appels depuis ce navigateur. Les recherches tapées sont envoyées au service externe Nominatim : évitez d'y saisir des informations privées. La carte se centre sur le résultat choisi et préremplit les coordonnées, mais **n'enregistre aucune borne automatiquement** : il faut ajouter le BSSID puis cliquer sur Enregistrer. L'emplacement retourné peut être le centre d'une rue, d'un quartier ou d'une ville : ajustez-le sur la carte pour une vraie borne Wi-Fi. Le service public est destiné à des tests manuels légers, pas à une recherche intensive multi-utilisateur. Voir [politique Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

La carte utilise **OpenStreetMap**, avec attribution visible, et **Leaflet**, chargé depuis un CDN. **Une connexion Internet est nécessaire pour charger le fond de carte et Leaflet** ; le serveur FastAPI, l'API et SQLite continuent à fonctionner localement. Les services communautaires OpenStreetMap ne doivent pas être utilisés pour télécharger massivement les tuiles ou préparer une carte hors ligne. Voir [politique d'utilisation des tuiles](https://operations.osmfoundation.org/policies/tiles/) et [documentation Leaflet](https://leafletjs.com/examples-v1/quick-start/).

**Limite historique :** les anciennes positions calculées uniquement en X/Y restent stockées mais ne sont pas converties automatiquement en GPS. Il faut géoréférencer les bornes puis **envoyer de nouveaux scans** pour obtenir de nouvelles positions visibles sur la carte.

**Hotspot / borne mobile :** la carte permet de **mettre à jour manuellement** la position d'un BSSID mobile. Le serveur ne suit pas automatiquement une borne qui se déplace ; une gestion de positions de bornes horodatées serait nécessaire pour cela.

## 7. Tests à réaliser

### Test 1 — Vérifier les routes

Démarrer le serveur puis vérifier :

1. `GET /health` dans `/docs`.
2. `POST /access-points` avec un BSSID fictif.
3. `POST /scans` avec ce BSSID.
4. `GET /scans` et `GET /trackers` pour vérifier l'enregistrement.
5. `GET /trackers/{tracker_id}/positions` pour vérifier l'estimation.

### Test 2 — Simuler un déplacement sans ESP32

Garder le serveur ouvert et lancer **dans un deuxième terminal**, à la racine du dépôt :

```powershell
.\py3.11\Scripts\python.exe src\demo.py
```

Le script ajoute **quatre bornes fictives géoréférencées près de Jussieu** et envoie sept scans pour le tracker `demo`. Ensuite, ouvrir `/map`, choisir ce tracker et cliquer sur « Cadrer les points ». Ces coordonnées et ces BSSID sont **des exemples**, pas des bornes réellement mesurées.

### Test 3 — Scanner les réseaux Wi-Fi depuis Windows

Pour tester une seule fois :

```powershell
.\py3.11\Scripts\python.exe src\tracker_windows.py --once
```

Pour envoyer un nouveau relevé toutes les 60 secondes :

```powershell
.\py3.11\Scripts\python.exe src\tracker_windows.py --tracker-id pc-windows --interval 60
```

Le script exploite `netsh wlan show networks mode=bssid`. Sur Windows, le niveau de signal est généralement fourni sous forme de **pourcentage** : sa conversion en dBm dans ce script est **approximative**, ce qui limite la précision de la localisation. La disponibilité des BSSID dépend aussi de la carte Wi-Fi et des autorisations Windows.

**Ne pas confondre :** le PC héberge le serveur FastAPI, mais celui-ci n'effectue pas lui-même le scan Wi-Fi. C'est le client Python (`tracker_windows.py`) qui récupère les réseaux puis transmet les données à l'API.

### Tests automatiques (facultatif)

Le fichier `src/test_api.py` permet de vérifier les routes principales, les AP GPS, les positions estimées et la migration de l'ancienne base. Les dépendances de test ne sont **pas** dans le `requirements.txt` actuel. Pour les installer dans `py3.11` :

```powershell
.\py3.11\Scripts\python.exe -m pip install pytest httpx
.\py3.11\Scripts\python.exe -m pytest src\test_api.py -q
```

## 8. Commandes utiles pour l'environnement virtuel

| Commande | Effet |
| --- | --- |
| `make setup PY=3.11` | Crée `py3.11` et installe les dépendances |
| `make info` | Affiche la configuration utilisée |
| `make run` | Lance la commande définie par le projet |
| `make shell` | Ouvre un nouveau PowerShell avec le venv activé |
| `make freeze` | Génère un fichier des dépendances installées |
| `make clean` | **Supprime** le venv choisi, sans supprimer les sources |
| `make rebuild` | Recrée l'environnement |

Pour **arrêter le serveur FastAPI** : `Ctrl + C` dans son terminal.

Pour **désactiver un venv activé manuellement** : `deactivate`.

Pour **quitter la fenêtre ouverte avec `make shell`** : `exit`.

Avec `make run`, le Makefile utilise directement Python dans `py3.11` : il n'y a normalement **aucun environnement à désactiver** dans le terminal parent.

## 9. Prochaines étapes

Le serveur démarre désormais manuellement sur le PC. Pour poursuivre le TP, il reste à :

1. Vérifier les routes avec Swagger (`/docs`).
2. Vérifier les enregistrements en base avec `demo.py`.
3. Tester les scans Wi-Fi réels avec `tracker_windows.py`.
4. Relever quelques BSSID et les coordonnées des points d'accès du campus.
5. Comparer la position estimée avec la position réelle et ajuster la méthode si nécessaire.
6. Vérifier les trajectoires et le filtre temporel sur OpenStreetMap.
7. Confirmer que `make run` démarre bien FastAPI avec le `Makefile.project` du TP.
8. Relever la latitude/longitude de quelques bornes réelles en cliquant sur la carte, puis évaluer la précision de l'estimation.

## 10. Remarques

- Le serveur est volontairement lié à `127.0.0.1` : il n'est pas accessible aux autres appareils du réseau.
- Ne pas publier les données de scans, BSSID ou déplacements sans autorisation.
- Ne pas ajouter le dossier `py3.11`, les caches Python ou la base `tracker.sqlite3` au dépôt Git.
- La précision d'une position Wi-Fi dépend de la qualité des mesures et de la connaissance des emplacements des points d'accès.

## 11. Modification de la carte (9 novembre 2026)

Cette version modifie seulement la partie du projet nécessaire à l'affichage géographique :

- `src/static/index.html` : interface cartographique, marqueurs et formulaire.
- `src/main.py` : coordonnées GPS en API et migration SQLite non destructive.
- `src/demo.py` : démo géographique fictive autour de Jussieu.
- `src/test_api.py` : tests couvrant notamment la compatibilité des anciennes données.
- `requirements.txt` et le Makefile générique : aucun changement de dépendance côté Python n'est nécessaire.

Pour intégrer les fichiers à un dépôt existant, faire une copie de sécurité de `src/main.py`, `src/static/index.html` et `src/tracker.sqlite3`, puis remplacer les fichiers correspondants. **Ne pas remplacer un `main.py` déjà personnalisé sans comparer les modifications.** Le ZIP fournit aussi le Makefile générique utilisé pour les tests, mais il n'est pas obligatoire de remplacer celui du dépôt.

## 12. Barre de recherche de lieu (9 novembre 2026)

- Ajout d'un champ **Rechercher un lieu en France** sur `/map`, sans changer le serveur Python ni le `Makefile`.
- Rechercher manuellement une ville, une rue ou une adresse ; sélectionner une des propositions.
- La carte zoome sur le résultat et remplit les champs GPS de l'éditeur des points d'accès.
- Aucun BSSID n'est ajouté à SQLite tant que l'utilisateur ne clique pas sur **Enregistrer**.
- Connexion Internet nécessaire à la recherche (API publique Nominatim) et au fond de carte.
- Pour ce changement, seul `src/static/index.html` est nécessaire côté application.
