"""Amazon request verification: only signed, fresh requests for our skill are accepted."""
import base64, datetime as dt, json
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.verification import Store
import conftest
APP = conftest.APP
NOW = dt.datetime.now(dt.timezone.utc)
URL = "https://s3.amazonaws.com/echo.api/echo-api-cert.pem"


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


@pytest.fixture(scope="module")
def pki():
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca = (x509.CertificateBuilder().subject_name(_name("Test CA")).issuer_name(_name("Test CA")).public_key(ca_key.public_key())
          .serial_number(1).not_valid_before(NOW - dt.timedelta(days=1)).not_valid_after(NOW + dt.timedelta(days=30))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
          .add_extension(x509.KeyUsage(True, False, False, False, False, True, True, False, False), True)
          .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), False).sign(ca_key, hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf = (x509.CertificateBuilder().subject_name(_name("echo-api.amazon.com")).issuer_name(_name("Test CA")).public_key(key.public_key())
            .serial_number(2).not_valid_before(NOW - dt.timedelta(days=1)).not_valid_after(NOW + dt.timedelta(days=30))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("echo-api.amazon.com")]), False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
            .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), True)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), False).sign(ca_key, hashes.SHA256()))
    return ca, leaf, key


@pytest.fixture
def client(pki, monkeypatch):
    ca, leaf, _ = pki
    monkeypatch.setattr(APP, "ROOTS", Store([ca]))
    monkeypatch.setattr(APP, "scarica", lambda u: leaf.public_bytes(serialization.Encoding.PEM))
    APP._cache.clear()
    return APP.app.test_client()


def post(client, key, body, url=URL, sign=True):
    raw = json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if sign:
        h["SignatureCertChainUrl"] = url
        h["Signature-256"] = base64.b64encode(key.sign(raw, padding.PKCS1v15(), hashes.SHA256())).decode()
    return client.post("/alexa", data=raw, headers=h)


def launch(app_id="amzn1.ask.skill.test", ts=None):
    return {"version": "1.0", "session": {"application": {"applicationId": app_id}, "user": {"userId": "u"}, "attributes": {}},
            "request": {"type": "LaunchRequest", "timestamp": (ts or NOW).strftime("%Y-%m-%dT%H:%M:%SZ")}}


def test_valid_request_is_answered(client, pki):
    r = post(client, pki[2], launch())
    assert r.status_code == 200 and r.json["response"]["outputSpeech"]["ssml"] == "<speak>Dimmi pure.</speak>"


@pytest.mark.parametrize("case", ["unsigned", "foreign_host", "path_traversal", "wrong_key", "other_skill", "old_timestamp"])
def test_bad_requests_are_rejected(client, pki, case):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if case == "wrong_key" else pki[2]
    body = launch(app_id="amzn1.ask.skill.other" if case == "other_skill" else "amzn1.ask.skill.test",
                  ts=NOW - dt.timedelta(minutes=5) if case == "old_timestamp" else None)
    url = {"foreign_host": "https://evil.example/echo.api/c.pem", "path_traversal": "https://s3.amazonaws.com/echo.api/../evil/c.pem"}.get(case, URL)
    assert post(client, key, body, url=url, sign=case != "unsigned").status_code == 400


def test_untrusted_certificate_chain_is_rejected(client, pki, monkeypatch):
    monkeypatch.setattr(APP, "ROOTS", APP._radici())   # real public roots: the test CA is not among them
    APP._cache.clear()
    assert post(client, pki[2], launch()).status_code == 400


def test_health(client):
    assert client.get("/health").json == {"ok": True}
