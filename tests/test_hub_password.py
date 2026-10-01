"""Hub admin password: no shipped default. Run: python3 tests/test_hub_password.py (or pytest)."""
import importlib.util, os, json, hashlib, tempfile, stat, sys, io, contextlib
SRC=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","overlay","opt","cloverstack","hub","clover-hub-api.py")
def load(d):
    os.environ["CLOVER_HUB_CONF"]=os.path.join(d,"hub.conf")
    os.environ["CLOVER_HUB_INITIAL_PW_FILE"]=os.path.join(d,"hub-initial-password")
    spec=importlib.util.spec_from_file_location("hub",SRC); m=importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    return m


def test_hub_password():
    d=tempfile.mkdtemp(); m=load(d)
    pw=open(m.INITIAL_PW_FILE).read().strip()
    assert len(pw)>=16 and m.verify_password(pw) and not m.verify_password("cloverOS")
    assert stat.S_IMODE(os.stat(m.INITIAL_PW_FILE).st_mode)==0o600
    assert stat.S_IMODE(os.stat(m.HUB_CONF).st_mode)==0o600
    # restart keeps same pw
    m2=load(d); assert m2.verify_password(pw)
    # two installs differ
    d2=tempfile.mkdtemp(); m3=load(d2); assert open(m3.INITIAL_PW_FILE).read()!=open(m.INITIAL_PW_FILE).read()
    # 2 legacy default rotated
    d=tempfile.mkdtemp(); json.dump({"password_hash":hashlib.sha256(b"cloverOS").hexdigest(),"x":1},open(d+"/hub.conf","w"))
    m=load(d); assert not m.verify_password("cloverOS"); assert json.load(open(m.HUB_CONF))["x"]==1
    assert m.verify_password(open(m.INITIAL_PW_FILE).read().strip())
    # legacy plaintext default rotated too
    d=tempfile.mkdtemp(); json.dump({"password":"cloverOS"},open(d+"/hub.conf","w")); m=load(d); assert not m.verify_password("cloverOS")
    # 3 user-set password untouched, no initial file
    d=tempfile.mkdtemp(); json.dump({"password_hash":hashlib.sha256(b"mine123").hexdigest()},open(d+"/hub.conf","w"))
    m=load(d); assert m.verify_password("mine123") and not os.path.exists(m.INITIAL_PW_FILE)
    # 4 change password removes initial file
    d=tempfile.mkdtemp(); m=load(d); m.change_password("newpass99")
    assert m.verify_password("newpass99") and not os.path.exists(m.INITIAL_PW_FILE)
    m=load(d); assert m.verify_password("newpass99")
    # 5 corrupt conf -> random, not default
    d=tempfile.mkdtemp(); open(d+"/hub.conf","w").write("{bad"); m=load(d); assert not m.verify_password("cloverOS") and os.path.exists(m.INITIAL_PW_FILE)


if __name__ == "__main__":
    test_hub_password()
    print("ALL OK")
