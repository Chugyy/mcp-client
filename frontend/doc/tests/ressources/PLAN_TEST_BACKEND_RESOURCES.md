# Plan de Test - Backend Resources API

## Objectif
Valider que les corrections apportées au backend Resources API fonctionnent correctement et exposent les métadonnées RAG au frontend.

---

## Prérequis

### Environnement
- Backend FastAPI démarré (`uvicorn app.main:app --reload`)
- Base de données PostgreSQL avec pgvector configurée
- Migrations à jour (migration 012_rag_system.sql appliquée)
- Token JWT valide pour authentification

### Variables d'environnement
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-key
```

---

## Phase 1 : Tests des Models

### Test 1.1 : Dataclass Upload contient resource_id
**Fichier:** `app/database/models.py`

**Validation:**
```python
from app.database.models import Upload

# Vérifier que le champ existe
assert hasattr(Upload, 'resource_id')
```

**Résultat attendu:** ✅ Le champ `resource_id` existe dans le dataclass

---

### Test 1.2 : Pydantic ResourceCreate est conforme
**Fichier:** `app/api/models.py`

**Validation:**
```python
from app.api.models import ResourceCreate

# Créer un DTO valide
dto = ResourceCreate(
    name="Test Resource",
    description="Description test",
    enabled=True,
    embedding_model="text-embedding-3-large",
    embedding_dim=3072
)

# Vérifier que les champs obsolètes n'existent plus
assert not hasattr(dto, 'type')
assert not hasattr(dto, 'config')
assert not hasattr(dto, 'methods')
assert not hasattr(dto, 'service_id')
```

**Résultat attendu:** ✅ DTO conforme au schéma DB

---

### Test 1.3 : Pydantic ResourceResponse expose les champs RAG
**Fichier:** `app/api/models.py`

**Validation:**
```python
from app.api.models import ResourceResponse
from datetime import datetime

response = ResourceResponse(
    id="res_test123",
    name="Test Resource",
    description="Test",
    enabled=True,
    status="ready",
    chunk_count=150,
    embedding_model="text-embedding-3-large",
    embedding_dim=3072,
    indexed_at=datetime.now(),
    error_message=None,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Vérifier que tous les champs RAG existent
assert response.status == "ready"
assert response.chunk_count == 150
assert response.embedding_model == "text-embedding-3-large"
assert response.embedding_dim == 3072
```

**Résultat attendu:** ✅ Tous les champs RAG sont exposés

---

### Test 1.4 : ResourceWithUploads existe
**Fichier:** `app/api/models.py`

**Validation:**
```python
from app.api.models import ResourceWithUploads, UploadResponse

# Vérifier que la classe existe
assert ResourceWithUploads is not None
assert hasattr(ResourceWithUploads, 'uploads')
```

**Résultat attendu:** ✅ Classe créée et hérite de ResourceResponse

---

## Phase 2 : Tests des CRUD Operations

### Test 2.1 : create_resource() n'accepte plus les champs obsolètes
**Fichier:** `app/database/crud/resources.py`

**Test:**
```python
from app.database.crud import create_resource
import inspect

# Vérifier la signature de la fonction
sig = inspect.signature(create_resource)
params = sig.parameters.keys()

# Vérifier que les champs obsolètes n'existent plus
assert 'resource_type' not in params
assert 'config' not in params
assert 'methods' not in params
assert 'service_id' not in params

# Vérifier que les nouveaux champs existent
assert 'embedding_model' in params
assert 'embedding_dim' in params
```

**Résultat attendu:** ✅ Signature mise à jour

---

### Test 2.2 : create_resource() fonctionne
**Test d'intégration:**

**Commande cURL:**
```bash
# Récupérer un token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  | jq -r '.access_token')

# Créer une resource
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Resource Backend",
    "description": "Resource de test",
    "enabled": true,
    "embedding_model": "text-embedding-3-large",
    "embedding_dim": 3072
  }' | jq .
```

**Résultat attendu:**
```json
{
  "id": "res_...",
  "name": "Test Resource Backend",
  "description": "Resource de test",
  "enabled": true,
  "status": "pending",
  "chunk_count": 0,
  "embedding_model": "text-embedding-3-large",
  "embedding_dim": 3072,
  "indexed_at": null,
  "error_message": null,
  "created_at": "2024-11-30T...",
  "updated_at": "2024-11-30T..."
}
```

**Validation:**
- ✅ 201 Created
- ✅ Champs RAG présents dans la réponse
- ✅ Pas de champs obsolètes (type, config, etc.)

---

### Test 2.3 : update_resource_status() fonctionne
**Test SQL direct:**

```sql
-- Vérifier que la fonction existe et fonctionne
SELECT * FROM resources WHERE id = 'res_test123';

