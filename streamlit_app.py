import os
import sys

# Ensure src/ and root are in Python module search path
root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Synchronize Streamlit Cloud secrets into os.environ
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
except Exception:
    pass

# Run the main Streamlit application dynamically on every script execution
app_path = os.path.join(root_dir, "ui", "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    code = compile(f.read(), app_path, "exec")
exec(code, globals())

