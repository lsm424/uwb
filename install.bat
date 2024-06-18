
# pyinstaller.exe .\main.spec --noconfirm
# copy .\config.yaml .\dist\uwb
pyinstaller --hidden-import=access --hidden-import=uwb --hidden-import=common --hidden-import=gui -F main.py


# pip install nuitka zstandard
python -m nuitka --follow-imports --enable-plugin=pyside6 --plugin-enable=numpy --include-package=common --include-package=gui --include-package=uwb --include-package=access --standalone --onefile  main.py