-- La fonction Python devrait exécuter:
-- UPDATE resources SET status='processing', updated_at=NOW() WHERE id='res_test123'
```

**Test Python:**
```python
from app.database.crud import update_resource_status

# Créer une resource
resource_id = await create_resource(
    name="Test Status",
    description="Test"
)

# Mettre à jour le status
success = await update_resource_status(
    resource_id=resource_id,
    status='processing'
)

assert success == True

# Vérifier en DB
resource = await get_resource(resource_id)
assert resource['status'] == 'processing'
```

**Résultat attendu:** ✅ Status mis à jour correctement

---

### Test 2.4 : list_uploads_by_resource() fonctionne
**Test:**

```python
from app.database.crud import list_uploads_by_resource, create_upload, create_resource

# Créer une resource
resource_id = await create_resource(name="Test Resource")

# Créer 2 uploads
upload1_id = await create_upload(
    user_id=None,
    agent_id=None,
    resource_id=resource_id,
    upload_type='resource',
    filename='doc1.pdf',
    file_path='/uploads/doc1.pdf',
    file_size=1000,
    mime_type='application/pdf'
)

upload2_id = await create_upload(
    user_id=None,
    agent_id=None,
    resource_id=resource_id,
    upload_type='resource',
    filename='doc2.pdf',
    file_path='/uploads/doc2.pdf',
    file_size=2000,
    mime_type='application/pdf'
)

# Récupérer les uploads
uploads = await list_uploads_by_resource(resource_id)

assert len(uploads) == 2
assert uploads[0]['filename'] in ['doc1.pdf', 'doc2.pdf']
assert uploads[0]['resource_id'] == resource_id
```

**Résultat attendu:** ✅ Liste correcte des uploads

---

## Phase 3 : Tests des Routes API

### Test 3.1 : GET /resources retourne les champs RAG
**Commande cURL:**

```bash
curl -X GET http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" | jq '.[0]'
```

**Résultat attendu:**
```json
{
  "id": "res_...",
  "name": "Test Resource",
  "description": "...",
  "enabled": true,
  "status": "pending",
  "chunk_count": 0,
  "embedding_model": "text-embedding-3-large",
  "embedding_dim": 3072,
  "indexed_at": null,
  "error_message": null,
  "created_at": "...",
  "updated_at": "..."
}
```

**Validation:**
- ✅ 200 OK
- ✅ Champs RAG présents
- ✅ Pas de champs obsolètes

---

### Test 3.2 : GET /resources/{id} retourne les métadonnées
**Commande cURL:**

```bash
RESOURCE_ID="res_abc123"

curl -X GET http://localhost:8000/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Validation:**
- ✅ 200 OK si existe
- ✅ 404 si n'existe pas
- ✅ Tous les champs RAG présents

---

### Test 3.3 : PATCH /resources/{id} fonctionne
**Commande cURL:**

```bash
RESOURCE_ID="res_abc123"

curl -X PATCH http://localhost:8000/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nouveau nom",
    "description": "Nouvelle description",
    "enabled": false
  }' | jq .
```

**Résultat attendu:**
```json
{
  "id": "res_abc123",
  "name": "Nouveau nom",
  "description": "Nouvelle description",
  "enabled": false,
  "status": "pending",
  "chunk_count": 0,
  ...
}
```

**Validation:**
- ✅ 200 OK
- ✅ Champs mis à jour
- ✅ `updated_at` modifié
- ✅ Champs RAG inchangés (status, chunk_count, etc.)

---

### Test 3.4 : GET /resources/{id}/uploads retourne les fichiers
**Commande cURL:**

```bash
RESOURCE_ID="res_abc123"

curl -X GET http://localhost:8000/api/v1/resources/$RESOURCE_ID/uploads \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Résultat attendu:**
```json
[
  {
    "id": "upl_xyz789",
    "user_id": null,
    "agent_id": null,
    "resource_id": "res_abc123",
    "type": "resource",
    "filename": "doc1.pdf",
    "file_path": "/uploads/doc1.pdf",
    "file_size": 1500000,
    "mime_type": "application/pdf",
    "created_at": "2024-11-30T..."
  }
]
```

**Validation:**
- ✅ 200 OK
- ✅ Liste vide si pas d'uploads
- ✅ 404 si resource n'existe pas
- ✅ `resource_id` présent dans chaque upload

---

### Test 3.5 : POST /uploads avec resource_id fonctionne
**Commande cURL:**

```bash
RESOURCE_ID="res_abc123"

