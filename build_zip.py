"""Build the zip to install in QGIS or upload to plugins.qgis.org.
The plugin code is at the root of this repository; the zip puts it inside the folder
CoastalInundation_Under_ClimateChange, as QGIS requires.
Usage: python build_zip.py   ->   CoastalInundation_Under_ClimateChange_v<version>.zip"""
import configparser
import pathlib
import zipfile

PLUGIN = "CoastalInundation_Under_ClimateChange"
EXCLUDE = {"README.md", "CITATION.cff", "build_zip.py", ".gitignore", "assets", ".git", ".github"}
root = pathlib.Path(__file__).resolve().parent
meta = configparser.ConfigParser()
meta.read(root / "metadata.txt", encoding="utf-8")
version = meta["general"]["version"]
out = root / f"{PLUGIN}_v{version}.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(root.rglob("*")):
        rel = f.relative_to(root)
        if (not f.is_file() or rel.parts[0] in EXCLUDE or "__pycache__" in rel.parts
                or f.suffix in (".pyc", ".zip")):
            continue
        z.write(f, pathlib.Path(PLUGIN) / rel)
print(out.name)
