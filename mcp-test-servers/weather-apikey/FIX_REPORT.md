# Weather MCP Server - Fix Report

## Date: 2025-11-27

## Problemes Identifies

### 1. Port Incorrect (CRITIQUE)
**Cause:** Le serveur ecoutait sur le port **9001** au lieu de **8001**
- Ligne 181: `uvicorn.run(app, host="127.0.0.1", port=9001)`
- Le backend s'attendait a trouver le serveur sur le port 8001
- **Impact:** Le serveur etait inaccessible depuis le backend

### 2. Endpoint avec Trailing Slash (CRITIQUE)
**Cause:** L'endpoint MCP etait defini comme `/mcp/` (avec trailing slash)
- Ligne 41: `@app.post("/mcp/", dependencies=[Depends(verify_api_key)])`
- Le backend appelle `/mcp` (sans trailing slash)
- FastAPI redirige automatiquement `/mcp` vers `/mcp/` avec un code 307 (Temporary Redirect)
- Apres la redirection, le backend recoit un 405 (Method Not Allowed) car le GET est utilise au lieu de POST
- **Impact:** Erreurs 307 puis 405 sur toutes les requetes MCP

### 3. API Key
**Info:** Le serveur attend l'API key `test-weather-api-key-123`
- Ligne 8: `API_KEY = "test-weather-api-key-123"`
- Cette cle doit etre configuree dans le backend lors de l'ajout du serveur MCP

## Corrections Apportees

### 1. Changement du Port
```python
# AVANT
uvicorn.run(app, host="127.0.0.1", port=9001)

# APRES
uvicorn.run(app, host="127.0.0.1", port=8001)
```
**Fichier:** `/Users/hugohoarau/Desktop/CODE/PERSO/full-ai-client/dev/mcp-test-servers/weather-apikey/server.py`
**Ligne:** 181

### 2. Suppression du Trailing Slash
```python
# AVANT
@app.post("/mcp/", dependencies=[Depends(verify_api_key)])

# APRES
@app.post("/mcp", dependencies=[Depends(verify_api_key)])
```
**Fichier:** `/Users/hugohoarau/Desktop/CODE/PERSO/full-ai-client/dev/mcp-test-servers/weather-apikey/server.py`
**Ligne:** 41

## Validation des Corrections

### Tests Effectues
Tous les tests ont ete executes avec succes :

#### Test 1: Health Check
```bash
curl http://127.0.0.1:8001/health
```
**Resultat:** `{"status":"ok"}` - ✅ OK

#### Test 2: Initialize avec API Key Correcte
```bash
curl -X POST 'http://127.0.0.1:8001/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer test-weather-api-key-123' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```
**Resultat:** Server info retourne correctement - ✅ OK
```json
{
  "name": "weather-apikey",
  "version": "1.0.0"
}
```

#### Test 3: Liste des Outils
```bash
curl -X POST 'http://127.0.0.1:8001/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer test-weather-api-key-123' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```
**Resultat:** 2 outils trouves - ✅ OK
- `get_alerts`: Get weather alerts for a US state
- `get_forecast`: Get weather forecast for a location

#### Test 4: Authentification avec Mauvaise API Key
```bash
curl -X POST 'http://127.0.0.1:8001/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer wrong-key' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```
**Resultat:** `{"detail":"Invalid API key"}` - ✅ OK (securite fonctionne)

#### Test 5: Appel d'Outil (get_forecast)
```bash
curl -X POST 'http://127.0.0.1:8001/mcp' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer test-weather-api-key-123' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_forecast","arguments":{"latitude":37.7749,"longitude":-122.4194}}}'
```
**Resultat:** Previsions meteo retournees correctement - ✅ OK

### Logs du Serveur
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     127.0.0.1:54769 - "GET /health HTTP/1.1" 200 OK
INFO:     127.0.0.1:54804 - "POST /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:54900 - "POST /mcp HTTP/1.1" 401 Unauthorized
INFO:     127.0.0.1:54927 - "POST /mcp HTTP/1.1" 200 OK
```

## Statut Final

### Serveur MCP Weather (API Key)
- **Status:** ✅ FONCTIONNEL
- **URL:** http://127.0.0.1:8001
- **Endpoints:**
  - `GET /health` - Health check (sans authentification)
  - `POST /mcp` - Endpoint JSON-RPC MCP (avec authentification Bearer)
- **API Key:** `test-weather-api-key-123`
- **Outils disponibles:** 2 (get_alerts, get_forecast)
- **Processus:** PID 24561

### Points Importants pour le Backend

1. **Configuration du Serveur:**
   - URL: `http://127.0.0.1:8001` ou `http://localhost:8001`
   - Type d'authentification: `api-key`
   - API Key: `test-weather-api-key-123`

2. **Endpoints a Utiliser:**
   - Health check: `GET /health` (pas d'auth)
   - MCP: `POST /mcp` (avec header `Authorization: Bearer test-weather-api-key-123`)

3. **Format des Requetes:**
   - Content-Type: `application/json`
   - Body: JSON-RPC 2.0 format
   - Authorization: `Bearer test-weather-api-key-123`

## Recommandations

1. **Coherence Backend:** S'assurer que le backend utilise bien l'API key `test-weather-api-key-123` pour ce serveur MCP

2. **Standardisation:** Verifier que tous les serveurs MCP de test utilisent des endpoints coherents (sans trailing slash)

3. **Documentation:** Ajouter cette API key dans la documentation ou configuration du backend pour faciliter les tests

4. **Monitoring:** Le serveur ecoute maintenant sur le bon port (8001) et repond correctement aux requetes
