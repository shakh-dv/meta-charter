# Charter Service

## 🚀 Setup

### 1. Create virtual env

```bash
uv venv --python 3.11
```

### 2. Activate

```bash
.venv\Scripts\activate
```

### 3. Install deps

```bash
uv sync
```

---

## ⚙️ Run project

```bash
uv run dev
```

---

## 🗄️ Database

### Create migration

```bash
alembic revision --autogenerate -m "message"
```

### Apply migration

```bash
alembic upgrade head
```

### Rollback

```bash
alembic downgrade -1
```

---

## 🔧 Notes

* FastAPI uses **asyncpg**
* Alembic uses **psycopg2**
* DB config:

  * `.env` → app
  * `alembic.ini` → migrations

---

## 🧠 Rules

* 1 offer = 1 row
* raw_json = original response
* no filtering via JSON
* use indexes

---

## 📦 Stack

* FastAPI
* SQLAlchemy (async)
* PostgreSQL
* Alembic
* uv
