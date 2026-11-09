# TP4 IoT — serveur local FastAPI / Wi-Fi Sniffing

Ce projet remplace l'envoi depuis l'ESP32 par des **requêtes HTTP de test** ou par un **tracker logiciel Windows**. Le serveur REST tourne sur le PC, stocke tout dans SQLite et propose un plan pour visualiser les trajets.

## Contenu

- `main.py` : API REST FastAPI et base SQLite (`tracker.sqlite3` créée automatiquement).
- `static/index.html` : plan local interactif en X/Y (mètres).
- `demo.py` : 4 points d'accès fictifs et 7 scans simulés pour essayer toute la chaîne.
- `tracker_windows.py` : client facultatif qui lit les réseaux à proximité avec `netsh` et envoie des scans au serveur.
- `requirements.txt` : dépendances du serveur.

## Lancement sur Windows (PowerShell)

Dans le dossier du projet :

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Si la commande `py -3.11` n'existe pas, essayer `py -m venv .venv` (Python 3.10+ requis). Si l'activation PowerShell est bloquée, utiliser directement `.\.venv\Scripts\python.exe` pour les commandes Python.

Ouvrir :
- `http://127.0.0.1:8000/docs` : API interactive (Swagger).
- `http://127.0.0.1:8000/map` : visualisation des points d'accès et des positions.
- `http://127.0.0.1:8000/health` : état du serveur.

### Tester sans ESP32 et sans données réelles

Dans un **deuxième terminal**, dans le même dossier et avec l'environnement activé :

```powershell
python demo.py
```

La démo crée 4 BSSID fictifs et 7 positions : rafraîchir `/map`, choisir le tracker `demo`.

## Étapes du TP

### Étape 1 — Réception REST

Le client envoie son identifiant et les réseaux aperçus :

`POST /scans`

```json
{
  "tracker_id": "tracker-01",
  "readings": [
    {"ssid": "Reseau_A", "bssid": "AA:BB:CC:DD:EE:01", "rssi": -51},
    {"ssid": "Reseau_B", "bssid": "AA:BB:CC:DD:EE:02", "rssi": -69}
  ]
}
```

Chaque scan reçoit un identifiant et une date côté serveur. On stocke **tous** les réseaux observés, connus ou non.

### Étape 2 — Points d'accès et estimation

Référencer chaque BSSID et ses coordonnées dans le même **repère local**, en mètres :

`POST /access-points`

```json
{
  "bssid": "AA:BB:CC:DD:EE:01",
  "ssid": "Reseau_A",
  "x": 5.0,
  "y": 12.0
}
```

Les points d'accès se lisent avec `GET /access-points`. La même route POST met à jour les coordonnées si le BSSID existe déjà.

La position est calculée par **barycentre pondéré** des points d'accès connus. Le poids est proportionnel à `1 / distance_estimee²`, où la distance estimée est obtenue avec un modèle RSSI très simplifié (−45 dBm à 1 m, exposant 3). Avec un seul point connu, la position estimée est celle de cet AP. Aucun AP connu : `position: null`, mais le scan reste enregistré.

**Attention :** cette méthode n'est pas une vraie trilatération, et les RSSI varient avec les murs, la position et le matériel. Pour de meilleures mesures, calibrer le modèle sur place, utiliser au moins 3 BSSID connus, et repérer leurs coordonnées avec soin.

### Étape 3 — Historique des trajets

- `GET /trackers` : liste des trackers.
- `GET /trackers/tracker-01/positions` : positions du tracker dans l'ordre chronologique.
- `GET /trackers/tracker-01/positions?start=2026-11-09T14:00:00Z&end=2026-11-09T17:00:00Z` : période précise (dates ISO avec fuseau horaire).
- `GET /scans` : résumé des scans reçus.
- `GET /scans/1` : RSSI bruts d'un scan précis et éventuelle position estimée.

Les observations sont conservées en base, même si les BSSID n'ont pas encore été référencés. L'estimation de position, en revanche, est faite au moment de la réception : pour recalculer un historique après ajout d'AP, il faudrait ajouter une fonctionnalité dédiée.

### Étape 4 — Visualiser

Le site `/map` affiche les points d'accès, le tracé d'un tracker, son dernier point et un filtre de dates. Il représente le plan en coordonnées locales. Une véritable carte du campus en fond nécessiterait un plan géoréférencé ou une image alignée sur ce repère.

## Utiliser le PC Windows comme tracker (facultatif)

Sans ESP32, Windows peut lister les BSSID visibles (si la carte Wi-Fi et les autorisations du système le permettent). Faire d'abord un scan :

```powershell
python tracker_windows.py --once
```

Puis, pour envoyer les relevés toutes les 60 secondes :

```powershell
python tracker_windows.py --tracker-id pc-windows --interval 60
```

La commande utilise `netsh wlan show networks mode=bssid`. **Windows fournit souvent un pourcentage de signal, pas le RSSI brut en dBm** : le script utilise la conversion indicative `-100 + pourcentage/2`. Il faut donc considérer les positions comme approximatives, surtout avant calibration. Chaque BSSID réel doit être référencé dans `POST /access-points` avec ses coordonnées, sinon la position sera `null`.

Le PC fait à la fois serveur et tracker dans cet exemple ; d'autres appareils pourraient envoyer des données si on change l'adresse d'écoute du serveur et qu'on sécurise l'accès. En mode de base, `127.0.0.1` reste accessible **seulement depuis ton PC**.

## Schéma de la base SQL

- `access_points` : `bssid`, `ssid`, `x`, `y`, `updated_at`.
- `scans` : `id`, `tracker_id`, `scanned_at`.
- `observations` : `scan_id`, `bssid`, `ssid`, `rssi`.
- `positions` : `scan_id`, `tracker_id`, `x`, `y`, `ap_count`, `method`, `estimated_at`.

Les clés SQL lient chaque observation et chaque position à son scan initial.

## Précautions

- N'enregistrer que les réseaux nécessaires au TP et respecter les règles du campus.
- Les BSSID et les déplacements peuvent être des données sensibles : garder la base en local, ne pas diffuser l'API sans authentification.
- Ne pas confondre SSID (nom du réseau) et BSSID (identifiant du point d'accès) : c'est le **BSSID** qui sert à associer une position.
