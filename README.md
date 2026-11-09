# TP4 IoT — Tracker par Wi-Fi Sniffing

Projet réalisé dans le cadre du TP4 IoT (S7) à Polytech Sorbonne.

L'objectif est de récupérer des informations sur les réseaux Wi-Fi visibles (SSID, BSSID, RSSI), d'en déduire une position approximative et de conserver l'historique des déplacements d'un tracker.

**Choix actuel :** on laisse de côté l'ESP32 et LoRaWAN. Le serveur est développé avec **FastAPI**, il tourne **en local sur mon PC Windows** et utilise **SQLite** pour stocker les données. Pour le moment, les scans peuvent venir d'un script de simulation ou d'un script Python exécuté sur Windows.

## 1. Avancement du projet — 9 novembre 2026

| Élément | État | Commentaire |
| --- | --- | --- |
| Environnement Python 3.11 | OK | Environnement `py3.11` créé par le Makefile |
| Installation des dépendances | OK | `fastapi` et `uvicorn` installés |
| Démarrage manuel de FastAPI | OK | Uvicorn a affiché `Application startup complete.` |
| Démarrage avec `make run` | À revalider | Le Makefile d'origine lançait `src/main.py` sans démarrer Uvicorn |
| Configuration générique du Makefile | Préparée | Utilisation possible d'un `Makefile.project` propre au TP |
| Routes API, SQLite et interface web | Implémentées dans la version du code fournie | À tester dans le dépôt local |
| Envoi de scans simulés | Script disponible | Test local restant à faire |
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

Cela confirme le **démarrage du serveur**, pas encore le bon fonctionnement de toutes les routes ni de la localisation.

## 2. Organisation des fichiers

```text
TP_4_IOT_S7_polytech_sorbonne/
├── Makefile                    # Gestion générique des environnements Python
├── Makefile.project            # Facultatif : lancement spécifique à ce TP
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
        └── index.html         # Interface web de visualisation
```

`Makefile.project` n'est présent que si on a ajouté la configuration proposée. Le fichier `tracker.sqlite3` est créé dans `src/` lors du démarrage de l'application, si le code est resté celui de la version fournie.

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

### Étape 2 — Référencer les points d'accès

La route **POST `/access-points`** permet d'enregistrer un point d'accès et ses coordonnées :

```json
{
  "bssid": "AA:BB:CC:DD:EE:01",
  "ssid": "Reseau_A",
  "x": 5.0,
  "y": 12.0
}
```

Les coordonnées sont pour l'instant dans un **repère local en mètres** (pas une latitude/longitude GPS). Les points connus sont consultables avec **GET `/access-points`**.

Quand un scan arrive, le serveur estime une position par **barycentre pondéré à partir des RSSI** et des coordonnées des points connus. Ce n'est pas une trilatération précise. Si aucun BSSID du scan n'est référencé, la position reste `null` mais les observations sont conservées.

### Étape 3 — Stocker l'historique

Les données sont enregistrées dans SQLite avec les tables suivantes :

- `access_points` : les BSSID et les coordonnées des points d'accès.
- `scans` : l'identifiant du tracker et la date du relevé.
- `observations` : les SSID, BSSID et RSSI mesurés pendant chaque scan.
- `positions` : les positions estimées, associées au tracker et à la date.

Principales routes de consultation :

| Méthode | Route | Utilité |
| --- | --- | --- |
| GET | `/access-points` | Liste des points d'accès |
| POST | `/access-points` | Ajouter ou mettre à jour un point d'accès |
| POST | `/scans` | Enregistrer un scan et calculer une position si possible |
| GET | `/scans` | Lister les scans |
| GET | `/scans/{scan_id}` | Détails d'un scan |
| GET | `/trackers` | Liste des trackers |
| GET | `/trackers/{tracker_id}/positions` | Historique des positions |
| GET | `/trackers/{tracker_id}/positions?start=2026-11-09T14:00:00Z&end=2026-11-09T17:00:00Z` | Historique sur une période |

### Étape 4 — Afficher les positions

La page **`/map`** permet de consulter le trajet d'un tracker sur un plan local et de filtrer une période.

Il ne s'agit pas encore d'une carte réelle du campus : il faudra relever les positions des bornes et, si nécessaire, ajouter un fond de plan correctement aligné.

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

Le script ajoute quatre points d'accès fictifs et envoie sept scans pour le tracker `demo`. Ensuite, ouvrir `/map` et sélectionner ce tracker.

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

Le fichier `src/test_api.py` permet de vérifier les principales routes. Les dépendances de test ne sont **pas** dans le `requirements.txt` actuel. Pour les installer dans `py3.11` :

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
6. Vérifier les trajectoires et le filtre temporel de l'interface web.
7. Confirmer que `make run` démarre bien FastAPI avec le `Makefile.project` du TP.

## 10. Remarques

- Le serveur est volontairement lié à `127.0.0.1` : il n'est pas accessible aux autres appareils du réseau.
- Ne pas publier les données de scans, BSSID ou déplacements sans autorisation.
- Ne pas ajouter le dossier `py3.11`, les caches Python ou la base `tracker.sqlite3` au dépôt Git.
- La précision d'une position Wi-Fi dépend de la qualité des mesures et de la connaissance des emplacements des points d'accès.
