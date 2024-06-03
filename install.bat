
pyinstaller.exe .\main.spec --noconfirm
copy .\config.yaml .\dist\uwb

pip install nuitka zstandard
python -m nuitka --follow-imports --enable-plugin=pyside6 --plugin-enable=numpy --include-package=common --include-package=gui --include-package=uwb --include-package=access --standalone --onefile  main.py