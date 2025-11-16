# 🚀 Οδηγίες Εκκίνησης Project - Multi-Cloud Manager v3.0

## Προαπαιτούμενα
- Python 3.8+
- Node.js 18+
- Docker & Docker Compose
- Azure CLI (για Azure deployments)
- GCP Service Account JSON (για GCP deployments)

---

## 📋 Βήμα προς Βήμα Εκκίνηση

### 1️⃣ Start Backend Services (PostgreSQL, Redis, Celery)

```bash
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main

# Ξεκινάει PostgreSQL και Redis με Docker Compose
docker-compose up -d

# Περίμενε 5-10 δευτερόλεπτα να ξεκινήσουν οι services
```

**Τι κάνει:**
- PostgreSQL (port 5432) - Database για deployments
- Redis (port 6379) - Message broker για Celery

---

### 2️⃣ Start Backend API (FastAPI)

**Άνοιξε νέο terminal:**

```bash
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main

# Activate Python virtual environment (αν έχεις)
source venv/bin/activate  # ή python -m venv venv && source venv/bin/activate

# Ξεκινάει το FastAPI backend
python backend/api_rest.py
```

**Τι κάνει:**
- Ξεκινάει FastAPI server στο http://localhost:8000
- Swagger UI διαθέσιμο στο http://localhost:8000/docs

---

### 3️⃣ Start Celery Worker (Async Tasks)

**Άνοιξε νέο terminal:**

```bash
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main

# Activate Python virtual environment
source venv/bin/activate

# Ξεκινάει Celery worker για async deployments
celery -A backend.tasks worker --loglevel=info
```

**Τι κάνει:**
- Celery worker που εκτελεί τα async deployment tasks
- Βλέπεις logs από τα deployments εδώ

---

### 4️⃣ Start Frontend (React + Vite)

**Άνοιξε νέο terminal:**

```bash
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main/frontend-v3

# Ξεκινάει Vite dev server
npm run dev
```

**Τι κάνει:**
- Ξεκινάει React frontend στο http://localhost:5173/
- Hot reload - οι αλλαγές φαίνονται αυτόματα

---

## ✅ Verification - Έλεγχος ότι όλα τρέχουν

Πρέπει να έχεις **4 terminals ανοιχτά:**

1. **Docker Compose** - `docker-compose up -d` (τρέχει στο background)
2. **Backend API** - `python backend/api_rest.py` → http://localhost:8000
3. **Celery Worker** - `celery -A backend.tasks worker --loglevel=info`
4. **Frontend** - `npm run dev` → http://localhost:5173/

---

## 🛑 Shutdown Project

**Για να σταματήσεις όλα:**

```bash
# 1. Σταμάτα Frontend (Ctrl+C στο terminal)
# 2. Σταμάτα Celery Worker (Ctrl+C στο terminal)
# 3. Σταμάτα Backend API (Ctrl+C στο terminal)

# 4. Σταμάτα Docker services
cd /home/thanosk/Desktop/Azure-Resource-Manager-Portal-main
docker-compose down
```

---

## 🔧 Troubleshooting

### Πρόβλημα: "Connection refused" στο Backend
```bash
# Έλεγξε αν τρέχει το Backend
curl http://localhost:8000/health

# Αν όχι, ξεκίνησέ το:
python backend/api_rest.py
```

### Πρόβλημα: "Cannot connect to Redis"
```bash
# Έλεγξε αν τρέχει το Docker Compose
docker-compose ps

# Αν όχι, ξεκίνησέ το:
docker-compose up -d
```

### Πρόβλημα: Frontend δεν φορτώνει
```bash
cd frontend-v3
rm -rf node_modules/.vite
npm run dev
```

---

## 📊 Allowed Azure Regions (Student Subscription)

Το Azure Student subscription επιτρέπει **μόνο** τα εξής regions:
- `norwayeast`
- `swedencentral`
- `polandcentral`
- `francecentral`
- `spaincentral`

---

## 🎯 Quick Start Commands (All-in-One)

**Terminal 1:**
```bash
docker-compose up -d && python backend/api_rest.py
```

**Terminal 2:**
```bash
celery -A backend.tasks worker --loglevel=info
```

**Terminal 3:**
```bash
cd frontend-v3 && npm run dev
```

---

## 📝 URLs

- Frontend: http://localhost:5173/
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

---

## 🔑 Credentials Location

- Azure: Configured via `az login`
- GCP: `credentials/peppy-booth-478115-i0-46364e3e5469.json`
- Environment variables: `.env` file
