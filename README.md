# bullwatch_unified

Single Flask app with modular blueprints for:
- core dashboard
- orderflow
- liquidation
- alpha

## Quickstart

```bash
cd bullwatch_unified
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

Open: http://127.0.0.1:5000

## Alternative (Flask CLI)

```bash
export FLASK_APP=bullwatch_unified:create_app
flask run --debug
```

## Tests

```bash
pytest -q
```