curl -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "upload_type=resource" \
  -F "resource_id=$RESOURCE_ID" | jq .
```

**Résultat attendu:**
```json
{
  "id": "upl_...",
  "user_id": null,
  "agent_id": null,
  "resource_id": "res_abc123",
  "type": "resource",
  "filename": "document.pdf",
  "file_path": "/uploads/document.pdf",
  "file_size": 1234567,
  "mime_type": "application/pdf",
  "created_at": "2024-11-30T..."
}
```

**Validation:**
- ✅ 201 Created
- ✅ `resource_id` correctement associé
- ✅ Fichier uploadé sur le serveur

---

## Phase 4 : Test du Pipeline RAG Complet

### Test 4.1 : Workflow complet - Création → Upload → Ingestion

**Étape 1 : Créer une resource**
```bash
RESOURCE_ID=$(curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Documentation Technique",
    "description": "Docs Q4 2024",
    "enabled": true
  }' | jq -r '.id')

echo "Resource créée: $RESOURCE_ID"
```

**Validation:**
- ✅ Status = `pending`
- ✅ chunk_count = 0
- ✅ indexed_at = null

---

**Étape 2 : Uploader des fichiers**
```bash
# Upload fichier 1
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./test-docs/rapport.pdf" \
  -F "upload_type=resource" \
  -F "resource_id=$RESOURCE_ID"

# Upload fichier 2
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./test-docs/presentation.pptx" \
  -F "upload_type=resource" \
  -F "resource_id=$RESOURCE_ID"
```

**Validation:**
```bash
# Vérifier les uploads
curl -X GET http://localhost:8000/api/v1/resources/$RESOURCE_ID/uploads \
  -H "Authorization: Bearer $TOKEN" | jq 'length'

# Résultat attendu: 2
```

---

**Étape 3 : Lancer l'ingestion**
```bash
curl -X POST http://localhost:8000/api/v1/resources/$RESOURCE_ID/ingest \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Résultat attendu:**
```json
{
  "success": true,
  "message": "Resource res_... ingestion complete"
}
```

**Validation immédiate:**
```bash
# Vérifier le status pendant l'ingestion
curl -X GET http://localhost:8000/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.status'

# Résultat: "processing"
```

---

**Étape 4 : Attendre la fin et vérifier**
```bash
# Attendre quelques secondes puis vérifier
sleep 5

curl -X GET http://localhost:8000/api/v1/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Résultat attendu:**
```json
{
  "id": "res_...",
  "name": "Documentation Technique",
  "status": "ready",
  "chunk_count": 142,
  "embedding_model": "text-embedding-3-large",
  "embedding_dim": 3072,
  "indexed_at": "2024-11-30T14:25:30.123Z",
  "error_message": null,
  ...
}
```

**Validation finale:**
- ✅ status = `ready`
- ✅ chunk_count > 0
- ✅ indexed_at défini (timestamp récent)
- ✅ error_message = null

---

**Étape 5 : Vérifier en DB**
```sql
-- Compter les embeddings créés
SELECT COUNT(*) FROM embeddings WHERE resource_id = 'res_...';

-- Vérifier les chunks par upload
SELECT
    u.filename,
    COUNT(e.id) as chunk_count
FROM uploads u
LEFT JOIN embeddings e ON e.upload_id = u.id
WHERE u.resource_id = 'res_...'
GROUP BY u.id, u.filename;
```

**Résultat attendu:**
```
 filename         | chunk_count
------------------+-------------
 rapport.pdf      | 87
 presentation.pptx| 55
```

---

## Phase 5 : Tests d'Erreurs

### Test 5.1 : Création resource avec données invalides
**Test:**
```bash
# Nom vide
curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "", "enabled": true}' | jq .
```

**Résultat attendu:** ✅ 422 Unprocessable Entity

---

### Test 5.2 : Upload vers resource inexistante
**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./test.pdf" \
  -F "upload_type=resource" \
  -F "resource_id=res_inexistant"
```

**Résultat attendu:** ✅ 404 Resource not found

---

