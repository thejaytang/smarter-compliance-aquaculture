"""Importing the optional API must not write a job database into caller cwd."""
import importlib
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient


def test_import_and_health_do_not_create_a_database(tmp_path):
    from tests.support.paths import PROJECT_ROOT
    code='from pdf_extraction.api.app import app; from fastapi.testclient import TestClient; assert TestClient(app).get("/health").status_code == 200'
    result=subprocess.run([sys.executable,'-c',code],cwd=tmp_path,capture_output=True,text=True,
                          env=__import__('os').environ|{'PYTHONPATH':str(PROJECT_ROOT/'src'),'PYTHONDONTWRITEBYTECODE':'1'},timeout=30)
    assert result.returncode==0,result.stderr
    assert list(tmp_path.iterdir())==[]


def test_default_belongs_to_system2_and_explicit_database_stays_authoritative(tmp_path,monkeypatch):
    module=importlib.import_module('pdf_extraction.api.app')
    from tests.support.paths import PROJECT_ROOT
    assert module.DEFAULT_DATABASE==PROJECT_ROOT/'runtime/jobs.sqlite3'
    monkeypatch.chdir(tmp_path)
    database=tmp_path/'chosen/jobs.sqlite3'
    app=module.create_app(database,defer_store=True)
    assert not database.exists()
    assert TestClient(app).get('/metrics').status_code==200
    assert database.exists() and app.state.store.path==database
    assert not (tmp_path/'runtime').exists()


def test_explicit_factory_retains_existing_job_history(tmp_path):
    module=importlib.import_module('pdf_extraction.api.app')
    database=tmp_path/'selected.sqlite3';first=module.create_app(database)
    job=first.state.store.create('source.pdf','output','config.yaml')
    reopened=module.create_app(database,defer_store=True)
    assert reopened.state.store.get(job.id)==job
    assert TestClient(reopened).get('/jobs/'+job.id).json()['id']==job.id