### Test 5.3 : Ingestion resource sans fichiers
**Test:**
```bash
# Créer une resource vide
RESOURCE_ID=$(curl -X POST http://localhost:8000/api/v1/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Resource vide", "enabled": true}' | jq -r '.id')

# Lancer l'ingestion
curl -X POST http://localhost:8000/api/v1/resources/$RESOURCE_ID/ingest \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Résultat attendu:**
- Option 1: ✅ 400 Bad Request ("No files to ingest")
- Option 2: ✅ Status = `ready` avec chunk_count = 0

---

## Checklist Finale

### Models
- [ ] Upload.resource_id existe
- [ ] ResourceCreate conforme (champs RAG ajoutés, obsolètes supprimés)
- [ ] ResourceUpdate conforme
- [ ] ResourceResponse expose tous les champs RAG
- [ ] ResourceWithUploads créé

### CRUD
- [ ] create_resource() signature correcte
- [ ] create_resource() fonctionne (test intégration)
- [ ] update_resource() signature correcte
- [ ] update_resource_status() existe et fonctionne
- [ ] list_uploads_by_resource() existe et fonctionne
- [ ] create_upload() accepte resource_id

### Routes API
- [ ] POST /resources retourne champs RAG
- [ ] GET /resources retourne champs RAG
- [ ] GET /resources/{id} retourne champs RAG
- [ ] PATCH /resources/{id} fonctionne
- [ ] DELETE /resources/{id} fonctionne
- [ ] GET /resources/{id}/uploads existe et fonctionne
- [ ] POST /uploads accepte resource_id

### Pipeline RAG
- [ ] Workflow complet fonctionne (create → upload → ingest)
- [ ] Status passe de pending → processing → ready
- [ ] chunk_count mis à jour correctement
- [ ] indexed_at défini après ingestion
- [ ] Embeddings créés en DB
- [ ] Gestion d'erreurs (error_message, status='error')

### Régression
- [ ] Endpoints existants non cassés (auth, agents, chats, etc.)
- [ ] Uploads user/agent fonctionnent toujours
- [ ] Migrations appliquées correctement

---

## Outils de Test

### Script de test automatisé
```bash
#!/bin/bash
# tests/test_resources_api.sh

set -e

# Configuration
API_URL="http://localhost:8000/api/v1"
EMAIL="test@example.com"
PASSWORD="password123"

# 1. Login
echo "🔐 Login..."
TOKEN=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | jq -r '.access_token')

echo "✅ Token: ${TOKEN:0:20}..."

# 2. Créer resource
echo "📦 Création resource..."
RESOURCE_ID=$(curl -s -X POST $API_URL/resources \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Auto","description":"Test automatisé","enabled":true}' \
  | jq -r '.id')

echo "✅ Resource créée: $RESOURCE_ID"

# 3. Vérifier GET
echo "🔍 Vérification GET /resources/$RESOURCE_ID..."
curl -s -X GET $API_URL/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" | jq .

# 4. Upload fichier
echo "📤 Upload fichier..."
curl -s -X POST $API_URL/uploads \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./test.txt" \
  -F "upload_type=resource" \
  -F "resource_id=$RESOURCE_ID" | jq .

# 5. Liste uploads
echo "📋 Liste uploads..."
curl -s -X GET $API_URL/resources/$RESOURCE_ID/uploads \
  -H "Authorization: Bearer $TOKEN" | jq .

# 6. Ingestion
echo "🚀 Lancement ingestion..."
curl -s -X POST $API_URL/resources/$RESOURCE_ID/ingest \
  -H "Authorization: Bearer $TOKEN" | jq .

# 7. Attendre et vérifier status
echo "⏳ Attente ingestion (5s)..."
sleep 5

echo "✅ Status final:"
curl -s -X GET $API_URL/resources/$RESOURCE_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.status, .chunk_count, .indexed_at'

echo "🎉 Tests terminés!"
```

---

## Résultat Attendu

**Toutes les validations doivent passer ✅**

Si un test échoue, vérifier :
1. Les logs backend (`uvicorn`)
2. Les logs PostgreSQL
3. Les migrations appliquées (`SELECT * FROM schema_migrations;`)
4. La signature des fonctions CRUD
5. Les modèles Pydantic

---

## Prochaines Étapes

Une fois tous les tests passés :
1. ✅ Backend validé et fonctionnel
2. 🚀 Démarrer l'implémentation frontend
3. 📦 Créer le service `resources` frontend selon l'architecture documentée
4. 🎨 Intégrer dans la page `ressources`
5. 🧪 Tests end-to-end (frontend → backend → DB)
